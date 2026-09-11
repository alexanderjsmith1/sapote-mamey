"""blastp_ingest.py (v9.7.163) — ingest NCBI BLASTp output into B5_BLASTp_Hits.

Input formats (both are standard NCBI web-BLAST downloads):
  - HitTable CSV  : -outfmt 10, headerless, 13 columns. The numeric source of truth.
  - Alignment XML : BLAST XML2; optional enrichment (subject description, sciname, subject
                    length, and the node/contig embedded in the query title).

Design (mirrors the pipeline's rules):
  - OBSERVED numeric fields come only from the CSV; enrichment fields are blank when no XML.
  - A BLASTp hit is a SIMILARITY signal (pct_identity / positives_pct), never a product-identity
    claim — same claim-safe posture as KCB.
  - Rows key to B1_BGC_Master on (strain, BGC_ID). BGC_ID is parsed off the query id
    (e.g. 'BGC008_ctg162_3' -> 'BGC008'); the short contig token ('ctg162') is captured, and the
    full node/contig ('NODE_162_length_14250_cov_63.7') is recovered from the XML query-title
    when supplied.
  - top_n caps hits per query gene (default 10), matching the user's top-10 download.
"""
from __future__ import annotations

import json
import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import re
import hashlib
import fnmatch
import math
import warnings as _warnings
import datetime as _dt
from pathlib import Path
import sqlite3
import stat
import uuid
from typing import Iterable, Sequence
from .xlsx_determinism import save_workbook_safely as _save_wb_safely


# External rollup importers historically repeated this positional schema in two tools and
# opened stores before proving that the target was the canonical store.  Keep one exact
# contract here, in the existing BLASTP-ingest owner, so reordered or partial tables cannot
# silently receive misaligned evidence.
BLASTP_HITS_SCHEMA = (
    ("workspace", "TEXT", 1),
    ("strain", "TEXT", 1),
    ("bgc_id", "TEXT", 1),
    ("gene", "TEXT", 1),
    ("aa_length", "INTEGER", 0),
    ("role", "TEXT", 0),
    ("domains", "TEXT", 0),
    ("hit_rank", "INTEGER", 0),
    ("subject_acc", "TEXT", 0),
    ("subject_organism", "TEXT", 0),
    ("subject_def", "TEXT", 0),
    ("subject_db", "TEXT", 0),
    ("pct_identity", "REAL", 0),
    ("align_length", "INTEGER", 0),
    ("query_coverage", "REAL", 0),
    ("evalue", "REAL", 0),
    ("bitscore", "REAL", 0),
    ("pct_positives", "REAL", 0),
    ("channel", "TEXT", 1),
    ("source_file", "TEXT", 1),
    ("source_mtime", "TEXT", 0),
    ("provenance_suspect", "INTEGER", 0),
)
BLASTP_HITS_COLUMNS = tuple(row[0] for row in BLASTP_HITS_SCHEMA)
_BLASTP_SOURCE_WORKSPACE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class BlastpStoreSchemaError(ValueError):
    """The selected SQLite file is not the admitted 22-column BLASTP hits store."""


class BlastpStoreWriteError(RuntimeError):
    """An admitted BLASTP store could not complete an atomic insert transaction."""


class BlastpAlignmentKeyConflictError(ValueError):
    """Two non-identical XML Search records claim the same query lookup key."""


class BlastpAlignmentSubjectKeyConflictError(BlastpAlignmentKeyConflictError):
    """Two non-identical XML Hit records claim the same subject lookup key."""


class BlastpOverlayReadError(RuntimeError):
    """An existing BLASTp overlay could not be read safely for an additive merge."""


class BlastpIngestLedgerError(RuntimeError):
    """The BLASTp ingest ledger exists but cannot be read without losing provenance."""


class BlastpTroveDiscoveryError(RuntimeError):
    """A configured BLASTp trove exists but cannot be traversed safely."""


class BlastpNumericEvidenceError(ValueError):
    """A numeric field needed for BLASTp evidence selection is invalid."""


class BlastpFileSetCommitError(RuntimeError):
    """A BLASTp multi-file commit failed and required bounded recovery."""


def _trove_entries(path: Path) -> list[Path]:
    """Snapshot a required trove directory without Path.glob's OSError suppression."""
    try:
        return sorted(path.iterdir())
    except OSError as exc:
        raise BlastpTroveDiscoveryError(
            f"BLASTP_TROVE_DISCOVERY_HOLD: cannot traverse {path} "
            f"({type(exc).__name__})"
        ) from exc


def _finite_evidence_number(value, field: str) -> float:
    """Return a finite evidence number or refuse an undecidable selection."""
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise BlastpNumericEvidenceError(
            f"BLASTP_NUMERIC_EVIDENCE_HOLD: invalid {field} {value!r}"
        ) from exc
    if not math.isfinite(number):
        raise BlastpNumericEvidenceError(
            f"BLASTP_NUMERIC_EVIDENCE_HOLD: non-finite {field} {value!r}"
        )
    return number


def _package_matches(package: Path, pattern: str) -> list[Path]:
    """Discover package evidence without collapsing traversal failure to no matches."""
    try:
        entries = list(package.iterdir())
    except OSError as exc:
        raise ValueError(
            f"BLASTP_PACKAGE_DISCOVERY_HOLD: cannot traverse {package} "
            f"({type(exc).__name__})"
        ) from exc
    return sorted(p for p in entries if p.is_file() and fnmatch.fnmatch(p.name, pattern))


def validate_blastp_source_workspace(value: str) -> str:
    """Return a portable provenance label or raise a typed admission hold."""
    label = str(value or "").strip()
    if not _BLASTP_SOURCE_WORKSPACE_RE.fullmatch(label):
        raise ValueError(
            "BLASTP_SOURCE_WORKSPACE_HOLD: use 1-64 letters, digits, dots, underscores, "
            "or hyphens, beginning with a letter or digit"
        )
    return label


def validate_blastp_hits_store(connection: sqlite3.Connection) -> None:
    """Require the exact ordered column/type/nullability contract for ``hits``.

    The strict order check is intentional even though writes use named columns: the store is a
    governed exchange object, and admitting a look-alike table would make downstream readers
    disagree about its meaning.
    """
    try:
        rows = connection.execute("PRAGMA table_info(hits)").fetchall()
    except sqlite3.DatabaseError as exc:
        raise BlastpStoreSchemaError(
            f"BLASTP_STORE_SCHEMA_HOLD: unable to inspect hits table: {exc}"
        ) from exc
    observed = tuple(
        (str(row[1]), str(row[2] or "").upper(), int(row[3]))
        for row in rows
    )
    if observed != BLASTP_HITS_SCHEMA:
        raise BlastpStoreSchemaError(
            "BLASTP_STORE_SCHEMA_HOLD: hits schema does not match the exact "
            f"22-column contract; expected={BLASTP_HITS_SCHEMA!r}; observed={observed!r}"
        )


def open_blastp_hits_store(
    database: str | Path, *, writable: bool = False
) -> sqlite3.Connection:
    """Open an existing admitted store without ever creating a missing SQLite file.

    SQLite's URI ``mode=ro`` and ``mode=rw`` both refuse absent paths.  This avoids the default
    ``sqlite3.connect(path)`` behavior that creates a zero-byte database during a dry run.
    """
    path = Path(database).expanduser()
    if not path.is_file():
        raise FileNotFoundError(f"BLASTP_STORE_MISSING: {path}")
    mode = "rw" if writable else "ro"
    uri = f"{path.resolve().as_uri()}?mode={mode}"
    try:
        connection = sqlite3.connect(uri, uri=True)
    except sqlite3.DatabaseError as exc:
        raise BlastpStoreSchemaError(
            f"BLASTP_STORE_OPEN_HOLD: cannot open {path} in mode={mode}: {exc}"
        ) from exc
    try:
        validate_blastp_hits_store(connection)
    except Exception:
        connection.close()
        raise
    return connection


def insert_blastp_hits(
    connection: sqlite3.Connection, rows: Iterable[Sequence[object]]
) -> int:
    """Insert admitted rows with named columns in one commit-or-rollback transaction."""
    materialized = [tuple(row) for row in rows]
    for number, row in enumerate(materialized, start=1):
        if len(row) != len(BLASTP_HITS_COLUMNS):
            raise BlastpStoreWriteError(
                "BLASTP_STORE_ROW_WIDTH_HOLD: "
                f"row {number} has {len(row)} values; expected {len(BLASTP_HITS_COLUMNS)}"
            )
    if not materialized:
        return 0
    validate_blastp_hits_store(connection)
    columns = ", ".join(BLASTP_HITS_COLUMNS)
    placeholders = ", ".join("?" for _ in BLASTP_HITS_COLUMNS)
    try:
        with connection:
            connection.executemany(
                f"INSERT INTO hits ({columns}) VALUES ({placeholders})",
                materialized,
            )
    except sqlite3.DatabaseError as exc:
        raise BlastpStoreWriteError(
            f"BLASTP_STORE_WRITE_HOLD: atomic insert rolled back: {exc}"
        ) from exc
    return len(materialized)

# NCBI -outfmt 10 standard column order (the 13-column web-BLAST variant with %positives last).
_CSV_COLS = [
    "query_id", "subject_acc", "pct_identity", "align_len", "mismatches", "gap_opens",
    "q_start", "q_end", "s_start", "s_end", "evalue", "bitscore", "positives_pct",
]

_BGC_RE = re.compile(r"(BGC\d+)")
_CTG_RE = re.compile(r"(ctg\d+)")
_NODE_RE = re.compile(r"(NODE_\d+(?:_length_\d+)?(?:_cov_[\d.]+)?)")


def parse_bgc_id(query_id: str) -> str:
    """'BGC008_ctg162_3' -> 'BGC008' (empty string if no BGC token)."""
    m = _BGC_RE.search(query_id or "")
    return m.group(1) if m else ""


def parse_short_contig(query_id: str) -> str:
    """'BGC008_ctg162_3' -> 'ctg162' (short form; full NODE_ comes from XML)."""
    m = _CTG_RE.search(query_id or "")
    return m.group(1) if m else ""


class BlastpHitTableError(ValueError):
    """A HitTable cannot be admitted as a complete, well-formed CSV result."""




class BlastpBindingConflict(ValueError):
    """v9.7.412: the HitTable query_id and the XML query-title name DIFFERENT BGCs for one query.
    Silent precedence would bind hits to whichever source won; this is a typed hold instead."""

def _non_numeric_hit_columns(raw: list[str]) -> list[str]:
    """Names of the numeric outfmt-10 columns (3..13) whose value is present but not a finite
    number. A blank is a producer-declared unknown (EBI's converter leaves `mismatches` empty,
    positives % is optional) and stays admissible, as the parse_hit_table docstring promises."""
    import math
    bad = []
    for idx in range(2, len(raw)):
        value = raw[idx]
        if value == "":
            continue
        try:
            if not math.isfinite(float(value)):
                bad.append(_CSV_COLS[idx])
        except (TypeError, ValueError):
            bad.append(_CSV_COLS[idx])
    return bad


