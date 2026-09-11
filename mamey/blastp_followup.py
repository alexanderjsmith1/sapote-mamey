"""Iterative BLASTP result ingestion and follow-up batch planning.

This module is intentionally offline-first. It does not call NCBI. Users run
NCBI web BLASTP manually, download Hit Table CSV first, and only provide XML2
when proof-grade coverage/identity details or hit titles are needed.
"""
from __future__ import annotations

try:  # pragma: no cover - import shape depends on package vs direct-script use
    from .console import emit
except ImportError:  # direct execution: no parent package to resolve against.
    # v9.7.407: a bare-script run (documented for workbook_schema_check.py) has neither a
    # parent package NOR the bundle root on sys.path, so put the root there first.
    import os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from mamey.console import emit

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter  # v9.7.409 export-injection: CSV formula-cell guard
except ImportError:  # module loaded by file path without a parent package (tests do this)
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter
import io
import json
import os
import re
import xml.etree.ElementTree as ET
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .bgc_blastp_panel import fasta_header, wrap_fasta

HIT_TABLE_COLUMNS = [
    "query_id", "subject_id", "pct_identity", "align_len", "mismatches",
    "gap_opens", "qstart", "qend", "sstart", "send", "evalue",
    "bitscore", "pct_positive",
]

STRONG_PRODUCT_TERMS = (
    "phosphonate", "phosphoenolpyruvate mutase", "pep mutase", "hpn", "hopene",
    "presqualene", "hydroxysqualene", "capreomycin", "halogenase",
    "glycosyltransferase", "dehydroxylase",
)

PRODUCT_RELEVANT_TERMS = (
    "phosphonate", "phosphoenolpyruvate mutase", "pep mutase", "hpn", "hopene",
    "presqualene", "hydroxysqualene", "capreomycin", "non-ribosomal", "nonribosomal",
    "nrps", "polyketide", "ketosynthase", "ketoacyl", "halogenase",
    "glycosyltransferase", "lanthipeptide", "lassopeptide", "tomm", "thiopeptide",
    "nucleoside", "siderophore", "resistance", "self-resistance", "transporter",
    "abc transporter", "regulator", "histidine kinase", "response regulator", "p450",
    "cytochrome", "dehydroxylase", "adenylation", "condensation",
)

COMMON_REDUNDANT_TERMS = (
    "abc transporter", "substrate-binding protein", "permease", "cytochrome p450",
    "beta-ketoacyl", "dehydrogenase", "histidine kinase", "hypothetical protein",
    "domain-containing protein", "family protein",
)

UNINFORMATIVE_TERMS = ("hypothetical protein", "uncharacterized", "unknown protein")

CLAIM_SAFETY = (
    "BLASTP evidence is sequence similarity only; it does not prove compound "
    "identity, pathway completeness, expression, or bioactivity."
)


@dataclass(frozen=True)
class HitRecord:
    query_id: str
    subject_id: str
    pct_identity: float
    align_len: int
    mismatches: int
    gap_opens: int
    qstart: int
    qend: int
    sstart: int
    send: int
    evalue: str
    bitscore: float
    pct_positive: float | None = None
    query_len: int | None = None
    subject_title: str = ""
    subject_accession: str = ""
    subject_sciname: str = ""
    subject_taxid: str = ""
    hit_len: int | None = None

    @property
    def query_coverage(self) -> float | None:
        # BLP-04 (v9.7.338): when the query length is genuinely unknown, DO NOT fall back to the
        # alignment extent (max(qstart, qend, align_len)) as the denominator — align_len / align_len
        # forces coverage to ~1.0 and fabricates near-full coverage on exactly the hits where we
        # know the least. Report unknown coverage as None (emitted as "NA"), never a false 1.0.
        qlen = self.query_len or query_len_from_id(self.query_id)
        if not qlen:
            return None
        return min(1.0, self.align_len / qlen)


def _cov_str(cov: float | None, places: int = 3) -> str:
    """Format a query-coverage value for emission; unknown coverage (None) -> "NA" (BLP-04)."""
    return "NA" if cov is None else f"{cov:.{places}f}"


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        return float(str(x).strip())
    except Exception:
        return default


def _safe_float_or_none(x: Any) -> float | None:
    """Like _safe_float but returns None (not a poison sentinel) on parse failure, so a
    malformed column never becomes a fabricated numeric value downstream. v9.7.371 fix: the
    pct_positive call site used _safe_float(x, default=-1.0) -- a *value*, not a None-checkable
    sentinel -- so a column misalignment (this file's own documented NCBI-CSV quoting edge case)
    silently became a fabricated -1.0 percent, rendered verbatim as '-1.00%' in reader-facing
    output instead of the 'NA' that _cov_str() already gives the equivalent coverage field."""
    try:
        return float(str(x).strip())
    except Exception:
        return None


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(float(str(x).strip()))
    except Exception:
        return default


def _text(x: Any) -> str:
    return re.sub(r"\s+", " ", str(x or "")).strip()


def parse_query_id(query_id: str) -> dict[str, str]:
    """Parse Sapote/Mamey FASTA header metadata from a BLASTP query id/title.

    Two header conventions are supported:

    1. Pipe-delimited (this bundle's own ``bgc_blastp_panel`` emission), e.g.
       ``strain|BGC002|slot=1|gene=ctg11_9|node=NODE_11|aa=317|...``.
    2. Space-delimited ``key=value`` (the convention used by manually-built
       NCBI BLASTP rounds, e.g. ``BGC008_ctg162_3 contig=NODE_162 node=NODE_162
       start=2859 end=3950 strand=+ kind=biosynthetic sec_met_domain=[...]``).
       Here the first whitespace token carries a combined ``BGC<n>_<gene>``
       identifier (PATCH-001).

    The two are disambiguated by the presence of a ``|``: a header with no
    pipe is parsed via the whitespace path so ``bgc_id``/``gene`` are still
    populated (without which ``merge_hit_xml``'s fallback match degenerates to
    ``None == None`` and silently mis-binds XML metadata — PATCH-001).
    """
    q = _text(query_id).lstrip(">")
    out: dict[str, str] = {"query_id": q}

    if "|" in q:
        parts = q.split("|")
        if parts:
            out["strain"] = parts[0]
        if len(parts) > 1 and parts[1].startswith("BGC"):
            out["bgc_id"] = parts[1]
        for part in parts[2:]:
            if "=" in part:
                k, v = part.split("=", 1)
                out[k.strip()] = v.strip()
            elif part.startswith("BGC") and "bgc_id" not in out:
                out["bgc_id"] = part
            elif part.startswith("NODE") and "node" not in out:
                out["node"] = part
            elif part.startswith("region") and "region" not in out:
                out["region"] = part
            elif "gene" not in out and ("_" in part or part.startswith("ctg")):
                out["gene"] = part
    else:
        # Space-delimited key=value convention (PATCH-001). The leading token
        # is a combined BGC+gene identifier; the remainder are key=value pairs
        # drawn from the same vocabulary as the pipe path (node=, region=,
        # start=, end=, strand=, kind=, aa=, etc.).
        tokens = q.split()
        if tokens:
            head = tokens[0]
            m = re.match(r"^(BGC\d+)_(\S+)$", head)
            if m:
                out["bgc_id"] = m.group(1)
                out["gene"] = m.group(2)
            elif head.startswith("BGC"):
                out["bgc_id"] = head
            # else: a first token that is neither BGC###_<gene> nor BGC###
            # is not a strain name — leave strain blank rather than guess
            # (honest-blank: the same standard applied to the combined-token
            # case; real manual headers always lead with BGC###_).
        for part in tokens[1:]:
            if "=" in part:
                k, v = part.split("=", 1)
                k = k.strip()
                v = v.strip()
                # First wins for keys that can legitimately recur (e.g. a bare
                # node= then a contig=); don't clobber an already-set value.
                if k not in out:
                    out[k] = v
                if k == "contig" and "node" not in out:
                    out["node"] = v
            elif part.startswith("BGC") and "bgc_id" not in out:
                out["bgc_id"] = part
            elif part.startswith("NODE") and "node" not in out:
                out["node"] = part

    if "aa" not in out:
        m = re.search(r"(?:^|[|\s])aa=(\d+)(?:[|\s]|$)", q)
        if m:
            out["aa"] = m.group(1)
    return out