def parse_hit_table(csv_path: str | Path, numeric_policy: str = "reject") -> list[dict]:
    """Read headerless 12/13-column outfmt 10; reject the whole malformed input.

    Empty/comment-only results are valid. Missing optional positives are blank, and
    existing producer blanks remain unknown. This checks structural admission, not
    query identity, provenance, or biological validity of the supplied measurements.
    """
    rows: list[dict] = []
    line = 0
    try:
        with open(csv_path, newline="", encoding="utf-8-sig") as fh:
            # Inspect only a bounded prefix; never materialize the input just to sniff it.
            head = fh.read(400).lstrip()
            if head.startswith("<") or "QBlastInfo" in head:
                raise BlastpHitTableError("BLASTP_HIT_TABLE_INVALID: upstream error document")
            fh.seek(0)
            reader = csv.reader(fh, strict=True)
            for raw in reader:
                line = reader.line_num
                if not raw or raw[0].lstrip().startswith("#"):
                    continue
                if len(raw) not in (12, 13):
                    raise BlastpHitTableError(
                        f"BLASTP_HIT_TABLE_INVALID: row ending at line {line} "
                        f"has {len(raw)} columns; expected 12 or 13"
                    )
                raw = [value.strip() for value in raw]
                if not raw[0] or not raw[1] or any("\x00" in value for value in raw):
                    raise BlastpHitTableError(
                        f"BLASTP_HIT_TABLE_INVALID: missing query/subject or NUL at line {line}"
                    )
                if len(raw) == 12:
                    raw.append("")
                # v9.7.410 hostile audit: outfmt 10 is headerless and columns 3-12 are numbers.
                # A header line ("query,subject,pident,length,...") used to be admitted as a hit
                # row — query_locus "query", subject "subject", pct_identity "pident" — i.e. a
                # fabricated hit that later blows up in float(). Non-finite values (nan/inf, or
                # an overflowing digit string) are equally impossible from BLAST. Reject the
                # whole input, same policy as the column-count check, and say which.
                bad = _non_numeric_hit_columns(raw)
                # v9.7.412: numeric_policy="flag" (manual ingest under a sealed package) keeps the
                # header-row rejection but records a per-row numeric defect so the binding guard can
                # QUARANTINE that row with a typed reason instead of rejecting the whole input.
                if bad and numeric_policy == "flag" and len(bad) < 8:
                    rec = dict(zip(_CSV_COLS, raw)); rec["_bad_numeric"] = ",".join(bad); rows.append(rec)
                    continue
                if bad:
                    looks_like_header = len(bad) >= 8
                    raise BlastpHitTableError(
                        "BLASTP_HIT_TABLE_INVALID: "
                        + ("header row detected at line %d — a HitTable must be headerless outfmt 10"
                           % line if looks_like_header else
                           "non-numeric or non-finite value(s) in %s at line %d"
                           % (", ".join(bad), line))
                    )
                rows.append(dict(zip(_CSV_COLS, raw)))
    except (OSError, UnicodeError, csv.Error) as exc:
        raise BlastpHitTableError(
            f"BLASTP_HIT_TABLE_INVALID: unreadable or malformed CSV near line {line} "
            f"({type(exc).__name__})"
        ) from exc
    return rows


def parse_alignment_xml(xml_path: str | Path) -> dict[str, dict]:
    """Extract enrichment keyed by query_id: {query_title, query_len, node, contig,
    and per-subject {acc: {desc, sciname, subject_len}}}. Regex-based (no lxml dep)."""
    txt = Path(xml_path).read_text(encoding="utf-8", errors="replace")
    out: dict[str, dict] = {}
    claims: dict[str, tuple[str, str, dict]] = {}
    # each <Report>...<Search> carries one query
    for rep in re.findall(r"<Search>.*?</Search>", txt, re.S):
        qid = _tag(rep, "query-id")
        qtitle = _tag(rep, "query-title")
        qlen = _tag(rep, "query-len")
        # the query-title in web-BLAST carries: 'BGCxxx_ctgN_M contig=NODE_.. node=NODE_..'
        node = ""
        mnode = re.search(r"node=(NODE_\S+)", qtitle) or _NODE_RE.search(qtitle)
        if mnode:
            node = mnode.group(1)
        contig = ""
        mctg = re.search(r"contig=(\S+)", qtitle)
        if mctg:
            contig = mctg.group(1)
        subjects: dict[str, dict] = {}
        subject_claims: dict[str, tuple[str, str, dict]] = {}
        for hit in re.findall(r"<Hit>.*?</Hit>", rep, re.S):
            acc = _tag(hit, "accession")
            if not acc:
                continue
            desc = _tag(hit, "title") or _tag(hit, "description")
            entry = {
                "subject_desc": desc,
                "sciname": _tag(hit, "sciname"),
                "subject_len": _tag(hit, "len"),
            }
            mver = re.search(r"<id>[^<]*\|(\S+?)\|", hit)
            versioned_id = mver.group(1) if mver else ""
            claim = (acc, versioned_id, entry)
            # Key by both the bare accession and its observed versioned form, but never
            # let either namespace silently overwrite a different Hit claim.
            for key in (acc, versioned_id):
                if not key:
                    continue
                existing = subject_claims.get(key)
                if existing is None:
                    subjects[key] = entry
                    subject_claims[key] = claim
                elif existing != claim:
                    raise BlastpAlignmentSubjectKeyConflictError(
                        "BLASTP_ALIGNMENT_SUBJECT_KEY_CONFLICT: XML Hit records map "
                        f"the same subject lookup key {key!r} to conflicting enrichment"
                    )
        # key by the leading token of the query title (matches the CSV query_id), and by query-id
        title_key = qtitle.split()[0] if qtitle else ""
        # v9.7.410 (CLAUDE_410_blastp_bgc_recovery_409): the BGC token survives ONLY here when the
        # query FASTA used a space-delimited defline (`>ctg107_3 gene=ctg107_3 BGC=BGC003 ...`) --
        # NCBI truncates the HitTable query_id at the first space, dropping `BGC=`. Carry the
        # BGC id parsed off the full title so build_b5_rows can recover it.
        rec = {"query_title": qtitle, "query_len": qlen, "node": node, "contig": contig,
               "bgc_id": parse_bgc_id(qtitle), "subjects": subjects}
        claim = (qid, title_key, rec)
        for key in (title_key, qid):
            if not key:
                continue
            existing = claims.get(key)
            if existing is None:
                out[key] = rec
                claims[key] = claim
            elif existing != claim:
                raise BlastpAlignmentKeyConflictError(
                    "BLASTP_ALIGNMENT_QUERY_KEY_CONFLICT: XML Search records map "
                    f"the same query lookup key {key!r} to conflicting enrichment"
                )
    return out


def _tag(block: str, name: str) -> str:
    m = re.search(rf"<{name}>(.*?)</{name}>", block, re.S)
    return m.group(1).strip() if m else ""


def _load_enrichment(xml_path: str | Path | None) -> tuple[dict, str]:
    """Parse the optional alignment XML. Returns ``(enrichment, status)`` with status one of
    ``absent`` (no path / no file), ``ok`` (>= 1 query parsed), ``empty`` (file present, zero
    queries — almost always the classic BLAST XML *1* download instead of XML2, which this parser
    does not read) or ``error:<ExceptionName>``.

    v9.7.410 hostile audit: before this, an XML that parsed to nothing was indistinguishable
    from a good one — ``ingest_blastp`` reported ``enriched: True`` because the file *existed*,
    and every description / sciname column silently stayed blank. Enrichment is still
    best-effort (the CSV numbers land regardless), but the miss is now warned and reported.
    """
    if not (xml_path and Path(xml_path).exists()):
        return {}, "absent"
    try:
        enrich = parse_alignment_xml(xml_path)
    except BlastpAlignmentKeyConflictError:
        raise
    except Exception as exc:  # enrichment is best-effort; numbers still land from the CSV
        status = f"error:{type(exc).__name__}"
        _warnings.warn(f"[ingest-blastp] alignment XML {Path(xml_path).name} could not be parsed "
                       f"({type(exc).__name__}); hits ingested WITHOUT XML enrichment", stacklevel=3)
        return {}, status
    if not enrich:
        _warnings.warn(f"[ingest-blastp] alignment XML {Path(xml_path).name} yielded 0 queries — "
                       "expected BLAST XML2 (<Search> blocks); hits ingested WITHOUT XML enrichment",
                       stacklevel=3)
        return {}, "empty"
    return enrich, "ok"


def build_b5_rows(strain: str, csv_path: str | Path, xml_path: str | Path | None = None,
                  top_n: int = 10, source: str = "NCBI web-BLASTp",
                  enrich_status: dict | None = None, numeric_policy: str = "reject") -> list[dict]:
    """Build B5_BLASTp_Hits rows from a HitTable CSV (+ optional XML). Ranks hits per query gene
    by CSV order (NCBI returns best-first), capped at top_n. Never raises on a missing XML.

    ``source`` defaults to "NCBI web-BLASTp" for backward compatibility, but that is only
    correct for the NCBI transport. blastp_ebi.py's -outfmt10 CSV output is the SAME 13-column
    shape and is otherwise indistinguishable at this layer, so a caller ingesting an EBI-origin
    HitTable MUST pass an explicit ``source`` (e.g. "EBI (uniprotkb_bacteria)") or every such row
    is silently mislabeled NCBI in B5_BLASTp_Hits, contradicting blastp_ebi.py's own documented
    claim-safety requirement that every EBI-transport card carry transport=EBI provenance."""
    raw = parse_hit_table(csv_path, numeric_policy=numeric_policy)
    enrich, xml_status = _load_enrichment(xml_path)
    if enrich_status is not None:
        enrich_status["xml"] = xml_status
    today = _dt.date.today().isoformat()
    per_query_rank: dict[str, int] = {}
    rows: list[dict] = []
    for h in raw:
        qid = h["query_id"]
        per_query_rank[qid] = per_query_rank.get(qid, 0) + 1
        rank = per_query_rank[qid]
        if rank > top_n:
            continue
        enr = enrich.get(qid, {})
        _subjmap = enr.get("subjects") or {}
        subj = _subjmap.get(h["subject_acc"]) or _subjmap.get(h["subject_acc"].split(".")[0], {})
        # node/contig: prefer full NODE_ from XML; else short ctg from the query id
        contig = enr.get("node") or enr.get("contig") or parse_short_contig(qid)
        # BGC: from the CSV query_id when the defline was space-free (pipe panel / BGC-leading
        # ids). v9.7.410: when NCBI truncated a space-delimited defline the CSV id carries no
        # BGC token; fall back to the id parsed off the XML <query-title>. Never invented: with
        # neither source the row keeps BGC_ID='' and write_nr_overlay skips it as before.
        _csv_bgc = parse_bgc_id(qid)
        _xml_bgc = enr.get("bgc_id") or parse_bgc_id(enr.get("query_title", ""))
        if _csv_bgc and _xml_bgc and _csv_bgc != _xml_bgc:
            # v9.7.412 (F4): the two sources disagree about which BGC this query belongs to.
            raise BlastpBindingConflict(
                f"XML_HITTABLE_BGC_CONFLICT: query {qid!r}: HitTable id says {_csv_bgc}, "
                f"XML query-title says {_xml_bgc}; refusing to bind by precedence")
        bgc_id = _csv_bgc or _xml_bgc
        rows.append({
            "_bad_numeric": h.get("_bad_numeric", ""),
            "strain": strain,
            "BGC_ID": bgc_id,
            "contig": contig,
            "query_locus": qid,
            "query_len": enr.get("query_len", ""),
            "hit_rank": rank,
            "subject_acc": h["subject_acc"],
            "subject_desc": subj.get("subject_desc", ""),
            "sciname": subj.get("sciname", ""),
            "pct_identity": h["pct_identity"],
            "positives_pct": h["positives_pct"],
            "align_len": h["align_len"],
            "mismatches": h["mismatches"],
            "gap_opens": h["gap_opens"],
            "q_start": h["q_start"],
            "q_end": h["q_end"],
            "s_start": h["s_start"],
            "s_end": h["s_end"],
            "evalue": h["evalue"],
            "bitscore": h["bitscore"],
            "subject_len": subj.get("subject_len", ""),
            "source": source,
            "ingest_date": today,
        })
    return rows