def query_len_from_id(query_id: str) -> int | None:
    meta = parse_query_id(query_id)
    if meta.get("aa"):
        try:
            return int(meta["aa"])
        except Exception:
            return None
    return None


def _looks_like_hit_table_header(row: list[str]) -> bool:
    low = [c.strip().lower() for c in row]
    return "qseqid" in low or "query id" in " ".join(low) or "query_id" in low


def parse_hit_table_csv(path: str | Path) -> list[HitRecord]:
    """Parse NCBI BLASTP Hit Table CSV.

    NCBI often emits this file without a header. This parser preserves the first
    row if it looks like a real query row, which prevents the common off-by-one
    loss of the top hit.
    """
    p = Path(path)
    # BLAST-P03: mirror blastp_ingest.parse_hit_table — an HTML/QBlastInfo stub is not a Hit Table;
    # bail before csv-parsing it into junk rows (was silently yielding empty/garbage).
    _head = p.read_text(encoding="utf-8", errors="replace")[:400].lstrip()
    if _head.startswith("<") or "QBlastInfo" in _head:
        return []
    records: list[HitRecord] = []
    with p.open(newline="", encoding="utf-8-sig") as handle:
        rows = [r for r in csv.reader(handle) if r and any(c.strip() for c in r)]
    if not rows:
        return []
    header = None
    data_rows = rows
    if _looks_like_hit_table_header(rows[0]):
        header = [c.strip().lower().replace(" ", "_") for c in rows[0]]
        data_rows = rows[1:]
    for row in data_rows:
        if len(row) < 12:
            continue
        if header:
            d = {header[i]: row[i] for i in range(min(len(header), len(row)))}
            vals = [
                d.get("qseqid") or d.get("query_id") or d.get("query") or row[0],
                d.get("sseqid") or d.get("subject_id") or d.get("subject") or row[1],
                d.get("pident") or d.get("percent_identity") or d.get("pct_identity") or row[2],
                d.get("length") or d.get("align_len") or row[3],
                d.get("mismatch") or d.get("mismatches") or row[4],
                d.get("gapopen") or d.get("gap_opens") or row[5],
                d.get("qstart") or row[6],
                d.get("qend") or row[7],
                d.get("sstart") or row[8],
                d.get("send") or row[9],
                d.get("evalue") or row[10],
                d.get("bitscore") or row[11],
                d.get("ppos") or d.get("pct_positive") or (row[12] if len(row) > 12 else ""),
            ]
        else:
            # NCBI web BLASTP Hit Table CSV is often headerless. It also does
            # not reliably quote commas embedded in the query title. Sapote/Mamey
            # FASTA headers may include KCB labels such as
            # "..., complete_genome | Type: T1PKS"; a normal csv.reader then
            # splits the query id into extra fields. The BLAST columns at the
            # end are stable, so recover by treating the final 12 fields as
            # subject_id + metrics and joining everything before them back into
            # query_id. This preserves the first row and prevents false
            # zero-identity/weak-hit calls.
            if len(row) > 13:
                vals = [",".join(row[:len(row) - 12])] + row[len(row) - 12:]
            else:
                vals = row[:13] if len(row) >= 13 else row[:12] + [""]
        records.append(HitRecord(
            query_id=_text(vals[0]), subject_id=_text(vals[1]), pct_identity=_safe_float(vals[2]),
            align_len=_safe_int(vals[3]), mismatches=_safe_int(vals[4]), gap_opens=_safe_int(vals[5]),
            qstart=_safe_int(vals[6]), qend=_safe_int(vals[7]), sstart=_safe_int(vals[8]), send=_safe_int(vals[9]),
            evalue=_text(vals[10]), bitscore=_safe_float(vals[11]),
            pct_positive=_safe_float_or_none(vals[12]) if vals[12] != "" else None,
            query_len=query_len_from_id(_text(vals[0])),
        ))
    return records


def _find_text(elem: ET.Element, name: str) -> str:
    child = elem.find(f".//{{*}}{name}")
    return _text(child.text if child is not None else "")


def _find_int(elem: ET.Element, name: str) -> int | None:
    txt = _find_text(elem, name)
    if not txt:
        return None
    try:
        return int(float(txt))
    except Exception:
        return None


def parse_xml2(path: str | Path) -> dict[str, dict[str, Any]]:
    """Return query-level and hit-title metadata from NCBI XML2."""
    p = Path(path)
    # BLAST-P02: degrade to empty on an NCBI HTML/QBlastInfo error stub or a truncated/malformed
    # file instead of raising ParseError into ingest — the stub-guard the rest of the family has.
    try:
        if "QBlastInfo" in p.read_text(encoding="utf-8", errors="replace")[:400]:
            return {}
        root = ET.parse(p).getroot()
    except (ET.ParseError, OSError):
        return {}
    queries: dict[str, dict[str, Any]] = {}
    for search in root.findall(".//{*}Search"):
        qid = _find_text(search, "query-title") or _find_text(search, "query-id")
        if not qid:
            continue
        qlen = _find_int(search, "query-len")
        hits = []
        for hit in search.findall(".//{*}Hit"):
            descr = hit.find(".//{*}HitDescr")
            hsp = hit.find(".//{*}Hsp")
            if descr is None:
                continue
            hits.append({
                "subject_id": _find_text(descr, "id"),
                "subject_accession": _find_text(descr, "accession"),
                "subject_title": _find_text(descr, "title"),
                "subject_taxid": _find_text(descr, "taxid"),
                "subject_sciname": _find_text(descr, "sciname"),
                "hit_len": _find_int(hit, "len"),
                "bitscore": _safe_float(_find_text(hsp, "bit-score")) if hsp is not None else 0.0,
                "evalue": _find_text(hsp, "evalue") if hsp is not None else "",
                "identity": _find_int(hsp, "identity") if hsp is not None else None,
                "positive": _find_int(hsp, "positive") if hsp is not None else None,
                "align_len": _find_int(hsp, "align-len") if hsp is not None else None,
            })
        queries[qid] = {"query_len": qlen, "hits": hits}
    return queries


def _accession_key(subject_id: str) -> str:
    s = subject_id.strip()
    if "|" in s:
        parts = [p for p in s.split("|") if p]
        for p in parts:
            if re.match(r"^[A-Z]{1,4}_?\d", p) or re.match(r"^[A-Z]{2,}\d", p):
                return p.split(".")[0]
    return s.split(".")[0]