# --- v9.7.239: nr overlay write path -------------------------------------------------
# authored_verify._bgc_context_from_package and genome_explore._conservation_median read
# <package>/blastp_online/<BGC>_online_blastp.csv to prefer nr over ClusterBlast when
# computing conservation_median_id (the input to the NOVELTY_CONTRADICTION lint). Until
# now NOTHING wrote that file: `blastp-online` writes to --outdir (default cwd), and
# `ingest-blastp` wrote only to the workbook's B5 sheet, which no code reads back. Any
# operator who runs BLASTp themselves left the guard disarmed, silently falling back to
# ClusterBlast. Mirror the ingested nr hits into the overlay the readers expect.
from .blastp_online import reconcile as _reconcile   # v9.7.241 (P7b)

_OVERLAY_COLS = ["locus_tag", "aa_length", "antismash_domains", "blastp_top_def",
                 "blastp_accession", "blastp_organism", "pct_identity", "query_coverage",
                 "evalue", "bitscore", "agreement", "channel", "query_strain",
                 "query_bgc", "query_locus", "query_aa_length", "source_channel",
                 "source_file_sha256", "ingest_date"]

# channel precedence: a higher-precedence channel's row wins for the same gene.
# (v9.7.344) swissprot added between clustered_nr and ebi; relative order of the pre-existing
# channels (nr > clustered_nr > ebi) is unchanged, so existing precedence behavior is preserved.
_CHANNEL_RANK = {"nr": 4, "clustered_nr": 3, "swissprot": 2, "ebi": 1}

# (v9.7.344) per-channel per-gene filenames actually found in the workspace troves. The original
# code only matched *_top_hit_per_gene.csv, so clustered_nr (*_top10_clustered.csv) and swissprot
# (*_top10_local.csv) silently ingested 0 rows — the gate's remediation would dead-end. Match the
# real names.
_TROVE_FILE_GLOBS = {
    "nr": ("{bgc}_top_hit_per_gene.csv", "*_top_hit_per_gene.csv"),
    "clustered_nr": ("{bgc}_blastp_top10_clustered.csv", "*_top10_clustered.csv",
                     "{bgc}_top_hit_per_gene.csv", "*_top_hit_per_gene.csv"),
    "swissprot": ("{bgc}_blastp_top10_local.csv", "*_top10_local.csv",
                  "{bgc}_top_hit_per_gene.csv", "*_top_hit_per_gene.csv"),
    "ebi": ("{bgc}_ebi_top_hit_per_gene.csv", "*_ebi*.csv",
            "{bgc}_top_hit_per_gene.csv", "*_top_hit_per_gene.csv"),
}

# column aliases in a pre-organized per-BGC trove (Blastp RESULTS/<S>/<BGC>/<BGC>_top_hit_per_gene.csv)
_TROVE_ALIASES = {
    "locus_tag": ("gene", "locus_tag", "query_gene"),
    "blastp_accession": ("subject_acc", "accession"),
    "blastp_organism": ("subject_organism", "organism"),
    "blastp_top_def": ("subject_def", "definition", "title"),
    "pct_identity": ("pct_identity", "pident"),
    "query_coverage": ("query_coverage", "qcovs", "coverage"),
    "evalue": ("evalue", "e_value"),
    "bitscore": ("bitscore", "bit_score"),
    "aa_length": ("aa_length", "aa", "query_len"),
}

_STRAIN_ALIASES = ("query_strain", "strain", "strain_id")
_BGC_ALIASES = ("query_bgc", "bgc_id", "BGC_ID")
_QUERY_ALIASES = ("query_locus", "query_id", "query_gene", "gene", "locus_tag")
_GUARD_REASONS = (
    "FOREIGN_STRAIN", "FOREIGN_BGC", "NONCURRENT_LOCUS",
    "QUERY_CURRENT_AA_LENGTH_MISMATCH", "ZERO_OR_BLANK_AA_LENGTH",
    "LEGACY_PROVENANCE_HOLD",
    # v9.7.412: manual `ingest-blastp` path (F1/F2/F5-F7)
    "IMPOSSIBLE_PCT_IDENTITY", "NONNUMERIC_EVALUE", "NONNUMERIC_FIELD", "HIT_LONGER_THAN_QUERY",
)
_QUARANTINE_COLS = [
    "reason", "channel", "package_strain", "destination_bgc", "query_strain",
    "query_bgc", "query_locus", "query_aa_length", "current_aa_length",
    "source_file", "source_file_sha256", "source_row_number", "source_row_json",
]