def merge_hit_xml(hit_records: list[HitRecord], xml_meta: dict[str, dict[str, Any]]) -> list[HitRecord]:
    if not xml_meta:
        return hit_records
    # Build exact query/title maps plus accession maps per query.
    merged: list[HitRecord] = []
    for r in hit_records:
        qmeta = xml_meta.get(r.query_id)
        if not qmeta:
            # Some NCBI hit tables may truncate query ids; try metadata-insensitive fallback.
            rmeta = parse_query_id(r.query_id)
            r_bgc = rmeta.get("bgc_id")
            r_gene = rmeta.get("gene")
            for xqid, xm in xml_meta.items():
                xmeta = parse_query_id(xqid)
                # PATCH-001: require the matched keys to be TRUTHY before
                # treating equality as a match. Without this guard, a header
                # that parse_query_id can't decompose leaves bgc_id/gene unset
                # on BOTH sides, so `None == None` is True for *every* XML
                # query and the loop silently binds the first-iterated query's
                # hits to every row.
                if not (r_bgc and r_gene):
                    break  # nothing to match on; leave qmeta None rather than mis-bind
                if xmeta.get("bgc_id") == r_bgc and xmeta.get("gene") == r_gene:
                    qmeta = xm
                    break
        qlen = qmeta.get("query_len") if qmeta else r.query_len
        hit_extra: dict[str, Any] = {}
        if qmeta:
            acc = _accession_key(r.subject_id)
            for h in qmeta.get("hits", []):
                hkeys = {_accession_key(str(h.get("subject_id", ""))), _accession_key(str(h.get("subject_accession", "")))}
                if acc in hkeys:
                    hit_extra = h
                    break
        merged.append(HitRecord(
            query_id=r.query_id, subject_id=r.subject_id, pct_identity=r.pct_identity,
            align_len=r.align_len, mismatches=r.mismatches, gap_opens=r.gap_opens,
            qstart=r.qstart, qend=r.qend, sstart=r.sstart, send=r.send, evalue=r.evalue,
            bitscore=r.bitscore, pct_positive=r.pct_positive, query_len=qlen or r.query_len,
            subject_title=hit_extra.get("subject_title", ""),
            subject_accession=hit_extra.get("subject_accession", ""),
            subject_sciname=hit_extra.get("subject_sciname", ""),
            subject_taxid=hit_extra.get("subject_taxid", ""),
            hit_len=hit_extra.get("hit_len"),
        ))
    return merged


def best_hits_by_query(records: Iterable[HitRecord]) -> dict[str, HitRecord]:
    best: dict[str, HitRecord] = {}
    for r in records:
        cur = best.get(r.query_id)
        if cur is None or (r.bitscore, r.pct_identity, r.align_len) > (cur.bitscore, cur.pct_identity, cur.align_len):
            best[r.query_id] = r
    return best


def classify_followup(r: HitRecord | None) -> tuple[str, str, int]:
    if r is None:
        return "UPGRADE_NO_HIT", "No BLASTP hit found; prioritize as weak/unknown evidence", 95
    title = (r.subject_title or r.subject_id).lower()
    qcov = r.query_coverage
    # BLP-04: unknown coverage (None) must not read as either high-confidence or weak on the
    # coverage axis — classify on identity/bitscore alone and defer the coverage judgement.
    cov_known = qcov is not None
    high_conf = r.pct_identity >= 80.0 and cov_known and qcov >= 0.75 and r.bitscore >= 100
    weak = r.pct_identity < 45.0 or (cov_known and qcov < 0.45)
    strong_product = any(t in title for t in STRONG_PRODUCT_TERMS)
    product_relevant = any(t in title for t in PRODUCT_RELEVANT_TERMS)
    uninformative = any(t in title for t in UNINFORMATIVE_TERMS)
    common = any(t in title for t in COMMON_REDUNDANT_TERMS)
    meta = parse_query_id(r.query_id)
    aa = _safe_int(meta.get("aa"), 0)
    giant = aa >= 1500
    if giant:
        return "ISOLATE_GIANT_OR_DOMAIN_FOLLOWUP", f"Giant multidomain query ({aa} aa); consider domain-focused BLASTP even when top hit is strong", 90
    if weak:
        _covtxt = f"{qcov:.2f} coverage" if cov_known else "coverage NA (query length unknown)"
        return "UPGRADE_WEAK_OR_PARTIAL", f"Weak/partial top hit ({r.pct_identity:.1f}% identity, {_covtxt})", 85
    if uninformative:
        return "UPGRADE_UNINFORMATIVE_TOP_HIT", "Top hit is hypothetical/uninformative", 80
    if high_conf and (strong_product or (product_relevant and not common)):
        return "RETAIN_PROOF_RELEVANT", "High-confidence product/class-relevant hit; retain for proof table", 70
    if high_conf and product_relevant and common:
        return "RETAIN_CONTEXT_RELEVANT", "High-confidence context/class hit; useful but likely not next-priority", 55
    if high_conf:
        return "DOWNGRADE_CONFIRMED_REDUNDANT", "Clear high-confidence annotation; lower priority for next batch", 20
    return "REVIEW_AMBIGUOUS", "Moderate or mixed evidence; manual review recommended", 60