def _pick(row: dict, names: tuple[str, ...], default: str = "") -> str:
    for n in names:
        if row.get(n) not in (None, ""):
            return str(row[n])
    return default


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    """Write to a temp sibling then atomically replace (mirrors packaging.py's
    ``_atomic_write_text``). An interrupted plain write here (kill -9, disk full, crash) can leave
    a truncated quarantine/receipt/ledger/overlay/top10-store file; a truncated JSON ledger is then
    read back by `read_ingest_ledger()`'s `except (OSError, json.JSONDecodeError): return {}` as an
    EMPTY ledger, silently erasing every previously-ingested channel's admitted/quarantined
    bookkeeping rather than surfacing the corruption -- exactly the file the BLASTp completeness
    gate trusts to know what has already been ingested."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


_FILESET_TXN_DIR = ".blastp_fileset_transactions"


def _recovery_kind(path: Path, *, directory: bool = False, missing: bool = False) -> bool:
    """Inspect lexical transaction paths without following links or suppressing errors."""
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        if missing:
            return False
        raise BlastpFileSetCommitError(f"BLASTP_FILESET_RECOVERY_HOLD: missing {path}")
    except OSError as exc:
        raise BlastpFileSetCommitError(
            f"BLASTP_FILESET_RECOVERY_HOLD: cannot inspect {path} ({type(exc).__name__})"
        ) from exc
    expected = stat.S_ISDIR(mode) if directory else stat.S_ISREG(mode)
    if not expected:
        raise BlastpFileSetCommitError(
            f"BLASTP_FILESET_RECOVERY_HOLD: unexpected file type at {path}"
        )
    return True


def _cleanup_fileset_transaction(txn_dir: Path) -> None:
    """Remove ordinary transaction debris only; never traverse a link during cleanup."""
    try:
        _recovery_kind(txn_dir.parent, directory=True)
        _recovery_kind(txn_dir, directory=True)
        children = list(txn_dir.iterdir())
        for child in children:
            _recovery_kind(child)
        for child in children:
            child.unlink()
        txn_dir.rmdir()
        parent = txn_dir.parent
        if not any(parent.iterdir()):
            parent.rmdir()
    except OSError as exc:
        import warnings
        warnings.warn(
            f"BLASTP_FILESET_CLEANUP_PENDING: {txn_dir} ({type(exc).__name__})",
            RuntimeWarning,
        )


def _validated_recovery_targets(package: Path, txn_dir: Path, journal: dict) -> list[dict]:
    """Validate the entire restoration set before changing any target."""
    if not isinstance(journal, dict) or not isinstance(journal.get("targets"), list):
        raise BlastpFileSetCommitError("BLASTP_FILESET_RECOVERY_HOLD: invalid journal targets")
    _recovery_kind(txn_dir.parent, directory=True)
    _recovery_kind(txn_dir, directory=True)
    root = package.resolve()
    paths, indexes = set(), set()
    for item in journal["targets"]:
        if not isinstance(item, dict):
            raise BlastpFileSetCommitError("BLASTP_FILESET_RECOVERY_HOLD: invalid target record")
        index = item.get("index")
        locator = item.get("relative_path")
        if (type(index) is not int or index < 0 or index in indexes
                or not isinstance(locator, str) or not locator
                or type(item.get("existed")) is not bool
                or item.get("backup") != f"backup_{index}.bin"
                or item.get("staged") not in ("", f"staged_{index}.txt")):
            raise BlastpFileSetCommitError("BLASTP_FILESET_RECOVERY_HOLD: invalid target schema")
        relative = Path(locator)
        if relative.is_absolute() or '..' in relative.parts or locator in paths:
            raise BlastpFileSetCommitError("BLASTP_FILESET_RECOVERY_HOLD: invalid target path")
        target = package / relative
        try:
            target.resolve(strict=False).relative_to(root)
        except (OSError, ValueError) as exc:
            raise BlastpFileSetCommitError("BLASTP_FILESET_RECOVERY_HOLD: target escapes package") from exc
        current = package
        for part in relative.parts[:-1]:
            current = current / part
            _recovery_kind(current, directory=True, missing=True)
        _recovery_kind(target, missing=True)
        if item["existed"]:
            _recovery_kind(txn_dir / item["backup"])
        paths.add(locator)
        indexes.add(index)
    return journal["targets"]


def _rollback_fileset_transaction(package: Path, txn_dir: Path, journal: dict) -> None:
    """Restore every preflighted target; preserve the journal on a restoration failure."""
    targets = _validated_recovery_targets(package, txn_dir, journal)
    for item in targets:
        target = package / item["relative_path"]
        if item["existed"]:
            backup = txn_dir / item["backup"]
            target.parent.mkdir(parents=True, exist_ok=True)
            restore = txn_dir / f"restore_{item['index']}.tmp"
            _recovery_kind(restore, missing=True)
            restore.write_bytes(backup.read_bytes())
            restore.replace(target)
        else:
            try:
                target.unlink()
            except FileNotFoundError:
                continue
    _cleanup_fileset_transaction(txn_dir)


def _recover_fileset_transactions(package: Path) -> None:
    """Recover valid PREPARED transactions before a new writer proceeds."""
    root = package / _FILESET_TXN_DIR
    if not _recovery_kind(root, directory=True, missing=True):
        return
    try:
        txn_dirs = sorted(root.iterdir())
        # Preflight every entry so a later malformed directory cannot follow earlier writes.
        journals = []
        for txn_dir in txn_dirs:
            _recovery_kind(txn_dir, directory=True)
            journal_path = txn_dir / "journal.json"
            _recovery_kind(journal_path)
            journal = json.loads(journal_path.read_text(encoding="utf-8"))
            if not isinstance(journal, dict) or journal.get("state") not in {"COMMITTED", "PREPARED"}:
                raise BlastpFileSetCommitError("BLASTP_FILESET_RECOVERY_HOLD: invalid journal")
            if journal["state"] == "PREPARED":
                _validated_recovery_targets(package, txn_dir, journal)
            else:
                for child in txn_dir.iterdir():
                    _recovery_kind(child)
            journals.append((txn_dir, journal))
        for txn_dir, journal in journals:
            if journal["state"] == "COMMITTED":
                _cleanup_fileset_transaction(txn_dir)
            else:
                _rollback_fileset_transaction(package, txn_dir, journal)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BlastpFileSetCommitError(
            f"BLASTP_FILESET_RECOVERY_HOLD: unreadable recovery data ({type(exc).__name__})"
        ) from exc


def _commit_text_file_set(package: Path, payloads: dict[Path, str],
                          deletions: set[Path] | None = None) -> None:
    """Commit a bounded set of text files, rolling back caught replacement failures.

    This is deliberately not a power-loss or concurrent-writer atomicity claim. The durable
    PREPARED journal exists so a later writer can retry rollback after a caught rollback failure.
    """
    deletions = deletions or set()
    targets = sorted(set(payloads) | set(deletions), key=lambda p: str(p))
    if not targets:
        return
    package_root = package.resolve()
    _recovery_kind(package / _FILESET_TXN_DIR, directory=True, missing=True)
    txn_dir = package / _FILESET_TXN_DIR / uuid.uuid4().hex
    txn_dir.mkdir(parents=True)
    journal = {"state": "PREPARED", "targets": []}
    try:
        for index, target in enumerate(targets):
            try:
                relative = target.resolve(strict=False).relative_to(package_root)
            except ValueError as exc:
                raise BlastpFileSetCommitError(
                    f"BLASTP_FILESET_COMMIT_HOLD: target escapes package: {target}"
                ) from exc
            try:
                target_stat = target.stat()
            except FileNotFoundError:
                existed = False
            except OSError as exc:
                raise BlastpFileSetCommitError(
                    f"BLASTP_FILESET_COMMIT_HOLD: cannot inspect target {relative} "
                    f"({type(exc).__name__})"
                ) from exc
            else:
                if not stat.S_ISREG(target_stat.st_mode):
                    raise BlastpFileSetCommitError(
                        f"BLASTP_FILESET_COMMIT_HOLD: target is not a regular file: {relative}"
                    )
                existed = True
            item = {"index": index, "relative_path": str(relative), "existed": existed,
                    "backup": f"backup_{index}.bin", "staged": ""}
            if existed:
                (txn_dir / item["backup"]).write_bytes(target.read_bytes())
            if target in payloads:
                item["staged"] = f"staged_{index}.txt"
                (txn_dir / item["staged"]).write_text(payloads[target], encoding="utf-8")
            journal["targets"].append(item)
        _atomic_write_text(txn_dir / "journal.json", json.dumps(journal, sort_keys=True) + "\n")
        for item in journal["targets"]:
            target = package / item["relative_path"]
            if item["staged"]:
                target.parent.mkdir(parents=True, exist_ok=True)
                (txn_dir / item["staged"]).replace(target)
            elif target.exists():
                target.unlink()
        journal["state"] = "COMMITTED"
        _atomic_write_text(txn_dir / "journal.json", json.dumps(journal, sort_keys=True) + "\n")
    except Exception as commit_exc:
        try:
            _rollback_fileset_transaction(package, txn_dir, journal)
        except Exception as rollback_exc:
            raise BlastpFileSetCommitError(
                f"BLASTP_FILESET_RECOVERY_HOLD: commit failed and rollback remains pending at "
                f"{txn_dir} ({type(rollback_exc).__name__})"
            ) from commit_exc
        raise BlastpFileSetCommitError(
            f"BLASTP_FILESET_COMMIT_HOLD: commit failed; prior file set restored "
            f"({type(commit_exc).__name__})"
        ) from commit_exc
    _cleanup_fileset_transaction(txn_dir)


def _read_optional_package_manifest(package: str | Path) -> dict | None:
    """Read an existing package manifest; missing is legacy absence, invalid is a hold."""
    manifest = Path(package) / "manifest.json"
    try:
        raw = manifest.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ValueError(
            f"BLASTP_PACKAGE_MANIFEST_HOLD: cannot read existing manifest "
            f"{manifest.name!r} ({type(exc).__name__})"
        ) from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"BLASTP_PACKAGE_MANIFEST_HOLD: cannot read existing manifest "
            f"{manifest.name!r} ({type(exc).__name__})"
        ) from exc
    if not isinstance(data, dict):
        raise ValueError("BLASTP_PACKAGE_MANIFEST_HOLD: package manifest root must be an object")
    return data


def _package_strain(package: Path, explicit_strain: str | None) -> str:
    """Load the sealed package identity and fail before any output path is created."""
    manifest = package / "manifest.json"
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"BLASTP ingest requires a readable package manifest: {manifest}") from exc
    strains = {str(data.get(k) or "").strip() for k in ("strain_id", "strain")
               if str(data.get(k) or "").strip()}
    if len(strains) != 1:
        raise ValueError("BLASTP ingest requires exactly one nonblank package strain identity")
    package_strain = next(iter(strains))
    if explicit_strain and str(explicit_strain).strip() != package_strain:
        raise ValueError(
            f"--strain {explicit_strain!r} conflicts with package manifest strain "
            f"{package_strain!r}"
        )
    return package_strain


def _positive_int(value) -> int | None:
    try:
        number = int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _current_locus_lengths(package: Path) -> dict[str, dict[str, int]]:
    """Load the authoritative current (BGC, locus, positive aa length) map.

    The sealed gene-context JSONL is preferred. The sealed all-BGC locus/gene table is a
    supported fallback for packages whose gene-context phase was unavailable. Ambiguous duplicate
    keys fail closed.
    """
    out: dict[str, dict[str, int]] = {}

    def add(bgc, locus, aa) -> None:
        bgc = str(bgc or "").strip()
        locus = str(locus or "").strip()
        length = _positive_int(aa)
        if not bgc or not locus or length is None:
            return
        old = out.setdefault(bgc, {}).get(locus)
        if old is not None and old != length:
            raise ValueError(
                f"ambiguous current aa length for {bgc}/{locus}: {old} versus {length}"
            )
        out[bgc][locus] = length

    contexts = _package_matches(package, "*gene_context.jsonl")
    if len(contexts) > 1:
        raise ValueError("BLASTP ingest found multiple gene_context JSONL files")
    if contexts:
        try:
            with contexts[0].open(encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    bgc = rec.get("bgc_id") or rec.get("BGC_ID")
                    for cds in rec.get("cds", []) or []:
                        add(bgc, cds.get("locus_tag"), cds.get("aa_length"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"unreadable current gene context: {contexts[0]}") from exc
    else:
        tables = _package_matches(package, "*gene_by_gene_all_bgcs.csv")
        if len(tables) > 1:
            raise ValueError("BLASTP ingest found multiple all-BGC locus tables")
        if tables:
            try:
                for row in csv.DictReader(tables[0].open(newline="", encoding="utf-8")):
                    add(row.get("bgc_id") or row.get("BGC_ID"), row.get("locus_tag"),
                        row.get("aa_length"))
            except (OSError, csv.Error) as exc:
                raise ValueError(f"unreadable current locus table: {tables[0]}") from exc
    if not out:
        raise ValueError(
            "BLASTP ingest requires authoritative current loci with positive aa lengths "
            "from sealed gene_context or all-BGC locus data"
        )
    return out


def _query_parts(row: dict) -> tuple[str, str, str, str]:
    raw_query = _pick(row, _QUERY_ALIASES)
    query_strain = _pick(row, _STRAIN_ALIASES)
    query_bgc = _pick(row, _BGC_ALIASES)
    if raw_query:
        parts = [p.strip() for p in raw_query.split("|")]
        if not query_strain and len(parts) >= 2 and _BGC_RE.fullmatch(parts[1]):
            query_strain = parts[0]
        if not query_bgc:
            query_bgc = parse_bgc_id(raw_query)
    locus = _gene_from_query(raw_query)
    aa = _pick(row, ("query_aa_length",) + _TROVE_ALIASES["aa_length"])
    if not aa:
        aa = _aa_from_query(raw_query)
    if not aa and raw_query:
        parts = [p.strip() for p in raw_query.split("|")]
        if parts and parts[-1].isdigit():
            aa = parts[-1]
    return query_strain.strip(), query_bgc.strip(), locus.strip(), str(aa or "").strip()


def _validate_ingest_row(row: dict, package_strain: str, destination_bgc: str,
                         current: dict[str, dict[str, int]]) -> tuple[dict, str]:
    query_strain, query_bgc, locus, query_aa = _query_parts(row)
    current_aa = current.get(destination_bgc, {}).get(locus)
    keys = {
        "query_strain": query_strain, "query_bgc": query_bgc,
        "query_locus": locus, "query_aa_length": query_aa,
        "current_aa_length": str(current_aa or ""),
    }
    if not query_strain or not query_bgc:
        return keys, "LEGACY_PROVENANCE_HOLD"
    if query_strain != package_strain:
        return keys, "FOREIGN_STRAIN"
    if query_bgc != destination_bgc or query_bgc not in current:
        return keys, "FOREIGN_BGC"
    if not locus or current_aa is None:
        return keys, "NONCURRENT_LOCUS"
    query_len = _positive_int(query_aa)
    if query_len is None:
        return keys, "ZERO_OR_BLANK_AA_LENGTH"
    if query_len != current_aa:
        return keys, "QUERY_CURRENT_AA_LENGTH_MISMATCH"
    return keys, ""


def _quarantine_row(reason: str, channel: str, package_strain: str, bgc: str,
                    keys: dict, source_file: str, source_sha: str, row_number: int,
                    row: dict) -> dict:
    return {
        "reason": reason, "channel": channel, "package_strain": package_strain,
        "destination_bgc": bgc, "query_strain": keys.get("query_strain", ""),
        "query_bgc": keys.get("query_bgc", ""), "query_locus": keys.get("query_locus", ""),
        "query_aa_length": keys.get("query_aa_length", ""),
        "current_aa_length": keys.get("current_aa_length", ""),
        "source_file": source_file, "source_file_sha256": source_sha,
        "source_row_number": row_number,
        "source_row_json": json.dumps(row, sort_keys=True, separators=(",", ":")),
    }


def _write_guard_artifacts(package: Path, channel: str, kind: str, package_strain: str,
                           sources: list[dict], admitted: dict[str, int],
                           quarantined: list[dict]) -> tuple[str, str]:
    """Write deterministic, content-addressed quarantine and receipt artifacts."""
    source_rows = sorted(sources, key=lambda r: (r["bgc"], r["file"], r["sha256"]))
    token_payload = json.dumps(
        {"channel": channel, "kind": kind, "sources": source_rows},
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")
    token = hashlib.sha256(token_payload).hexdigest()[:16]
    qdir = package / "blastp_quarantine"
    rdir = package / "blastp_ingest_receipts"
    qdir.mkdir(parents=True, exist_ok=True)
    rdir.mkdir(parents=True, exist_ok=True)
    qpath = qdir / f"{channel}_{kind}_{token}_quarantine.csv"
    ordered_q = sorted(quarantined, key=lambda r: (
        r["destination_bgc"], r["query_locus"], r["reason"], r["source_file"],
        int(r["source_row_number"]), r["source_row_json"],
    ))
    import io
    buf = io.StringIO(newline="")
    writer = _SafeDictWriter(buf, fieldnames=_QUARANTINE_COLS, lineterminator="\n")
    writer.writeheader()
    for row in ordered_q:
        writer.writerow({k: row.get(k, "") for k in _QUARANTINE_COLS})
    qtext = buf.getvalue()
    if qpath.exists() and qpath.read_text(encoding="utf-8") != qtext:
        raise ValueError(f"immutable BLASTP quarantine collision: {qpath}")
    _atomic_write_text(qpath, qtext)

    reason_counts = {reason: 0 for reason in _GUARD_REASONS}
    quarantined_by_bgc: dict[str, int] = {}
    for row in ordered_q:
        reason_counts[row["reason"]] += 1
        quarantined_by_bgc[row["destination_bgc"]] = \
            quarantined_by_bgc.get(row["destination_bgc"], 0) + 1
    all_bgcs = sorted(set(admitted) | set(quarantined_by_bgc))
    receipt = {
        "schema": "mamey_blastp_five_part_ingest_v1",
        "package_strain": package_strain,
        "channel": channel,
        "store_kind": kind,
        "sources": source_rows,
        "admitted_by_bgc": {b: int(admitted.get(b, 0)) for b in all_bgcs},
        "quarantined_by_bgc": {b: int(quarantined_by_bgc.get(b, 0)) for b in all_bgcs},
        "quarantined_by_reason": reason_counts,
        "admitted_total": sum(admitted.values()),
        "quarantined_total": len(ordered_q),
        "evidence_complete_by_bgc": {b: bool(admitted.get(b, 0)) for b in all_bgcs},
        "quarantine_file": qpath.name,
        "quarantine_sha256": hashlib.sha256(qtext.encode("utf-8")).hexdigest(),
    }
    rpath = rdir / f"{channel}_{kind}_{token}_receipt.json"
    rtext = json.dumps(receipt, indent=2, sort_keys=True) + "\n"
    if rpath.exists() and rpath.read_text(encoding="utf-8") != rtext:
        raise ValueError(f"immutable BLASTP receipt collision: {rpath}")
    _atomic_write_text(rpath, rtext)
    return str(qpath), str(rpath)


def ingest_blastp_trove(package: str | Path, trove_dir: str | Path, channel: str,
                        strain: str | None = None) -> dict:
    """Ingest a pre-parsed per-BGC hit trove into <package>/blastp_online/<BGC>_online_blastp.csv.

    trove_dir layout: <STRAIN>/<BGC>/<BGC>_top_hit_per_gene.csv (the schema blastp_ingest/
    blastp_followup already emit). Unlike ingest-blastp this needs NO raw NCBI HitTable and NO
    workbook: the trove is already the rank-1 hit per gene. Channel-tagged; higher-precedence
    channels are not overwritten by lower ones. Reader-side, non-scoring.
    """
    if channel not in _CHANNEL_RANK:
        raise ValueError(f"channel must be one of {sorted(_CHANNEL_RANK)}; got {channel!r}")
    pkg = Path(package)
    _recover_fileset_transactions(pkg)
    package_strain = _package_strain(pkg, strain)
    current = _current_locus_lengths(pkg)
    outdir = pkg / "blastp_online"
    domains = _domains_by_locus(pkg)
    self_binomial = _self_binomial(pkg)
    troot = Path(trove_dir)
    # accept either <trove>/<BGC>/... (single strain) or <trove>/<STRAIN>/<BGC>/...
    direct_strain = troot / package_strain
    if direct_strain.is_dir():
        strain_dirs = [direct_strain]
    else:
        root_entries = _trove_entries(troot)
        strain_dirs = ([d for d in root_entries if d.is_dir()]
                       if not any(d.is_dir() and d.name.upper().startswith("BGC")
                                  for d in root_entries) else [troot])
    written: dict[str, int] = {}
    rejected: list[dict] = []
    sources: list[dict] = []
    plans: list[tuple[str, Path, list[dict]]] = []
    for sdir in strain_dirs:
        for bgc_dir in (p for p in _trove_entries(sdir)
                        if p.is_dir() and p.name.upper().startswith("BGC")):
            bgc = bgc_dir.name
            bgc_entries = _trove_entries(bgc_dir)
            # (v9.7.344) try the channel's real per-gene filenames, in order, before giving up.
            src = None
            for pat in _TROVE_FILE_GLOBS.get(channel, ("{bgc}_top_hit_per_gene.csv", "*_top_hit_per_gene.csv")):
                pat = pat.format(bgc=bgc)
                if "*" in pat:
                    cand = [p for p in bgc_entries if fnmatch.fnmatch(p.name, pat)]
                    if cand:
                        src = cand[0]; break
                else:
                    p = bgc_dir / pat
                    if p.exists():
                        src = p; break
            if src is None:
                continue
            source_sha = _sha256(src)
            source_file = str(src.relative_to(troot))
            sources.append({"bgc": bgc, "file": source_file, "sha256": source_sha})
            new_rows = {}
            for row_number, r in enumerate(csv.DictReader(src.open(newline="", encoding="utf-8")), 2):
                keys, reason = _validate_ingest_row(r, package_strain, bgc, current)
                if reason:
                    rejected.append(_quarantine_row(
                        reason, channel, package_strain, bgc, keys, source_file,
                        source_sha, row_number, r,
                    ))
                    continue
                locus = keys["query_locus"]
                sci = _pick(r, _TROVE_ALIASES["blastp_organism"])
                pid = _pick(r, _TROVE_ALIASES["pct_identity"])
                # BC-378: this trove format is, by this function's own contract (see module
                # docstring), already the rank-1 (sole) hit per gene -- so every row here IS a
                # rank-1 hit. Passing hit_rank=1 arms _is_self_hit's XML-free fallback (v9.7.338 /
                # BLP-03): without it, a named genome's own protein (>=99% identity, no sciname
                # column in a CSV-only trove) silently survived into the overlay as a fabricated
                # comparator, inflating conservation_median_id exactly as that fallback exists to
                # prevent -- see write_nr_overlay's equivalent call, which already passes hit_rank.
                if _is_self_hit(sci, pid, self_binomial, hit_rank=1):
                    continue
                new_rows[locus] = {
                    "locus_tag": locus,
                    "aa_length": keys["query_aa_length"],
                    "antismash_domains": domains.get(locus, ""),
                    "blastp_top_def": _pick(r, _TROVE_ALIASES["blastp_top_def"]),
                    "blastp_accession": _pick(r, _TROVE_ALIASES["blastp_accession"]),
                    "blastp_organism": sci,
                    "pct_identity": pid,
                    "query_coverage": _pick(r, _TROVE_ALIASES["query_coverage"]),
                    "evalue": _pick(r, _TROVE_ALIASES["evalue"]),
                    "bitscore": _pick(r, _TROVE_ALIASES["bitscore"]),
                    "agreement": "",           # authored_verify recomputes vs antiSMASH
                    "channel": channel,
                    "query_strain": keys["query_strain"],
                    "query_bgc": keys["query_bgc"],
                    "query_locus": keys["query_locus"],
                    "query_aa_length": keys["query_aa_length"],
                    "source_channel": channel,
                    "source_file_sha256": source_sha,
                    "ingest_date": _dt.date.today().isoformat(),
                }
            plans.append((bgc, src, list(new_rows.values())))
            written[bgc] = len(new_rows)

    # Identity and all source-row guards have run before the first channel output is modified.
    overlay_payloads: dict[Path, str] = {}
    overlay_deletions: set[Path] = set()
    for bgc, _src, new_row_list in plans:
        new_rows = {row["locus_tag"]: row for row in new_row_list}
        # merge with any existing overlay, honouring channel precedence
        opath = outdir / f"{bgc}_online_blastp.csv"
        merged = {}
        if opath.exists():
            old_sha = _sha256(opath)
            old_file = f"existing_overlay/{opath.name}"
            old_rejected = False
            for row_number, r in enumerate(csv.DictReader(opath.open(newline="", encoding="utf-8")), 2):
                keys, reason = _validate_ingest_row(r, package_strain, bgc, current)
                if reason:
                    rejected.append(_quarantine_row(
                        reason, r.get("channel") or channel, package_strain, bgc,
                        keys, old_file, old_sha, row_number, r,
                    ))
                    old_rejected = True
                    continue
                if not r.get("source_file_sha256") or not r.get("source_channel"):
                    rejected.append(_quarantine_row(
                        "LEGACY_PROVENANCE_HOLD", r.get("channel") or channel,
                        package_strain, bgc, keys, old_file, old_sha, row_number, r,
                    ))
                    old_rejected = True
                    continue
                merged[r["locus_tag"]] = r
            if old_rejected:
                sources.append({"bgc": bgc, "file": old_file, "sha256": old_sha})
        for locus, row in new_rows.items():
            cur = merged.get(locus)
            if cur is None or _CHANNEL_RANK.get(channel, 0) >= _CHANNEL_RANK.get(cur.get("channel", ""), 0):
                merged[locus] = row
        if merged:
            import io as _io
            _buf = _io.StringIO(newline="")
            w = _SafeDictWriter(_buf, fieldnames=_OVERLAY_COLS, lineterminator="\n")
            w.writeheader()
            for locus in sorted(merged):
                row = merged[locus]
                w.writerow({k: row.get(k, "") for k in _OVERLAY_COLS})
            overlay_payloads[opath] = _buf.getvalue()
        elif opath.exists():
            # Never leave a header-only or stale legacy overlay looking like evidence.
            overlay_deletions.add(opath)

    _commit_text_file_set(pkg, overlay_payloads, overlay_deletions)

    quarantine_path, receipt_path = _write_guard_artifacts(
        pkg, channel, "overlay", package_strain, sources, written, rejected,
    )
    _update_ingest_ledger(
        outdir, channel, written, rejected, package_strain, sources, receipt_path,
    )
    return {"package": str(pkg), "channel": channel, "bgcs_written": written,
            "genes": sum(written.values()), "quarantined": len(rejected),
            "quarantine": quarantine_path, "receipt": receipt_path}


def _load_ingest_ledger(ledger_path: Path) -> dict:
    """Load an optional ledger, refusing unreadable or structurally unsafe content."""
    try:
        raw = ledger_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError as exc:
        raise BlastpIngestLedgerError(
            f"BLASTP_INGEST_LEDGER_HOLD: cannot read ingest ledger {ledger_path.name!r} "
            f"({type(exc).__name__})"
        ) from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BlastpIngestLedgerError(
            f"BLASTP_INGEST_LEDGER_HOLD: cannot read ingest ledger {ledger_path.name!r} "
            f"({type(exc).__name__})"
        ) from exc
    if not isinstance(data, dict):
        raise BlastpIngestLedgerError(
            f"BLASTP_INGEST_LEDGER_HOLD: ingest ledger {ledger_path.name!r} "
            "must contain a JSON object"
        )
    return data


def _update_ingest_ledger(store_dir: Path, channel: str, written: dict,
                          rejected: list[dict], strain: str, sources: list[dict],
                          receipt_path: str) -> None:
    """Record admitted and quarantined counts separately; zero-admission is incomplete."""
    led = store_dir / "_ingest_ledger.json"
    data = _load_ingest_ledger(led)
    ch = data.setdefault(channel, {})
    rejected_by_bgc: dict[str, int] = {}
    for row in rejected:
        bgc = row["destination_bgc"]
        rejected_by_bgc[bgc] = rejected_by_bgc.get(bgc, 0) + 1
    source_by_bgc: dict[str, list[str]] = {}
    for source in sources:
        source_by_bgc.setdefault(source["bgc"], []).append(source["sha256"])
    for bgc in sorted(set(written) | set(rejected_by_bgc)):
        admitted = int(written.get(bgc, 0))
        ch[bgc] = {
            "strain": strain,
            "admitted_rows": admitted,
            "quarantined_rows": int(rejected_by_bgc.get(bgc, 0)),
            "evidence_complete": admitted > 0,
            "source_sha256": sorted(source_by_bgc.get(bgc, [])),
            "receipt": Path(receipt_path).name,
        }
    led.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(led, json.dumps(data, indent=2, sort_keys=True) + "\n")


def read_ingest_ledger(package: str | Path) -> dict:
    """{channel: {bgc: {...}}} of what has been ingested into this package. Empty if none."""
    led = Path(package) / "blastp_online" / "_ingest_ledger.json"
    return _load_ingest_ledger(led)


# v9.7.344: BLASTp lives INSIDE the package as FOUR SEPARATE, UNMIXED, named channel stores
# (the Developer or User directive 2026-07-31). No cross-channel precedence merge — each channel keeps its own
# top-10 hits per gene, with BOTH pct_identity AND pct_positives (similarity). Portable: the
# package is self-contained.
CHANNEL_STORE = {"nr": "blastp_nr", "clustered_nr": "blastp_clustered_nr",
                 "swissprot": "blastp_swissprot", "ebi": "blastp_ebi"}
_TOP10_GLOBS = {
    "nr": ("{bgc}_blastp_top10.csv", "*_blastp_top10.csv"),
    "clustered_nr": ("{bgc}_blastp_top10_clustered.csv", "*_blastp_top10_clustered.csv"),
    "swissprot": ("{bgc}_blastp_top10_local.csv", "*_blastp_top10_local.csv"),
    # (v9.7.374) the trailing "*_blastp_top10*.csv" catch-all removed: it is a strict SUPERSET of
    # the "nr" channel's own patterns above ({bgc}_blastp_top10.csv / *_blastp_top10.csv), so an
    # ebi-channel install pointed at a directory holding only an nr-shaped top10 file silently
    # ingested nr's hits and labeled them "ebi" in the unmixed blastp_ebi/ store -- exactly the
    # ClusteredNR-is-not-nr / channel-provenance violation this four-store architecture (v9.7.344)
    # exists to prevent. ebi's remaining two patterns already require "ebi" in the filename, same
    # as every other channel requires its own name; no catch-all is needed or safe here.
    "ebi": ("{bgc}_blastp_top10_ebi.csv", "*_ebi*top10*.csv"),
}
_TOP10_COLS = ["strain", "bgc_id", "gene", "aa_length", "role", "hit_rank", "subject_acc",
               "subject_organism", "subject_def", "pct_identity", "pct_positives",
               "query_coverage", "evalue", "bitscore", "channel", "query_strain",
               "query_bgc", "query_locus", "query_aa_length", "source_file_sha256",
               "ingest_date"]


def install_channel_top10(package: str | Path, trove_dir: str | Path, channel: str,
                          strain: str | None = None) -> dict:
    """Install a channel's per-BGC TOP-10 hit tables into the package as an unmixed store
    <pkg>/blastp_<channel>/<BGC>_top10.csv (keeps pct_identity + pct_positives; all 10 ranks).
    Also records the ledger so the BLASTp gate is satisfied. Non-scoring / reader-side."""
    if channel not in CHANNEL_STORE:
        raise ValueError(f"channel must be one of {sorted(CHANNEL_STORE)}; got {channel!r}")
    pkg = Path(package)
    _recover_fileset_transactions(pkg)
    package_strain = _package_strain(pkg, strain)
    current = _current_locus_lengths(pkg)
    store = pkg / CHANNEL_STORE[channel]
    troot = Path(trove_dir)
    # robust strain-dir finding (tolerates an intermediate level like '_NR_RID/results/<strain>/')
    from .blastp_gate import _strain_dirs_in
    strain_dirs = _strain_dirs_in(troot, package_strain)
    if not strain_dirs:
        direct_strain = troot / package_strain
        if direct_strain.is_dir():
            strain_dirs = [direct_strain]
        else:
            root_entries = _trove_entries(troot)
            strain_dirs = ([d for d in root_entries if d.is_dir()]
                           if not any(d.is_dir() and d.name.upper().startswith("BGC")
                                      for d in root_entries) else [troot])
    written: dict[str, int] = {}
    rejected: list[dict] = []
    sources: list[dict] = []
    plans: list[tuple[str, list[dict]]] = []
    for sdir in strain_dirs:
        for bgc_dir in (p for p in _trove_entries(sdir) if p.is_dir()
                        and p.name.upper().startswith("BGC")):
            bgc = bgc_dir.name
            bgc_entries = _trove_entries(bgc_dir)
            src = None
            for pat in _TOP10_GLOBS.get(channel, ("*_blastp_top10*.csv",)):
                pat = pat.format(bgc=bgc)
                cand = [p for p in bgc_entries if fnmatch.fnmatch(p.name, pat)] if "*" in pat else \
                    ([bgc_dir / pat] if (bgc_dir / pat).exists() else [])
                if cand:
                    src = cand[0]; break
            if src is None:
                continue
            source_sha = _sha256(src)
            source_file = str(src.relative_to(troot))
            sources.append({"bgc": bgc, "file": source_file, "sha256": source_sha})
            rows: list[dict] = []
            for row_number, r in enumerate(csv.DictReader(src.open(newline="", encoding="utf-8")), 2):
                keys, reason = _validate_ingest_row(r, package_strain, bgc, current)
                if reason:
                    rejected.append(_quarantine_row(
                        reason, channel, package_strain, bgc, keys, source_file,
                        source_sha, row_number, r,
                    ))
                    continue
                out = {k: r.get(k, "") for k in _TOP10_COLS}
                out.update({
                    "strain": package_strain, "bgc_id": bgc,
                    "gene": keys["query_locus"], "aa_length": keys["query_aa_length"],
                    "channel": channel, "query_strain": keys["query_strain"],
                    "query_bgc": keys["query_bgc"], "query_locus": keys["query_locus"],
                    "query_aa_length": keys["query_aa_length"],
                    "source_file_sha256": source_sha,
                    "ingest_date": _dt.date.today().isoformat(),
                })
                rows.append(out)
            plans.append((bgc, rows))
            written[bgc] = len(rows)

    store_payloads: dict[Path, str] = {}
    store_deletions: set[Path] = set()
    for bgc, rows in plans:
        if not rows:
            # An all-rejected source must not leave a stale channel file that looks complete.
            stale = store / f"{bgc}_top10.csv"
            if stale.exists():
                store_deletions.add(stale)
            continue
        import io as _io
        _buf = _io.StringIO(newline="")
        w = _SafeDictWriter(_buf, fieldnames=_TOP10_COLS, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in sorted(rows, key=lambda x: (x.get("gene", ""),
                                              _positive_int(x.get("hit_rank")) or 0,
                                              x.get("subject_acc", ""))):
            w.writerow({k: r.get(k, "") for k in _TOP10_COLS})
        store_payloads[store / f"{bgc}_top10.csv"] = _buf.getvalue()

    _commit_text_file_set(pkg, store_payloads, store_deletions)

    quarantine_path, receipt_path = _write_guard_artifacts(
        pkg, channel, "top10", package_strain, sources, written, rejected,
    )
    _update_ingest_ledger(
        pkg / "blastp_online", channel, written, rejected, package_strain, sources,
        receipt_path,
    )
    return {"package": str(pkg), "channel": channel, "store": str(store),
            "bgcs": sum(1 for n in written.values() if n > 0),
            "hits": sum(written.values()), "quarantined": len(rejected),
            "quarantine": quarantine_path, "receipt": receipt_path}


def blastp_status(package: str | Path) -> list[dict]:
    """Per-BGC overlay coverage audit — the single retrieval entry point.
    Returns [{bgc, channels, genes, path, armed}]; armed False => ClusterBlast fallback."""
    pkg = Path(package); outdir = pkg / "blastp_online"
    rows = []
    try:
        entries = list(outdir.iterdir())
    except (FileNotFoundError, NotADirectoryError):
        entries = []
    except OSError as exc:
        raise BlastpOverlayReadError(
            f"BLASTP_OVERLAY_READ_HOLD: cannot traverse overlay store "
            f"({type(exc).__name__})"
        ) from exc
    bgcs = sorted({p.name.split("_online_blastp")[0] for p in entries
                   if p.is_file() and p.name.endswith("_online_blastp.csv")})
    for bgc in bgcs:
        p = outdir / f"{bgc}_online_blastp.csv"
        recs = list(csv.DictReader(p.open(newline="")))
        chans = sorted({r.get("channel", "") for r in recs if r.get("channel")})
        rows.append({"bgc": bgc, "channels": ";".join(chans) or "?", "genes": len(recs),
                     "path": str(p), "armed": bool(recs)})
    return rows


_LOCUS_RE = re.compile(r"(ctg\d+_\d+)")  # full locus tag: contig index + gene index


def _gene_from_query(qid: str) -> str:
    """Recover the gene locus tag from a panel query title.

    Fast path: an explicit ``gene=`` token (`...|gene=ctg66_8|...`) — standard panels.
    TROVE-01 fallback (v9.7.340): a bare pipe/space defline WITHOUT ``gene=`` — e.g.
    ``AS-XXX|BGC041|ctg66_8|3116`` (the pre-organized trove format `ingest-blastp-trove` reads) —
    recover the `ctg<N>_<M>` locus rather than returning the whole defline as the "gene", which
    fragments the per-gene merge. A `NODE_..._length_..._cov_...` header carries no `ctg<N>_<M>`
    and is returned unchanged (guarded)."""
    m = re.search(r"gene=([^|\s]+)", qid)
    if m:
        return m.group(1)
    m2 = _LOCUS_RE.search(qid or "")
    return m2.group(1) if m2 else qid


def _aa_from_query(qid: str, fallback: str = "") -> str:
    """Recover the query length from a panel defline (`...|aa=420|...`). XML enrichment is
    optional, so `query_len` is often blank; the defline always carries aa=."""
    m = re.search(r"\baa=(\d+)", qid)
    return m.group(1) if m else str(fallback or "")


def _coverage(row: dict) -> str:
    try:
        qlen = float(row.get("query_len") or _aa_from_query(row.get("query_locus", "")) or 0)
        if qlen <= 0:
            return ""
        span = abs(int(row["q_end"]) - int(row["q_start"])) + 1
        return f"{100.0 * span / qlen:.1f}"
    except (ValueError, TypeError, KeyError):
        return ""


def _domains_by_locus(pkg: Path) -> dict[str, str]:
    """locus_tag -> `; `-joined antiSMASH sec_met domains, from the sealed gene_context.jsonl.

    v9.7.241 (P7b). The overlay's `antismash_domains` column was hardcoded to "", so
    `reconcile()` could only ever return REVIEW and the `agreement` column was a constant.
    The package already carries the domains; join on the panel defline's `gene=` token.
    A genuinely missing optional gene context yields {}; an existing unreadable context or
    package traversal failure raises a typed hold before overlay output.
    """
    out: dict[str, str] = {}
    gc = next(iter(_package_matches(pkg, "*gene_context.jsonl")), None)
    if gc is None:
        return out
    try:
        with gc.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec = json.loads(line)
                for cds in rec.get("cds", []) or []:
                    lt = cds.get("locus_tag")
                    if lt:
                        out[lt] = "; ".join(cds.get("sec_met_domains") or [])
    except (OSError, ValueError) as exc:
        raise ValueError(
            f"BLASTP_GENE_CONTEXT_HOLD: cannot read existing gene context {gc.name!r} "
            f"({type(exc).__name__})"
        ) from exc
    return out



def _self_binomial(package) -> str | None:
    """v9.7.252: the query genome's own binomial, lowercased, or None.

    A deposited type strain or reference genome has its OWN proteins in nr, so the rank-1 hit for most
    genes is the query genome itself at ~100% identity. That drives `conservation_median_id` to 100 --
    the input to `scan_divergence` and to the `NOVELTY_CONTRADICTION` guard -- so arming the overlay,
    the very act meant to improve the evidence, silently INVERTS the divergence signal.

    Returns None for an unnamed species ("Micromonospora sp. AS-XXX", "Streptomyces sp."): "genus sp."
    is not a binomial, and treating it as one would exclude every unnamed congener in nr. Every
    AS-series strain is unnamed, so nothing is excluded for them.
    """
    man = _read_optional_package_manifest(package)
    if man is None:
        return None
    # v9.7.412 (F10): prefer `taxonomy` (the binomial the genome hits itself under in nr) over
    # `display_name`, which is often "<Genus> <StrainCode>" and masked the binomial -> None ->
    # the genome's own 100% self-hit survived and drove conservation_median_id to 100.
    for name in (str(man.get("taxonomy") or "").strip(), str(man.get("display_name") or "").strip()):
        toks = name.replace("(", " ").split()
        if len(toks) < 2:
            continue
        genus, species = toks[0], toks[1].strip(".,")
        if not genus[:1].isupper() or not species.islower() or not species.isalpha():
            continue
        if species in ("sp", "spp", "cf", "aff"):
            continue
        return f"{genus} {species}".lower()
    return None


def _is_self_hit(sciname, pct_identity, self_binomial, hit_rank=None) -> bool:
    """A hit is the query genome itself when the subject's binomial equals the query's AND identity
    is >= 99.0%. A same-species hit from a DIFFERENT strain at moderate identity (e.g. 92%) is a real
    comparator and is retained -- that is the whole point of the identity floor.

    v9.7.338 (BLP-03): `sciname` only lands from the alignment XML. A named type strain ingested
    CSV-only (HitTable, no XML) therefore has an EMPTY sciname on every row, so the binomial check
    could never fire and the genome's own rank-1 100% self-hit survived -- inflating
    conservation_median_id toward 100 exactly as v9.7.252 set out to prevent. XML-free fallback:
    when the query genome is NAMED (self_binomial set) but the row carries no sciname, drop a
    RANK-1 hit at >= 99.0% identity as a probable self-hit. Restricted to rank-1 (where the genome's
    own protein sits) so a lower-ranked same-species comparator is retained. Moot for AS `sp.`
    strains (self_binomial is None -> returns False immediately, nothing excluded)."""
    if not self_binomial:
        return False
    if sciname:
        toks = str(sciname).split()
        if len(toks) < 2:
            return False
        if f"{toks[0]} {toks[1].strip('.,')}".lower() != str(self_binomial).lower():
            return False
        return _finite_evidence_number(pct_identity, "pct_identity") >= 99.0
    # XML-free fallback: no organism string on the row (CSV-only ingest of a named genome).
    if hit_rank is None:
        return False
    try:
        rank = int(hit_rank)
    except (TypeError, ValueError) as exc:
        raise BlastpNumericEvidenceError(
            f"BLASTP_NUMERIC_EVIDENCE_HOLD: invalid hit_rank {hit_rank!r}"
        ) from exc
    return rank == 1 and _finite_evidence_number(pct_identity, "pct_identity") >= 99.0


def write_nr_overlay(package: str | Path, rows: list[dict]) -> dict:
    """Write one <BGC>_online_blastp.csv per BGC into <package>/blastp_online/ from
    ingested B5 rows. Best hit per query gene only (hit_rank == 1). Fail-open: rows with
    no resolvable BGC are skipped, never invented. Returns {bgcs, genes, outdir}.

    v9.7.241 (P7a): **MERGES** with any existing overlay instead of truncating it. The
    documented workflow splits a strain's proteins into rounds (`bgc-blastp-panel` emits
    one FASTA per round) and NCBI returns one Hit Table per round, so a campaign calls
    `ingest-blastp` once per round. The previous `open("w")` made that last-round-wins:
    on a real 35-round AS-XXX campaign the overlay retained **557 of 1,002 genes**, and for
    BGC017 it kept 23 of 48 -- dropping the 4,071 aa megasynthase and biasing
    `conservation_median_id` from a true 84.8% to 96.7%. That median is the input to the
    `NOVELTY_CONTRADICTION` guard this overlay was added (in v9.7.239) to arm, so the guard
    was being armed with a biased subset. Higher bitscore wins on a locus_tag collision.
    """
    pkg = Path(package)
    _recover_fileset_transactions(pkg)
    outdir = pkg / "blastp_online"
    dom_by_lt = _domains_by_locus(pkg)

    def _bits(rec: dict) -> float:
        return _finite_evidence_number(rec.get("bitscore"), "bitscore")

    # v9.7.252: rank-1 is no longer assumed informative. On a deposited genome rank-1 is the genome
    # itself; the informative comparator sits one rank down (observed: ctg7_50 rank-1 self @100.000%,
    # rank-2 77.3% to Nocardia sp. NPDC058633). Consider every rank, drop self-hits, keep the best
    # remaining by bitscore. With no self-hits this reduces exactly to the old rank-1 selection,
    # because rank-1 carries the highest bitscore -- the P7a contract is preserved.
    _self = _self_binomial(package)
    # v9.7.338 (BLP-03): record whether any row carries an organism string (XML enrichment). With
    # a named query genome and NO sciname anywhere, self-exclusion runs on the rank-1 heuristic and
    # provenance flags that XML was unavailable rather than silently leaving self-hits in.
    _has_sciname = any(str(r.get("sciname", "")).strip() for r in rows)
    self_excluded = 0
    self_excluded_heuristic = 0
    per_bgc: dict[str, dict[str, dict]] = {}
    for r in rows:
        _sci = r.get("sciname", "")
        if _is_self_hit(_sci, r.get("pct_identity", ""), _self, hit_rank=r.get("hit_rank")):
            self_excluded += 1
            if not str(_sci).strip():
                self_excluded_heuristic += 1
            continue
        bgc = (r.get("BGC_ID") or "").strip()
        if not bgc:
            continue
        lt = _gene_from_query(r.get("query_locus", ""))
        doms = dom_by_lt.get(lt, "")
        desc = r.get("subject_desc", "")
        rec = {
            "locus_tag": lt,
            "aa_length": _aa_from_query(r.get("query_locus", ""), r.get("query_len", "")),
            "antismash_domains": doms,
            "blastp_top_def": desc,
            "blastp_accession": r.get("subject_acc", ""),
            "blastp_organism": r.get("sciname", ""),
            "pct_identity": r.get("pct_identity", ""),
            "query_coverage": _coverage(r),
            "evalue": r.get("evalue", ""),
            "bitscore": r.get("bitscore", ""),
            "agreement": _reconcile(doms, desc) if desc else "",
            "channel": "nr",
            "source_channel": "nr",
        }
        _bits(rec)
        slot = per_bgc.setdefault(bgc, {})
        if lt not in slot or _bits(rec) > _bits(slot[lt]):
            slot[lt] = rec

    # merge with what is already on disk from earlier rounds
    for bgc, slot in per_bgc.items():
        path = outdir / f"{bgc}_online_blastp.csv"
        if path.exists():
            try:
                with path.open(encoding="utf-8") as fh:
                    for old_rec in csv.DictReader(fh):
                        lt = (old_rec.get("locus_tag") or "").strip()
                        if not lt:
                            continue
                        if lt not in slot or _bits(old_rec) > _bits(slot[lt]):
                            slot[lt] = {c: old_rec.get(c, "") for c in _OVERLAY_COLS}
            except (OSError, csv.Error) as exc:
                raise BlastpOverlayReadError(
                    f"BLASTP_OVERLAY_READ_HOLD: cannot merge existing overlay {path.name!r} "
                    f"({type(exc).__name__}); existing evidence was preserved"
                ) from exc

    genes = 0
    overlay_payloads: dict[Path, str] = {}
    for bgc, slot in per_bgc.items():
        recs = sorted(slot.values(), key=lambda x: x["locus_tag"])
        genes += len(recs)
        import io as _io
        _buf = _io.StringIO(newline="")
        w = _SafeDictWriter(_buf, fieldnames=_OVERLAY_COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(recs)
        overlay_payloads[outdir / f"{bgc}_online_blastp.csv"] = _buf.getvalue()
    _commit_text_file_set(pkg, overlay_payloads)
    _self_mode = ("not_applicable" if not _self
                  else ("binomial_confirmed" if _has_sciname else "rank1_heuristic_no_xml"))
    return {"bgcs": len(per_bgc), "genes": genes, "outdir": str(outdir),
            "self_hits_excluded": self_excluded,
            "self_hits_excluded_heuristic": self_excluded_heuristic,
            "self_exclusion_mode": _self_mode,
            "self_exclusion_xml_available": _has_sciname}


_B5_KEY_COLS = ("strain", "query_locus", "subject_acc", "hit_rank", "q_start", "q_end")



def _manual_locus(qid: str) -> str:
    """Locus tag of a manual-ingest query id: `...|gene=ctg5_1136|...`, `BGC027_ctg5_1136`, `ctg5_1136`."""
    m = re.search(r"\bgene=([^|\s]+)", qid or "")
    if m:
        return m.group(1)
    m = re.search(r"(ctg\d+_\d+)", qid or "")
    if m:
        return m.group(1)
    return re.sub(r"^BGC\d+[_|]", "", (qid or "").split("|")[-1]).strip()


def _manual_binding_guard(package: Path, strain: str, rows: list[dict], csv_path: Path) -> tuple[list[dict], dict]:
    """v9.7.412 (DEEP_AUDIT2_blastp_ingest F1/F2/F3/F5-F7): the manual `ingest-blastp` overlay path
    applied NONE of the trove path's guards, so a wrong-BGC, phantom-BGC or physically impossible row
    wrote straight into <package>/blastp_online/ -- the file authored_verify / genome_explore trust for
    conservation_median_id and NOVELTY_CONTRADICTION. Returns (admitted_rows, guard_summary).

    Fails OPEN only when the package carries no sealed context (no strain_id, no gene context): such a
    legacy package cannot be cross-checked and keeps the pre-.412 behaviour, flagged binding_validated=False.
    Refuses (ValueError) a --strain that contradicts the package manifest BEFORE anything is written."""
    man = _read_optional_package_manifest(package) or {}
    man_strain = str(man.get("strain_id") or "").strip()
    if man_strain and strain and man_strain != strain:
        raise ValueError(f"--strain {strain!r} conflicts with package manifest strain_id {man_strain!r}; refusing to ingest")
    try:
        current = _current_locus_lengths(package)
    except ValueError:
        # Missing legacy context and corrupt/ambiguous supplied context differ.
        # Do not turn the authoritative reader's rejection into admission.
        if (_package_matches(package, "*gene_context.jsonl")
                or _package_matches(package, "*gene_by_gene_all_bgcs.csv")):
            raise
        return rows, {"binding_validated": False, "quarantined": 0, "admitted": len(rows), "quarantine": "", "receipt": ""}
    sha = _sha256(csv_path)
    admitted: list[dict] = []; quarantined: list[dict] = []; admitted_by_bgc: dict[str, int] = {}
    for i, row in enumerate(rows, 1):
        bgc = (row.get("BGC_ID") or "").strip()
        if not bgc:
            admitted.append(row); continue  # unbound rows are already skipped by write_nr_overlay
        locus = _manual_locus(row.get("query_locus", ""))
        cur_aa = current.get(bgc, {}).get(locus)
        keys = {"query_strain": strain, "query_bgc": bgc, "query_locus": locus,
                "query_aa_length": str(row.get("query_len") or ""), "current_aa_length": str(cur_aa or "")}
        reason = ""
        if bgc not in current:
            reason = "FOREIGN_BGC"
        elif cur_aa is None:
            reason = "NONCURRENT_LOCUS"
        elif row.get("_bad_numeric"):
            reason = "NONNUMERIC_EVALUE" if "evalue" in str(row["_bad_numeric"]).split(",") else "NONNUMERIC_FIELD"
        elif any(
            _positive_int(value) != cur_aa
            for value in (
                row.get("query_len"),
                _aa_from_query(row.get("query_locus", "")),
            )
            if value is not None and str(value).strip()
        ):
            # Each supplied length is independently rejection-only. A matching
            # defline must not hide a contradictory XML length, or vice versa.
            reason = "QUERY_CURRENT_AA_LENGTH_MISMATCH"
        else:
            try:
                pid = float(row.get("pct_identity"))
                if not (0.0 <= pid <= 100.0):
                    reason = "IMPOSSIBLE_PCT_IDENTITY"
            except (TypeError, ValueError):
                reason = "NONNUMERIC_FIELD"
            if not reason:
                try:
                    if int(float(row.get("align_len") or 0)) > int(cur_aa) * 2:
                        reason = "HIT_LONGER_THAN_QUERY"  # allow gapped alignments up to 2x; 999999 vs 300 is impossible
                except (TypeError, ValueError):
                    reason = "NONNUMERIC_FIELD"
        if reason:
            quarantined.append(_quarantine_row(reason, "nr_manual", strain, bgc, keys, csv_path.name, sha, i,
                                               {k: v for k, v in row.items() if not str(k).startswith("_")}))
        else:
            admitted.append(row); admitted_by_bgc[bgc] = admitted_by_bgc.get(bgc, 0) + 1
    qpath = rpath = ""
    if quarantined:
        qpath, rpath = _write_guard_artifacts(package, "nr_manual", "hittable", strain,
                                              [{"bgc": "*", "file": csv_path.name, "sha256": sha}],
                                              admitted_by_bgc, quarantined)
    return admitted, {"binding_validated": True, "quarantined": len(quarantined), "admitted": len(admitted),
                      "quarantine": qpath, "receipt": rpath}

def _b5_key(row: dict) -> tuple:
    """Identity of a B5 hit row. v9.7.241 (P7c)."""
    return tuple(str(row.get(c, "")).strip() for c in _B5_KEY_COLS)


def _existing_b5_keys(ws) -> set:
    """Keys already present in an open, canonical B5 worksheet."""
    try:
        header = [str(c.value or "").strip() for c in next(ws.iter_rows(min_row=1, max_row=1))]
    except StopIteration as exc:
        raise BlastpStoreSchemaError(
            "BLASTP_B5_SCHEMA_HOLD: existing B5_BLASTp_Hits sheet has no header"
        ) from exc
    try:
        idx = [header.index(c) for c in _B5_KEY_COLS]
    except ValueError as exc:
        raise BlastpStoreSchemaError(
            "BLASTP_B5_SCHEMA_HOLD: existing B5_BLASTp_Hits sheet lacks dedupe key columns"
        ) from exc
    keys = set()
    for row in ws.iter_rows(min_row=2, values_only=True):
        if row is None:
            continue
        if len(row) <= max(idx):
            raise BlastpStoreSchemaError(
                "BLASTP_B5_SCHEMA_HOLD: existing B5_BLASTp_Hits row is truncated"
            )
        keys.add(tuple(str(row[i] if row[i] is not None else "").strip() for i in idx))
    return keys


def ingest_blastp(master_path: str | Path, strain: str, csv_path: str | Path,
                  xml_path: str | Path | None = None, top_n: int = 10,
                  package: str | Path | None = None, source: str = "NCBI web-BLASTp") -> dict:
    """Append BLASTp hits to B5_BLASTp_Hits in an existing master workbook. Returns a summary
    dict {rows, queries, bgcs, enriched}. Creates B5 (with header) if absent.

    ``source`` (default "NCBI web-BLASTp", unchanged) is stamped into every row's ``source``
    column verbatim — pass a transport-accurate value (e.g. "EBI (uniprotkb_bacteria)") for a
    non-NCBI HitTable so B5_BLASTp_Hits never mislabels its provenance."""
    import openpyxl
    from .master_workbook import CANONICAL_V1_HEADERS as _SHEET_HEADERS, _append_row_by_header

    _xml_status: dict = {}
    # v9.7.412: under a package the binding guard quarantines defective rows (numeric_policy="flag");
    # without one the parser keeps its whole-input rejection.
    rows = build_b5_rows(strain, csv_path, xml_path, top_n=top_n, source=source,
                         enrich_status=_xml_status, numeric_policy="flag" if package else "reject")
    if package:
        rows, _guard = _manual_binding_guard(Path(package), strain, rows, Path(csv_path))
    else:
        _guard = {"binding_validated": False, "quarantined": 0, "admitted": len(rows), "quarantine": "", "receipt": ""}
    from .xlsx_determinism import guard_workbook_size as _guard_xlsx  # v9.7.410: inflation cap before a full load
    _guard_xlsx(master_path)
    try:
        wb = openpyxl.load_workbook(master_path)
    except Exception as _exc:  # v9.7.409 (BC hostile audit H15): a garbage --master traced back from openpyxl's zip validator
        raise SystemExit(f"ingest-blastp: master workbook unreadable ({type(_exc).__name__}: {_exc}): {master_path}")
    if "B5_BLASTp_Hits" not in wb.sheetnames:
        ws = wb.create_sheet("B5_BLASTp_Hits")
        ws.append(_SHEET_HEADERS["B5_BLASTp_Hits"])
    ws = wb["B5_BLASTp_Hits"]

    # v9.7.241 (P7c): B5 append was not idempotent. Ingesting the same Hit Table twice
    # duplicated every row (150 -> 300 on a real AS-XXX round), and a 35-round campaign
    # re-run after a failure silently doubled the sheet. Nothing downstream deduplicates.
    # Skip rows already present, keyed on the identity of a hit.
    existing = _existing_b5_keys(ws)
    fresh = [r for r in rows if _b5_key(r) not in existing]
    skipped = len(rows) - len(fresh)
    for r in fresh:
        _append_row_by_header(ws, r)
    _save_wb_safely(wb, master_path)

    # The overlay is written from ALL parsed rows, not just the fresh ones: it is a
    # merge-by-locus_tag view (write_nr_overlay), so re-ingesting a round is a no-op there
    # and a first ingest after a partial failure still repairs the file.
    overlay = write_nr_overlay(package, rows) if package else None
    return {
        "rows": len(fresh),
        "duplicates_skipped": skipped,
        "queries": len({r["query_locus"] for r in rows}),
        "bgcs": len({r["BGC_ID"] for r in rows if r["BGC_ID"]}),
        # v9.7.410: rows parsed from the HitTable regardless of dedup, and how many of them bound
        # a BGC. The CLI warns when parsed > 0 and bgcs == 0 (a silent 0-BGC ingest, see
        # CLAUDE_410_blastp_bgc_recovery_409); a re-ingest of an already-loaded round reports
        # rows=0 but still has parsed > 0, so the warning is keyed on parsed, not fresh.
        "rows_parsed": len(rows),
        "rows_unbound": sum(1 for r in rows if not r["BGC_ID"]),
        # v9.7.410: truthful — True only when the XML actually yielded queries (see _load_enrichment).
        "enriched": _xml_status.get("xml") == "ok",
        "xml_status": _xml_status.get("xml", "absent"),
        "overlay": overlay,
        "binding_guard": _guard,  # v9.7.412
    }