def summarize_results(hit_records: list[HitRecord]) -> tuple[list[dict], list[dict]]:
    best = best_hits_by_query(hit_records)
    hit_rows: list[dict] = []
    for r in hit_records:
        meta = parse_query_id(r.query_id)
        hit_rows.append({
            "query_id": r.query_id, "strain": meta.get("strain", ""), "bgc_id": meta.get("bgc_id", ""),
            "gene": meta.get("gene", meta.get("locus_tag", "")), "role": meta.get("role", ""),
            "aa": meta.get("aa", r.query_len or ""), "subject_id": r.subject_id,
            "subject_accession": r.subject_accession, "subject_title": r.subject_title,
            "subject_sciname": r.subject_sciname, "pct_identity": f"{r.pct_identity:.3f}",
            "pct_positive": "" if r.pct_positive is None else f"{r.pct_positive:.2f}",
            "query_coverage": _cov_str(r.query_coverage), "align_len": r.align_len,
            "evalue": r.evalue, "bitscore": f"{r.bitscore:.1f}",
        })
    query_rows: list[dict] = []
    for qid, r in sorted(best.items(), key=lambda kv: (parse_query_id(kv[0]).get("bgc_id", ""), kv[0])):
        meta = parse_query_id(qid)
        decision, reason, priority = classify_followup(r)
        query_rows.append({
            "query_id": qid, "strain": meta.get("strain", ""), "bgc_id": meta.get("bgc_id", ""),
            "gene": meta.get("gene", meta.get("locus_tag", "")), "role": meta.get("role", ""),
            "aa": meta.get("aa", r.query_len or ""), "top_subject_id": r.subject_id,
            "top_accession": r.subject_accession, "top_title": r.subject_title,
            "top_sciname": r.subject_sciname, "top_identity": f"{r.pct_identity:.3f}",
            # PATCH-005 part 1: emit raw counts alongside percentages so the
            # "identical N/L (P%)" gene-table format is computed once here
            # rather than reassembled by hand per BGC. align_len is the BLASTP
            # alignment length; counts are derived deterministically from it.
            "top_identical_count": round(r.pct_identity / 100.0 * r.align_len),
            "top_positive": "" if r.pct_positive is None else f"{r.pct_positive:.2f}",
            "top_positive_count": "" if r.pct_positive is None
                                  else round(r.pct_positive / 100.0 * r.align_len),
            "top_query_coverage": _cov_str(r.query_coverage), "top_align_len": r.align_len,
            "top_evalue": r.evalue, "top_bitscore": f"{r.bitscore:.1f}",
            "followup_decision": decision, "followup_priority": priority, "followup_reason": reason,
            "claim_safety": CLAIM_SAFETY,
        })
    return hit_rows, query_rows


def _atomic_write_text(path, text, encoding: str = "utf-8") -> None:
    """AUDIT_374: tmp-sibling + os.replace, so a crash mid-write never leaves a
    truncated blastp-followup deliverable on disk (matches mamey/packaging.py's helper)."""
    path = str(path)
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding=encoding) as fh:
            fh.write(text)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise
    os.replace(tmp, path)


def _read_csv_dicts(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _write_csv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    if fields is None:
        keys: list[str] = []
        for row in rows:
            for k in row:
                if k not in keys:
                    keys.append(k)
        fields = keys
    buf = io.StringIO()
    w = _SafeDictWriter(buf, fieldnames=fields)
    w.writeheader()
    for row in rows:
        w.writerow({k: row.get(k, "") for k in fields})
    _atomic_write_text(path, buf.getvalue())


def load_fasta_records(panel_dir: str | Path) -> dict[str, str]:
    seqs: dict[str, str] = {}
    for faa in Path(panel_dir).glob("*.faa"):
        header = None
        chunks: list[str] = []
        for line in faa.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith(">"):
                if header:
                    seqs[header] = "".join(chunks)
                header = line[1:].strip()
                chunks = []
            else:
                chunks.append(re.sub(r"[^A-Za-z]", "", line).upper())
        if header:
            seqs[header] = "".join(chunks)
    return seqs


def _manifest_header_candidates(row: dict) -> list[str]:
    strain = row.get("strain", "strain")
    try:
        return [fasta_header(strain, row)[1:]]
    except Exception:
        return []


def make_followup_batch(previous_manifest: str | Path, panel_dir: str | Path,
                        searched_query_ids: set[str], out_fasta: Path,
                        max_proteins: int = 10, target_residues: int = 20000) -> list[dict]:
    rows = _read_csv_dicts(Path(previous_manifest))
    seqs = load_fasta_records(panel_dir)
    chosen: list[dict] = []
    total = 0
    # Use curated rows first, avoid first-pass/one-best duplicates.
    def key(row: dict):
        scope = row.get("panel_scope", "")
        scope_rank = 0 if scope.startswith("curated_") else (1 if "one_best" in scope else 2)
        warn_rank = 1 if row.get("warning") else 0
        return (scope_rank, warn_rank, -_safe_int(row.get("selection_score")), _safe_int(row.get("aa_len"), 999999))
    seen = set()
    for row in sorted(rows, key=key):
        identity = (row.get("bgc_id", ""), row.get("locus_tag", ""), row.get("protein_id", ""), row.get("slot", ""))
        if identity in seen:
            continue
        seen.add(identity)
        headers = _manifest_header_candidates(row)
        if any(h in searched_query_ids for h in headers):
            continue
        seq = ""
        header = ""
        for h in headers:
            if h in seqs:
                header, seq = h, seqs[h]
                break
        if not seq:
            continue
        # v9.7.335: `break` is right for the count cap but wrong for the residue budget — one
        # oversized protein ended selection, leaving budget unused and dropping every smaller
        # protein behind it (measured: 21 selected / 18819 of 20000 residues, 56 droppable).
        if chosen and len(chosen) >= max_proteins:
            break
        if chosen and total + len(seq) > target_residues:
            continue
        row2 = dict(row)
        row2["sequence"] = seq
        row2["followup_header"] = header
        chosen.append(row2)
        total += len(seq)
    text = ""
    for row in chosen:
        text += wrap_fasta(">" + row["followup_header"].lstrip(">"), row["sequence"])
    _atomic_write_text(out_fasta, text)
    return chosen


def ingest_followup(hit_table: str | Path, outdir: str | Path, xml2: str | Path | None = None,
                    previous_selection: str | Path | None = None, panel_dir: str | Path | None = None,
                    next_proteins: int = 10, target_residues: int = 20000) -> dict[str, Any]:
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    hit_records = parse_hit_table_csv(hit_table)
    xml_meta = parse_xml2(xml2) if xml2 else {}
    merged = merge_hit_xml(hit_records, xml_meta)
    hit_rows, query_rows = summarize_results(merged)
    _write_csv(out / "BLASTP_hit_table_normalized.csv", hit_rows)
    _write_csv(out / "BLASTP_query_summary.csv", query_rows)
    _write_csv(out / "BLASTP_reprioritization.csv", query_rows)

    searched = {r.query_id for r in merged}
    next_batch_count = 0
    next_residues = 0
    next_fasta = ""
    if previous_selection and panel_dir:
        next_fasta_path = out / "BLASTP_FOLLOWUP_next_batch_round001_for_BLASTP.faa"
        chosen = make_followup_batch(previous_selection, panel_dir, searched, next_fasta_path,
                                     max_proteins=next_proteins, target_residues=target_residues)
        next_batch_count = len(chosen)
        next_residues = sum(len(r.get("sequence", "")) for r in chosen)
        next_fasta = next_fasta_path.name

    decision_counts = defaultdict(int)
    for row in query_rows:
        decision_counts[row["followup_decision"]] += 1
    summary = {
        "schema": "blastp_iterative_followup_v1",
        "hit_table": str(hit_table),
        "xml2": str(xml2) if xml2 else "",
        "hit_count": len(merged),
        "query_count": len({r.query_id for r in merged}),
        "xml_query_count": len(xml_meta),
        "decision_counts": dict(sorted(decision_counts.items())),
        "next_fasta": next_fasta,
        "next_batch_count": next_batch_count,
        "next_batch_residues": next_residues,
        "claim_safety": CLAIM_SAFETY,
    }
    _atomic_write_text(out / "BLASTP_followup_summary.json", json.dumps(summary, indent=2))

    guide = [
        "# BLASTP follow-up ingest",
        "",
        f"Parsed {summary['hit_count']} hits across {summary['query_count']} BLASTP queries.",
        f"XML2 query metadata present for {summary['xml_query_count']} queries.",
        "",
        "## Files",
        "",
        "- `BLASTP_hit_table_normalized.csv` — all parsed hits, normalized columns.",
        "- `BLASTP_query_summary.csv` — top hit and decision per query.",
        "- `BLASTP_reprioritization.csv` — same query-level table for sorting/filtering.",
        "- `BLASTP_followup_summary.json` — machine-readable counts.",
    ]
    if next_fasta:
        guide.append(f"- `{next_fasta}` — next NCBI-safe follow-up FASTA ({next_batch_count} proteins, {next_residues} residues).")
    guide += [
        "",
        "## Recommended interpretation",
        "",
        "- `DOWNGRADE_CONFIRMED_REDUNDANT`: strong annotation; do not spend the next BLASTP batch here unless this BGC is central.",
        "- `RETAIN_CONTEXT_RELEVANT` / `RETAIN_PROOF_RELEVANT`: useful for evidence tables and class-safe reporting.",
        "- `UPGRADE_*`: prioritize for next batch or XML2/proof-grade follow-up.",
        "- `ISOLATE_GIANT_OR_DOMAIN_FOLLOWUP`: split into domain-focused FASTAs if NCBI web BLASTP struggles.",
        "",
        "Claim-safety: " + CLAIM_SAFETY,
        "",
    ]
    _atomic_write_text(out / "BLASTP_FOLLOWUP_USER_GUIDE.md", "\n".join(guide))
    return summary


def command(args) -> int:
    summary = ingest_followup(
        hit_table=args.hit_table,
        xml2=getattr(args, "xml2", None),
        previous_selection=getattr(args, "previous_selection", None),
        panel_dir=getattr(args, "panel_dir", None),
        outdir=args.outdir,
        next_proteins=getattr(args, "next_proteins", 10),
        target_residues=getattr(args, "target_residues", 20000),
    )
    emit(f"blastp-followup: parsed {summary['hit_count']} hits across {summary['query_count']} queries")
    if summary.get("next_fasta"):
        emit(f"  next FASTA: {summary['next_fasta']} ({summary['next_batch_count']} proteins; {summary['next_batch_residues']} residues)")
    emit("  summary: BLASTP_followup_summary.json")
    return 0 if summary["query_count"] else 1
