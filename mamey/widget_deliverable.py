"""Post-seal interactive widget deliverables for sealed Sapote-Mamey packages.

The renderer is deliberately reader-side: it reads package artifacts, never changes
scoring, never writes into the sealed package, and uses only the Python standard
library.  Every HTML view is self-contained so it remains usable over ``file://``.
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
import hashlib
import html
import io
import json
import os
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from . import roster_v2
from .csv_safety import CSV_LEADER_CLASS_JS, CSV_NUMERIC_TOKEN  # v9.7.410: one CSV-injection rule for Python + widget JS
from .dedup_and_guard import derive_release  # SSOT for the release tag (v9.7.236: AS- is PUBLIC)


SCHEMA_VERSION = "mamey_widget_deliverable_v2"
CLAIM_CEILING = (
    "BGC classes, routing priors, domain counts, similarity anchors, and RG-GMCI "
    "relationships are evidence-navigation aids. They do not establish compound identity, "
    "production, activity, novelty, causality, organism identity, or physical linkage. "
    "Missing evidence is not a biological negative; expression is unknown without culture data."
)
_PAGE_ORDER = ("priority", "domains", "evidence", "genes", "rggmci", "completeness", "gene")
_PAGE_TITLES = {
    "priority": "BGC priority explorer",
    "domains": "Domain architecture explorer",
    "evidence": "CCTT and KCB evidence explorer",
    "genes": "Gene evidence explorer",
    "rggmci": "RG-GMCI relationship explorer",
    "completeness": "Evidence completeness and gate explorer",
    "gene": "Per-gene channel explorer",
}


# Curated capacity-level reaction hints. These deliberately stop at enzyme-family
# chemistry: domains and homologs do not identify the exact substrate, product,
# stereochemistry, pathway membership, expression state, or metabolite.
_REACTION_HINTS: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"DegT_DnrJ_EryC1|\bDnrJ\b|\bEryC1\b", re.I),
     "PLP-dependent nucleotide-deoxysugar aminotransferase",
     "Transfers an amino group onto an oxidized nucleotide-deoxysugar intermediate; exact nucleotide sugar, position, and stereochemistry remain HOLD."),
    (re.compile(r"dTDP_sugar_isom|3,5-epimerase", re.I),
     "dTDP-deoxysugar epimerase",
     "Reconfigures stereocentres in a dTDP-linked deoxysugar intermediate; exact pathway product remains HOLD."),
    (re.compile(r"RmlD|4,6-dehydratase", re.I),
     "nucleotide-sugar 4,6-dehydratase",
     "Supports dehydration of an activated nucleotide sugar during deoxysugar biosynthesis; exact donor and downstream glycan remain HOLD."),
    (re.compile(r"Hexose_dehydrat|2,3-dehydratase", re.I),
     "nucleotide-hexose dehydratase",
     "Supports dehydration of a nucleotide-linked hexose intermediate; exact substrate and product remain HOLD."),
    (re.compile(r"GFO_IDH_MocA|ketoreductase", re.I),
     "nucleotide-sugar oxidoreductase",
     "Supports NAD(P)-dependent reduction or oxidation of a sugar intermediate; exact stereochemical outcome remains HOLD."),
    (re.compile(r"MGT|DUF1205|TIGR04516|glycosyltransfer|UDPGT", re.I),
     "glycosyltransferase",
     "Transfers an activated sugar to an acceptor; donor sugar, acceptor scaffold, linkage, and product remain HOLD."),
    (re.compile(r"AMP-binding|adenylation", re.I),
     "ATP-dependent carboxylate activation",
     "Activates a carboxylate as an adenylate; substrate and whether this is an NRPS or standalone ligase reaction remain HOLD."),
    (re.compile(r"PP-binding|phosphopantethe", re.I),
     "carrier-protein tethering capacity",
     "Provides a phosphopantetheinylated thiol for covalent intermediate tethering; cargo and pathway remain HOLD."),
    (re.compile(r"PKS_KS|ketoacyl-synth|ketosynth", re.I),
     "ketosynthase-like carbon-chain extension",
     "Supports decarboxylative carbon-carbon bond formation in a compatible assembly line; extender, chain, and product remain HOLD."),
    (re.compile(r"Condensation|NRPS_C", re.I),
     "NRPS condensation-domain capacity",
     "Supports amide-bond formation between compatible carrier-bound substrates; substrate identities and product remain HOLD."),
    (re.compile(r"LANC_like|LanM|lanthionine", re.I),
     "lanthionine-forming RiPP maturation capacity",
     "Supports dehydration/cyclization chemistry only with a compatible precursor and cassette; precursor, ring pattern, and product remain HOLD."),
    (re.compile(r"Peptidase_C39", re.I),
     "C39 peptidase processing capacity",
     "Supports leader-peptide cleavage coupled to a compatible export system; precursor and mature product remain HOLD."),
    (re.compile(r"p450|cytochrome P450", re.I),
     "cytochrome P450 oxidative tailoring",
     "Supports oxygen-dependent oxidative tailoring; substrate, position, and product remain HOLD."),
    (re.compile(r"methyltransf|methyltransfer", re.I),
     "SAM-dependent methyl transfer",
     "Supports methyl transfer to a compatible acceptor; atom, substrate, and product remain HOLD."),
    (re.compile(r"adh_short|SDR|oxidoreduct|dehydrogenase", re.I),
     "oxidoreductase capacity",
     "Supports cofactor-dependent redox chemistry; substrate, direction, and pathway role remain HOLD."),
    (re.compile(r"Ectoine_synth|\bEctC\b", re.I),
     "ectoine cyclization capacity",
     "Supports cyclization of N-acetyl-diaminobutyrate in an ectoine-compatible cassette; production remains HOLD."),
]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Crash-safe text write: write to a sibling .tmp then rename into place (v9.7.374 fix;
    mirrors mamey/packaging.py::_atomic_write_text). Without this, an interrupted render of
    render_widget_deliverable() could leave a truncated HTML page, widget_data.json, or -- worse
    -- a truncated WIDGET_MANIFEST.json / SHA256SUMS.txt sitting next to files it is supposed to
    checksum, which would then fail (or falsely pass) the bundle's own determinism/checksum
    verification test (test_outputs_are_deterministic_and_checksum_manifest_verifies)."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding=encoding)
    tmp.replace(path)


def _num(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


# v9.7.409 (DEEP_AUDIT2_resource_dos #2): antiSMASH-derived /product and /translation qualifiers reach
# the widget JSON uncapped; a crafted 5 MB qualifier bloats the deliverable payload. Bound every
# rendered text value to a sane length with an explicit [truncated] marker. Env-overridable.
_QUALIFIER_MAX_CHARS = 20_000


def _cap_text(text: str) -> str:
    try:
        cap = int(os.environ.get("MAMEY_QUALIFIER_MAX_CHARS", str(_QUALIFIER_MAX_CHARS)))
    except (TypeError, ValueError):
        cap = _QUALIFIER_MAX_CHARS
    if len(text) > cap:
        return text[:cap] + f" …[truncated {len(text) - cap} of {len(text)} chars]"
    return text


def _text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return _cap_text("; ".join(str(v) for v in value))
    return _cap_text(str(value))


class PackageSource:
    """Read a package directory or a Complete_Package.zip without extraction."""

    def __init__(self, supplied: str | Path):
        self.path = Path(supplied).expanduser().resolve()
        self.kind = "zip" if self.path.is_file() and zipfile.is_zipfile(self.path) else "directory"
        self._zip: zipfile.ZipFile | None = None
        self._root = self.path
        self.used: dict[str, str] = {}
        if self.kind == "zip":
            self._zip = zipfile.ZipFile(self.path)
            self._names = sorted(
                n for n in self._zip.namelist()
                if not n.endswith("/") and "__MACOSX" not in PurePosixPath(n).parts
            )
        else:
            if not self.path.is_dir():
                raise FileNotFoundError(f"package source not found: {self.path}")
            if not (self._root / "manifest.json").exists() and (self._root / "package" / "manifest.json").exists():
                self._root = self._root / "package"
            self._names = sorted(
                p.relative_to(self._root).as_posix()
                for p in self._root.rglob("*") if p.is_file()
            )

    def close(self) -> None:
        if self._zip is not None:
            self._zip.close()

    def locate(self, suffix: str, *, required: bool = False) -> str | None:
        # NC-037: match only at a path/basename boundary. A bare `n.endswith(suffix)` admits a
        # differently-prefixed file that merely ends with the token (e.g. suffix "board.csv" wrongly
        # matching "scoreboard.csv"), which could silently ingest the wrong evidence table post-seal.
        # Real suffixes are either a full member/basename (e.g. "manifest.json") or a strain-prefixed
        # "_<token>" that attaches at the basename boundary (e.g. "_4_triage_board.csv" on
        # "AS-XXX_4_triage_board.csv"). Reject anything that doesn't align to such a boundary.
        def _match(n: str) -> bool:
            base = n.rsplit("/", 1)[-1]
            return (n == suffix or n.endswith("/" + suffix) or base == suffix
                    or (suffix.startswith("_") and base.endswith(suffix)))
        matches = [n for n in self._names if _match(n)]
        if matches:
            # Prefer the canonical package/ member and the shallowest path.
            return sorted(matches, key=lambda n: ("/package/" not in "/" + n, n.count("/"), len(n), n))[0]
        if required:
            raise FileNotFoundError(f"required package artifact not found: *{suffix}")
        return None

    def read_bytes(self, name: str) -> bytes:
        if self.kind == "zip":
            assert self._zip is not None
            data = self._zip.read(name)
        else:
            data = (self._root / name).read_bytes()
        self.used[name] = _sha256(data)
        return data

    def json(self, suffix: str, *, required: bool = False) -> tuple[dict, str | None]:
        name = self.locate(suffix, required=required)
        if not name:
            return {}, None
        try:
            return json.loads(self.read_bytes(name).decode("utf-8-sig")), name
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            if required:
                raise ValueError(f"cannot parse required JSON {name}: {exc}") from exc
            return {}, name

    def csv(self, suffix: str) -> tuple[list[dict[str, str]], str | None]:
        name = self.locate(suffix)
        if not name:
            return [], None
        text = self.read_bytes(name).decode("utf-8-sig", errors="replace")
        return list(csv.DictReader(io.StringIO(text))), name

    def csv_many(self, directory_name: str) -> list[tuple[list[dict[str, str]], str]]:
        """Read every CSV beneath one exact package directory name.

        The path-component match prevents ``blastp_nr`` from silently pooling
        ``blastp_clustered_nr`` or another similarly named evidence channel.
        """
        marker = f"/{directory_name.strip('/')}/"
        names = [
            name for name in self._names
            if marker in f"/{name}" and name.lower().endswith(".csv")
        ]
        out: list[tuple[list[dict[str, str]], str]] = []
        for name in sorted(names):
            text = self.read_bytes(name).decode("utf-8-sig", errors="replace")
            out.append((list(csv.DictReader(io.StringIO(text))), name))
        return out

    def fingerprint(self) -> str:
        h = hashlib.sha256()
        for name, digest in sorted(self.used.items()):
            h.update(name.encode("utf-8")); h.update(b"\0"); h.update(digest.encode("ascii")); h.update(b"\n")
        return h.hexdigest()


def _join_rows(triage: list[dict], inventory: list[dict]) -> list[dict]:
    inv = {r.get("BGC_ID", ""): r for r in inventory}
    source = triage or inventory
    out = []
    for pos, row in enumerate(source, 1):
        merged = dict(inv.get(row.get("BGC_ID", ""), {})); merged.update(row)
        # Corrected_rank is blank by design for standing-rule-excluded/primary-metabolism
        # rows (scoring.py never assigns one). Rank is the raw pre-exclusion, score-sorted
        # position over ALL BGCs. Naively falling back "Corrected_rank or Rank" (as this line
        # once did) reuses that raw position as the *displayed* rank for excluded rows, and it
        # routinely collides with an unrelated real lead's genuine Corrected_rank (e.g. an
        # Inventory-tier saccharide-excluded BGC and an active Low-tier lead both shown as
        # "17" in the priority explorer) while also leaving gaps elsewhere in the sequence.
        # Sort real corrected ranks first (ascending), excluded rows after them ordered by
        # their raw Rank, then renumber 1..N below so every row gets a unique, sequential,
        # non-colliding displayed rank.
        corrected_txt = _text(merged.get("Corrected_rank"))
        sort_key = (0, _int(merged.get("Corrected_rank"), pos)) if corrected_txt else (1, _int(merged.get("Rank"), pos))
        out.append({
            "_sort_key": sort_key,
            "bgc_id": _text(merged.get("BGC_ID")),
            "products": _text(merged.get("Products")),
            "boundary": _text(merged.get("Boundary")),
            "arch": _text(merged.get("Arch")),
            "length_kb": _num(merged.get("Length_kb")),
            "ab": _num(merged.get("AB_auto")),
            "af": _num(merged.get("AF_auto")),
            "novelty": _num(merged.get("Novelty_auto")),
            "lead_tier": _text(merged.get("Lead_tier_auto")),
            "kcb_top": _text(merged.get("KCB_top")),
            "kcb_score": _num(merged.get("KCB_score")),
            "kcb_proteins": _int(merged.get("KCB_proteins")),
            "cctt": _text(merged.get("CCTT_triggers")),
            "rggmci_support": _text(merged.get("RGGMCI_support")),
            "standing_rule": _text(merged.get("Standing_rule")),
            "misanchor": _text(merged.get("Misanchor_flag") or merged.get("Mis_anchor_flag")),
            "parse_confidence": _text(merged.get("parse_confidence")),
            "claim_confidence": _text(merged.get("claim_confidence")),
            "claim_ceiling": _text(merged.get("claim_ceiling")),
            "safe_claim": _text(merged.get("safe_claim")),
        })
    out.sort(key=lambda r: (r["_sort_key"], r["bgc_id"]))
    for i, r in enumerate(out, 1):
        r["rank"] = i
        del r["_sort_key"]
    return out


def _domain_rows(rows: list[dict]) -> list[dict]:
    keys = ("PKS_KS", "PKS_AT", "PKS_KR", "PKS_DH", "NRPS_C", "NRPS_A", "NRPS_T_PCP", "TE_release")
    out = []
    for row in rows:
        item = {"bgc_id": _text(row.get("bgc_id") or row.get("BGC_ID"))}
        item.update({key: _int(row.get(key)) for key in keys})
        item["total"] = sum(item[key] for key in keys)
        out.append(item)
    return sorted(out, key=lambda r: (-r["total"], r["bgc_id"]))


def _rggmci_rows(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        out.append({
            "pair": _text(row.get("pair")),
            "bgc_a": _text(row.get("bgc_a") or row.get("BGC_A")),
            "bgc_b": _text(row.get("bgc_b") or row.get("BGC_B")),
            "score": _num(row.get("rggmci_score")),
            "confidence": _text(row.get("rggmci_confidence")),
            # v9.7.374: the real _4A_RGGMCI_ranked_pairs.csv (models.py's writer) never
            # emitted "reference_support_count" / "shared_reference_count" /
            # "geometry_support_count" / bare "tiling_verdict" — those column names do not
            # exist in any shipped CSV. The actual columns are "supporting_references",
            # "n_shared_subjects", "good_geometry_references", and "subject_tiling_verdict".
            # row.get() on the wrong name silently returned None, and _int()/_text() turned
            # that into 0/"" with no error, so every RG-GMCI pair rendered (and CSV-exported)
            # zeroed-out reference/geometry support on every strain. Read the real column
            # first; keep the old name as a harmless secondary fallback in case an older or
            # hand-built CSV used it.
            "reference_support": _int(row.get("supporting_references", row.get("reference_support_count"))),
            "shared_refs": _int(row.get("n_shared_subjects", row.get("shared_reference_count"))),
            "geometry": _text(row.get("geometry") or row.get("geometry_class")),
            "geometry_support": _int(row.get("good_geometry_references", row.get("geometry_support_count"))),
            "functional_rescue": _text(row.get("functional_rescue_class")),
            "tiling_verdict": _text(row.get("subject_tiling_verdict") or row.get("tiling_verdict")),
            "flags": _text(row.get("flags")),
            "best_sources": _text(row.get("best_sources")),
            "interpretation_guard": _text(row.get("interpretation_guard")),
        })
    return sorted(out, key=lambda r: (-r["score"], r["pair"]))


_BLASTP_CHANNEL_DIRS = {
    "nr": ("blastp_nr",),
    "clustered_nr": ("blastp_clustered_nr", "blastp_cluster_nr"),
    "swissprot": ("blastp_swissprot",),
    "ebi": ("blastp_ebi",),
    "online": ("blastp_online",),
}


def _reaction_hint(domains: str, function_text: str) -> dict[str, str]:
    evidence = f"{domains}; {function_text}"
    for pattern, family, explanation in _REACTION_HINTS:
        if pattern.search(evidence):
            return {
                "reaction_family": family,
                "reaction_hint": explanation,
                "reaction_status": "CAPACITY_LEVEL",
            }
    return {
        "reaction_family": "No curated reaction hint",
        "reaction_hint": (
            "The package supports a domain/function annotation only; exact enzyme reaction, "
            "substrate, product, and pathway role remain HOLD."
        ),
        "reaction_status": "HOLD",
    }


def _top_blastp_hit(row: dict[str, str]) -> dict[str, Any]:
    return {
        "hit_rank": _int(row.get("hit_rank"), 999999),
        "subject_acc": _text(row.get("subject_acc") or row.get("blastp_accession")),
        "subject_organism": _text(row.get("subject_organism") or row.get("blastp_organism")),
        "subject_def": _text(row.get("subject_def") or row.get("blastp_top_def")),
        "pct_identity": _num(row.get("pct_identity")),
        "pct_positives": _num(row.get("pct_positives")),
        "query_coverage": _num(row.get("query_coverage"), -1.0),
        "evalue": _text(row.get("evalue")),
        "bitscore": _num(row.get("bitscore")),
    }


def _gene_evidence_rows(
    *,
    strain: str,
    genes: list[dict[str, str]],
    inventory: list[dict[str, str]],
    mibig: list[dict[str, str]],
    clusterblast: list[dict[str, str]],
    blastp_batches: dict[str, list[tuple[list[dict[str, str]], str]]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Build exact-current gene rows and a channel-admission receipt.

    The gene-by-gene table is authoritative. Protein rows are admitted only on
    exact package strain, BGC, current locus, and positive amino-acid length.
    Legacy online rows without durable strain/BGC provenance remain HOLD.
    """
    inv = {row.get("BGC_ID", ""): row for row in inventory}
    # v9.7.374 fix: normalize the strain key the same way established elsewhere in this codebase
    # (mode_b/availability.py::normalize_strain, modeb_subsections.py, p450_tailoring.py all use
    # .strip().upper() for strain-ID comparisons). Without this, a BLASTp channel CSV's "strain"
    # column differing only in case/whitespace from manifest.strain_id (e.g. "AS-XXX" vs "AS-XXX")
    # silently rejects every row for that channel as HOLD_NOT_ESTABLISHED, even though the rows are
    # a genuine exact-current match -- confirmed live: a lowercased "strain" value in one blastp_nr
    # batch caused rows_admitted to drop from 1 to 0 and the channel status to flip to HOLD.
    strain_key = strain.strip().upper()
    current: dict[tuple[str, str], dict[str, str]] = {}
    duplicate_keys: set[tuple[str, str]] = set()
    for row in genes:
        bgc = _text(row.get("bgc_id") or row.get("BGC_ID"))
        locus = _text(row.get("locus_tag") or row.get("gene"))
        aa = _int(row.get("aa_length"), -1)
        if not bgc or not locus or aa <= 0:
            continue
        key = (bgc, locus)
        if key in current:
            duplicate_keys.add(key)
            continue
        current[key] = row
    for key in duplicate_keys:
        current.pop(key, None)

    mibig_by_gene: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in mibig:
        key = (_text(row.get("bgc_id")), _text(row.get("query_gene")))
        if key not in current:
            continue
        mibig_by_gene.setdefault(key, []).append({
            "reference_rank": _int(row.get("reference_rank"), 999999),
            "mibig_accession": _text(row.get("mibig_accession")),
            "mibig_compound": _text(row.get("mibig_compound")),
            "reference_type": _text(row.get("reference_type")),
            "subject_gene": _text(row.get("subject_gene")),
            "pct_identity": _num(row.get("pct_identity")),
            "pct_coverage": _num(row.get("pct_coverage_interpretation") or row.get("pct_coverage")),
            "evalue": _text(row.get("evalue")),
            "coverage_qc_flag": _text(row.get("coverage_qc_flag")),
        })
    for hits in mibig_by_gene.values():
        hits.sort(key=lambda row: (row["reference_rank"], -row["pct_identity"], row["mibig_accession"]))

    cluster_by_gene: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in clusterblast:
        key = (_text(row.get("bgc_id")), _text(row.get("query_gene")))
        if key not in current:
            continue
        cluster_by_gene.setdefault(key, []).append({
            "reference_rank": _int(row.get("reference_rank"), 999999),
            "reference": _text(row.get("reference")),
            "reference_source": _text(row.get("reference_source")),
            "subject_gene": _text(row.get("subject_gene")),
            "pct_identity": _num(row.get("pct_identity")),
            "pct_coverage": _num(row.get("pct_coverage")),
            "evalue": _text(row.get("evalue")),
        })
    for hits in cluster_by_gene.values():
        hits.sort(key=lambda row: (row["reference_rank"], -row["pct_identity"], row["reference"]))

    admitted: dict[str, dict[tuple[str, str], list[dict[str, Any]]]] = {}
    channel_summary: dict[str, Any] = {}
    for channel in _BLASTP_CHANNEL_DIRS:
        batches = blastp_batches.get(channel, [])
        by_gene: dict[tuple[str, str], list[dict[str, Any]]] = {}
        total = accepted = rejected = 0
        for rows, _source_name in batches:
            for row in rows:
                total += 1
                row_strain = _text(row.get("strain")).strip().upper()
                bgc = _text(row.get("bgc_id"))
                locus = _text(row.get("gene") or row.get("locus_tag"))
                aa = _int(row.get("aa_length"), -1)
                key = (bgc, locus)
                cur = current.get(key)
                cur_aa = _int((cur or {}).get("aa_length"), -1)
                if row_strain != strain_key or not bgc or not locus or aa <= 0 or cur is None or aa != cur_aa:
                    rejected += 1
                    continue
                accepted += 1
                by_gene.setdefault(key, []).append(_top_blastp_hit(row))
        for hits in by_gene.values():
            hits.sort(key=lambda row: (row["hit_rank"], -row["bitscore"], row["subject_acc"]))
        admitted[channel] = by_gene
        channel_summary[channel] = {
            "source_files": [name for _rows, name in batches],
            "rows_total": total,
            "rows_admitted": accepted,
            "rows_quarantined_or_held": rejected,
            "status": "UNAVAILABLE" if not batches else ("PRESENT" if accepted else "HOLD_NO_EXACT_CURRENT_ROWS"),
        }

    out: list[dict[str, Any]] = []
    for (bgc, locus), row in current.items():
        inventory_row = inv.get(bgc, {})
        aa = _int(row.get("aa_length"))
        domains = _text(row.get("sec_met_domains"))
        function_text = _text(row.get("product_qualifier") or row.get("gene_function_inference"))
        item: dict[str, Any] = {
            "strain": strain,
            "bgc_id": bgc,
            "bgc_rank": _int(row.get("rank"), 999999),
            "contig": _text(row.get("contig")),
            "region_locator": _text(row.get("source_gbk")),
            "locus_tag": locus,
            "aa_length": aa,
            "bgc_start": _int(row.get("bgc_start"), -1),
            "bgc_end": _int(row.get("bgc_end"), -1),
            "cds_start": _int(row.get("cds_start"), -1),
            "cds_end": _int(row.get("cds_end"), -1),
            "strand": _text(row.get("strand")),
            "products": _text(row.get("bgc_products") or inventory_row.get("Products")),
            "boundary": _text(row.get("boundary_flag") or inventory_row.get("Boundary")),
            "role": _text(row.get("gene_function_inference")),
            "function_text": function_text,
            "domains": domains,
            **_reaction_hint(domains, function_text),
            "mibig_hits": mibig_by_gene.get((bgc, locus), [])[:8],
            "mibig_hit_count": len(mibig_by_gene.get((bgc, locus), [])),
            "clusterblast_hits": cluster_by_gene.get((bgc, locus), [])[:5],
            "clusterblast_hit_count": len(cluster_by_gene.get((bgc, locus), [])),
            "blastp": {},
            "blastp_channel_status": {},
        }
        for channel in _BLASTP_CHANNEL_DIRS:
            hits = admitted[channel].get((bgc, locus), [])
            item["blastp_channel_status"][channel] = (
                "PRESENT" if hits else (
                    "UNAVAILABLE" if not blastp_batches.get(channel) else "HOLD_NOT_ESTABLISHED_FOR_EXACT_CURRENT_LOCUS"
                )
            )
            if hits:
                item["blastp"][channel] = hits[0]
        out.append(item)
    out.sort(key=lambda row: (row["bgc_rank"], row["bgc_id"], row["contig"], row["locus_tag"]))
    return out, {
        "authoritative_current_genes": len(out),
        "duplicate_current_keys_quarantined": len(duplicate_keys),
        "channels": channel_summary,
    }


def _load_model(source: PackageSource) -> dict:
    manifest, manifest_name = source.json("manifest.json", required=True)
    intake, intake_name = source.json("_1_intake.json")
    inventory, inventory_name = source.csv("_2_inventory.csv")
    triage, triage_name = source.csv("_4_triage_board.csv")
    rggmci, rggmci_name = source.csv("_4A_RGGMCI_ranked_pairs.csv")
    domains, domains_name = source.csv("_perBGC_domain_heatmap_data.csv")
    missing, missing_name = source.csv("_7_missing_data_worklist.csv")
    genes, genes_name = source.csv("_gene_by_gene_all_bgcs.csv")
    mibig_genes, mibig_genes_name = source.csv("_3_mibig_per_gene.csv")
    clusterblast_genes, clusterblast_genes_name = source.csv("_4A2_ClusterBlast_per_gene.csv")
    blastp_batches = {
        channel: [
            batch
            for directory in directories
            for batch in source.csv_many(directory)
        ]
        for channel, directories in _BLASTP_CHANNEL_DIRS.items()
    }
    gate, gate_name = source.json("gate_validation.json")
    claim, claim_name = source.json("claim_safety_status.json")
    package_status, package_status_name = source.json("package_status.json")
    strain = _text(manifest.get("strain_id") or intake.get("strain_id") or "UNKNOWN")
    release = _text(intake.get("release"))
    if not release:
        for bgc in manifest.get("bgcs", []):
            if bgc.get("release"):
                release = _text(bgc.get("release")); break
    source_release = release or "UNSPECIFIED"
    # SSOT release guard: fail-safe to PRIVATE only when derive_release says so
    # (AJS-/PENDING-/unrecognized); a PUBLIC AS- strain keeps the package's own tag.
    release_guard_val = derive_release(strain)
    effective_release = "PRIVATE" if release_guard_val == "PRIVATE" else source_release
    version = _text(manifest.get("workflow_version") or "unknown")
    gene_evidence, gene_evidence_receipt = _gene_evidence_rows(
        strain=strain,
        genes=genes,
        inventory=inventory,
        mibig=mibig_genes,
        clusterblast=clusterblast_genes,
        blastp_batches=blastp_batches,
    )
    status = {
        "package_status": _text(package_status.get("package_status") or manifest.get("package_status")),
        "gate_status": _text(gate.get("status")),
        "claim_safety_status": _text(claim.get("claim_safety_status") or manifest.get("claim_safety_status")),
        "checksum_integrity": _text(gate.get("checksum_integrity")),
        "gold_completeness": _text(gate.get("gold_completeness")),
        "antismash_version": _text(intake.get("antismash_version")),
        "antismash_profile": _text(intake.get("antismash_profile") or manifest.get("antismash_profile")),
    }
    artifacts = {
        "manifest": manifest_name, "intake": intake_name, "inventory": inventory_name,
        "triage": triage_name, "rggmci": rggmci_name, "domains": domains_name,
        "missing_worklist": missing_name, "gate_validation": gate_name,
        "claim_safety": claim_name, "package_status": package_status_name,
        "gene_table": genes_name, "mibig_per_gene": mibig_genes_name,
        "clusterblast_per_gene": clusterblast_genes_name,
        "blastp_channels": {
            channel: [name for _rows, name in batches]
            for channel, batches in blastp_batches.items()
        },
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "meta": {
            "strain_id": strain, "display_name": _text(intake.get("display_name") or manifest.get("display_name") or strain),
            "taxonomy": _text(intake.get("taxonomy") or manifest.get("taxonomy")),
            "source": _text(intake.get("source") or manifest.get("source")),
            "release": effective_release, "source_release": source_release,
            "release_guard": "PRIVATE_PREFIX_OVERRIDE" if (release_guard_val == "PRIVATE" and source_release != "PRIVATE") else "SOURCE_RELEASE_RETAINED",
            "workflow_version": version,
            "source_kind": source.kind, "claim_ceiling": CLAIM_CEILING,
        },
        "priority": _join_rows(triage, inventory),
        "domains": _domain_rows(domains),
        "rggmci": _rggmci_rows(rggmci),
        "genes": gene_evidence,
        "gene_evidence_receipt": gene_evidence_receipt,
        "missing_worklist": missing,
        "statuses": status,
        "source_artifacts": artifacts,
        "gene_roster": _safe_gene_roster(source, strain),
    }


_CSS = r"""
:root{--ink:#16243a;--muted:#5e6b7f;--blue:#176b87;--cyan:#26a7b8;--gold:#c69422;--red:#a43f4d;--paper:#f6f8fb;--card:#fff;--line:#dbe2ea}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.45 ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}header{background:linear-gradient(125deg,#102c46,#176b87);color:white;padding:24px clamp(18px,4vw,54px)}header h1{margin:.2rem 0;font-size:clamp(1.65rem,3vw,2.55rem)}header p{max-width:960px;margin:.35rem 0;color:#dceff4}.eyebrow{text-transform:uppercase;letter-spacing:.12em;font-weight:700;font-size:.75rem}nav{display:flex;gap:8px;flex-wrap:wrap;padding:12px clamp(18px,4vw,54px);background:white;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:5}nav a{color:var(--blue);text-decoration:none;padding:7px 10px;border-radius:7px;font-weight:650}nav a:hover,nav a.active{background:#e4f2f5}main{max-width:1280px;margin:20px auto;padding:0 18px 60px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}.card,.panel{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px;box-shadow:0 4px 16px #1d38580b}.card h2,.panel h2{margin-top:0}.kpi{font-size:2rem;font-weight:800;color:var(--blue)}.muted{color:var(--muted)}.guard{border-left:5px solid var(--gold);background:#fff9e9;padding:13px 15px;margin:18px 0}.controls{display:flex;flex-wrap:wrap;gap:10px;align-items:end;margin:12px 0}.controls label{font-size:.8rem;font-weight:700;color:var(--muted)}input,select,button{font:inherit;border:1px solid #b9c5d3;border-radius:7px;padding:8px 10px;background:white}button{cursor:pointer;color:white;background:var(--blue);border-color:var(--blue);font-weight:700}button.secondary{background:white;color:var(--blue)}.chart{width:100%;min-height:360px;border:1px solid var(--line);border-radius:10px;background:white}.chart text{font:12px ui-sans-serif,system-ui;fill:var(--ink)}.chart .axis{stroke:#8794a7;stroke-width:1}.chart .gridline{stroke:#e9edf2;stroke-width:1}.table-wrap{overflow:auto;max-height:570px;border:1px solid var(--line);border-radius:10px}table{border-collapse:collapse;width:100%;background:white;font-size:.84rem}th,td{text-align:left;padding:8px 9px;border-bottom:1px solid #e6ebf0;vertical-align:top}th{position:sticky;top:0;background:#eaf2f6;z-index:2;white-space:nowrap}tr:hover td{background:#f4f9fb}.badge{display:inline-block;padding:3px 7px;border-radius:999px;background:#e5f1f4;color:#145a70;font-size:.72rem;font-weight:800}.bad{background:#f8e3e6;color:#8d2f3e}.warn{background:#fff1c9;color:#755200}details{margin-top:16px;border-top:1px solid var(--line);padding-top:12px}summary{cursor:pointer;font-weight:750;color:var(--blue)}pre.caption{white-space:pre-wrap;background:#f2f5f8;padding:12px;border-radius:8px}.status-pass{color:#147447}.status-warn{color:#8a5d00}.status-fail{color:#a12f42}.card-link{text-decoration:none;color:inherit}.card-link .card{height:100%;transition:.12s transform,.12s box-shadow}.card-link:hover .card{transform:translateY(-2px);box-shadow:0 8px 22px #173d5b1c}.gene-detail{display:grid;grid-template-columns:minmax(240px,.8fr) minmax(0,2.2fr);gap:14px;margin:14px 0}.gene-summary{background:#eef6f8;border:1px solid #c9e0e6;border-radius:10px;padding:14px}.gene-summary h3{margin:.15rem 0 .55rem}.evidence-stack{display:grid;gap:12px}.evidence-block{border:1px solid var(--line);border-radius:10px;padding:12px;background:white}.evidence-block h3{margin:0 0 8px}.locus-button{padding:2px 5px;background:transparent;color:var(--blue);border:0;text-align:left}.selected-row td{background:#e8f5f7!important}.channel-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:8px}.channel{border-left:4px solid var(--cyan);background:#f4fafb;padding:8px 10px}.hold{border-left-color:var(--gold);background:#fff9e9}.gene-overview{display:grid;gap:10px;margin:14px 0}.gene-overview svg{width:100%;height:auto;border:1px solid var(--line);border-radius:10px;background:#fbfdff}.gene-overview .legend{display:flex;gap:14px;flex-wrap:wrap;color:var(--muted);font-size:.82rem}.gene-overview .legend span{display:inline-flex;gap:5px;align-items:center}.shape{display:inline-block;width:10px;height:10px;border:2px solid currentColor}.shape.circle{border-radius:50%}.shape.diamond{transform:rotate(45deg)}.shape.triangle{width:0;height:0;border-left:6px solid transparent;border-right:6px solid transparent;border-bottom:11px solid currentColor;border-top:0}.gene-focus{padding:11px 13px;background:#f5f8fb;border:1px solid var(--line);border-radius:10px;font-weight:650}.gene-figure-note{color:var(--muted);font-size:.84rem;margin:.2rem 0 1rem}@media(max-width:760px){.gene-detail{grid-template-columns:1fr}}@media print{nav,.controls,button{display:none!important}body{background:white}.card,.panel{box-shadow:none}.table-wrap{max-height:none;overflow:visible}}
:root{color-scheme:light;--plot-background:#fff;--marker-stroke:#34465b;--axis:#8794a7;--gridline:#e2e8f0;--selected-stroke:#102c46;--soft:#f5f8fb;--soft-2:#eef6f8;--guard-bg:#fff9e9;--table-head:#eaf2f6;--row-hover:#f4f9fb;--selected-row:#e8f5f7;--control-bg:#fff;--control-border:#b9c5d3}
:root[data-theme="dark"]{color-scheme:dark;--ink:#f3f5f7;--muted:#a9adb3;--blue:#75bcec;--cyan:#56cbd7;--gold:#e2bb60;--red:#f08e9b;--paper:#171717;--card:#212121;--line:#3b3b3b;--plot-background:#171717;--marker-stroke:#f3f5f7;--axis:#606060;--gridline:#303030;--selected-stroke:#f3f5f7;--soft:#252525;--soft-2:#252525;--guard-bg:#29261d;--table-head:#292929;--row-hover:#272d31;--selected-row:#24343a;--control-bg:#202020;--control-border:#555}
nav,.chart,table,input,select,button.secondary,.evidence-block,.gene-overview svg{background:var(--control-bg)}
input,select,button{border-color:var(--control-border);color:var(--ink)}
nav a:hover,nav a.active{background:var(--soft)}
.guard,.hold{background:var(--guard-bg)}
th{background:var(--table-head)}tr:hover td{background:var(--row-hover)}.selected-row td{background:var(--selected-row)!important}
.gene-summary{background:var(--soft-2);border-color:var(--line)}.channel,.gene-focus,pre.caption{background:var(--soft)}
.theme-toggle{margin-left:auto;padding:7px 10px;white-space:nowrap}
@media(max-width:760px){.theme-toggle{margin-left:0}}
"""


_COMMON_JS = r"""
const D=window.WIDGET_DATA;const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const cssColor=name=>getComputedStyle(document.documentElement).getPropertyValue(name).trim();
const themeToggle=document.getElementById('themeToggle');
function syncThemeButton(){if(!themeToggle)return;const dark=document.documentElement.dataset.theme==='dark';themeToggle.textContent=dark?'Light theme':'Dark theme';themeToggle.setAttribute('aria-pressed',String(dark))}
if(themeToggle){syncThemeButton();themeToggle.addEventListener('click',()=>{const next=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=next;try{localStorage.setItem('mamey-widget-theme',next)}catch(_e){}syncThemeButton();window.dispatchEvent(new CustomEvent('mamey-theme-change',{detail:{theme:next}}))})}
function saveBlob(blob,name){const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
function exportSvg(id,name){const node=document.getElementById(id);if(!node)return;const x=node.cloneNode(true);x.setAttribute('xmlns','http://www.w3.org/2000/svg');saveBlob(new Blob([new XMLSerializer().serializeToString(x)],{type:'image/svg+xml'}),name)}
// v9.7.410 CSV formula-injection guard: same rule as mamey/csv_safety.py (leader class + numeric-token regex are injected from that module).
// A string cell starting with = + - @ TAB CR is prefixed with ' BEFORE CSV quoting (quoting alone does not stop Excel/LibreOffice
// evaluating the cell). Lone strand signs and plain signed numbers (-1.5, +3, -2e-4) pass through unchanged so numeric cells stay numeric.
const CSV_LEADER=/^[__CSV_LEADER_CLASS__]/,CSV_NUMERIC=/__CSV_NUMERIC_TOKEN__/;
function csvSafeCell(s){return (CSV_LEADER.test(s)&&!(/^[+-]/.test(s)&&(s.length===1||CSV_NUMERIC.test(s))))?"'"+s:s}
function exportCsv(rows,name){if(!rows.length)return;const keys=[...new Set(rows.flatMap(r=>Object.keys(r)))];const q=v=>'"'+csvSafeCell(String(v??'')).replaceAll('"','""')+'"';const text=[keys.map(q).join(','),...rows.map(r=>keys.map(k=>q(r[k])).join(','))].join('\n');saveBlob(new Blob([text],{type:'text/csv'}),name)}
function line(x1,y1,x2,y2,cls='gridline'){return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" class="${cls}"/>`}
function statusClass(v){v=String(v||'').toUpperCase();return v.includes('FAIL')?'status-fail':(v.includes('PASS')||v.includes('COMPLETE'))?'status-pass':'status-warn'}
""".replace("__CSV_LEADER_CLASS__", CSV_LEADER_CLASS_JS).replace("__CSV_NUMERIC_TOKEN__", CSV_NUMERIC_TOKEN)


def _json_script(data: Any) -> str:
    # v9.7.410 hostile audit: escape EVERY `<` as <, not just `</`. Inside a <script> block a
    # literal `<!--` followed by `<script` puts the HTML tokenizer into the "double-escaped" state,
    # after which the widget's real closing tag no longer ends the element and the rest of the page
    # is swallowed as script text. The payload is deliverable text (antiSMASH product / note
    # strings), so it is attacker-reachable. `<` is valid JSON and valid JS; the parsed value
    # is unchanged.
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")


def _nav(active: str = "") -> str:
    links = ['<a href="OPEN_WIDGETS.html">Hub</a>']
    for key in _PAGE_ORDER:
        cls = ' class="active"' if key == active else ""
        links.append(f'<a{cls} href="{key}.html">{html.escape(_PAGE_TITLES[key])}</a>')
    links.append('<button id="themeToggle" class="secondary theme-toggle" type="button" aria-pressed="false">Dark theme</button>')
    return "<nav>" + "".join(links) + "</nav>"


def _shell(title: str, body: str, data: dict, *, active: str = "") -> str:
    meta = data["meta"]
    # Gene evidence is the largest payload. Keep it self-contained on its own
    # page, but do not duplicate it into every other HTML file.
    page_data = data if active == "genes" else {**data, "genes": []}
    theme_init = "<script>(function(){let t='';try{t=localStorage.getItem('mamey-widget-theme')||''}catch(_e){}if(t!=='light'&&t!=='dark')t=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';document.documentElement.dataset.theme=t})();</script>"
    return "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">" + theme_init + \
        f"<title>{html.escape(meta['strain_id'])} · {html.escape(title)}</title><style>{_CSS}</style></head><body>" + \
        f"<header><div class=\"eyebrow\">Sapote-Mamey post-seal widget deliverable · {html.escape(meta['release'])}</div><h1>{html.escape(meta['strain_id'])} · {html.escape(title)}</h1><p>{html.escape(meta['taxonomy'])} · {html.escape(meta['source'])} · {html.escape(meta['workflow_version'])}</p></header>" + \
        _nav(active) + f"<script>window.WIDGET_DATA={_json_script(page_data)};</script><script>{_COMMON_JS}</script><main>{body}</main></body></html>"


def _publication_details(kind: str, data: dict) -> str:
    strain = html.escape(data["meta"]["strain_id"])
    titles = {
        "priority": "Routing-prior landscape", "domains": "Biosynthetic domain architecture",
        "evidence": "Diagnostic and similarity-anchor evidence", "rggmci": "RG-GMCI candidate relationships",
        "genes": "Exact-current gene evidence",
        "completeness": "Package evidence completeness",
        "gene": "Per-gene multi-channel homology",
    }
    cap = f"{titles[kind]} for {strain}. Values were re-projected without re-scoring from the sealed Sapote-Mamey package. See PUBLICATION_HANDOFF.md for the full methods text and citation status."
    return f'<details><summary>Publication handoff text</summary><pre class="caption">{html.escape(cap)}</pre><p class="muted">Export the current vector chart as SVG and the filtered rows as CSV. Preserve the claim ceiling and source-package fingerprint when adapting the caption.</p></details>'


def _hub(data: dict) -> str:
    counts = {"priority": len(data["priority"]), "domains": len(data["domains"]), "evidence": len(data["priority"]), "genes": len(data["genes"]), "rggmci": len(data["rggmci"]), "completeness": len(data["missing_worklist"]), "gene": len(data["gene_roster"]["bgcs"])}
    cards = "".join(
        f'<a class="card-link" href="{key}.html"><div class="card"><div class="eyebrow">{key}</div><h2>{html.escape(_PAGE_TITLES[key])}</h2><div class="kpi">{counts[key]:,}</div><p class="muted">{("rows" if key != "completeness" else "worklist items")}</p></div></a>'
        for key in _PAGE_ORDER
    )
    s = data["statuses"]
    body = f'<section class="grid"><div class="card"><div class="eyebrow">BGC denominator</div><div class="kpi">{len(data["priority"]):,}</div><p class="muted">Package-native inventory/triage rows</p></div><div class="card"><div class="eyebrow">Domain rows</div><div class="kpi">{len(data["domains"]):,}</div><p class="muted">No zero-filled inference when source layer is absent</p></div><div class="card"><div class="eyebrow">Package status</div><div class="kpi" style="font-size:1.25rem">{html.escape(s.get("package_status") or "UNAVAILABLE")}</div><p class="muted">Displayed, never promoted by this renderer</p></div></section><h2>Explore the sealed result</h2><section class="grid">{cards}</section><div class="guard"><strong>Claim ceiling.</strong> {html.escape(CLAIM_CEILING)}</div><section class="panel"><h2>Publication conversion workflow</h2><p>Every analytical page can export the current chart as vector SVG and the filtered data as CSV. The bundle also includes <code>PUBLICATION_HANDOFF.md</code> and <code>publication_metadata.json</code> with caption/methods text, citation status, source artifacts, and the non-inference guard.</p></section>'
    return _shell("Interactive result widgets", body, data)


def _priority_page(data: dict) -> str:
    body = '<section class="panel"><h2>Routing-prior landscape</h2><p>Change axes, search BGC/class/anchor text, or filter boundaries and tiers. The plot shows routing priors, not measured activity or final scores.</p><div class="controls"><label>X axis<br><select id="x"><option value="ab">AB prior</option><option value="af">AF prior</option><option value="novelty">Novelty prior</option><option value="length_kb">Length (kb)</option></select></label><label>Y axis<br><select id="y"><option value="af">AF prior</option><option value="ab">AB prior</option><option value="novelty">Novelty prior</option><option value="length_kb">Length (kb)</option></select></label><label>Boundary<br><select id="boundary"><option value="">All</option></select></label><label>Tier<br><select id="tier"><option value="">All</option></select></label><label>Search<br><input id="q" placeholder="BGC, product, KCB"></label><button onclick="exportSvg(\'chart\',D.meta.strain_id+\'_priority.svg\')">Export SVG</button><button class="secondary" id="csv">Export filtered CSV</button></div><svg id="chart" class="chart" viewBox="0 0 900 500" role="img" aria-label="Routing prior scatterplot"></svg><p id="n" class="muted"></p><div class="table-wrap"><table><thead><tr><th>Rank</th><th>BGC</th><th>Products</th><th>Boundary</th><th>Tier</th><th>AB</th><th>AF</th><th>Novelty</th><th>KCB anchor</th><th>Guard</th></tr></thead><tbody id="rows"></tbody></table></div>'+_publication_details("priority",data)+'</section><div class="guard"><strong>Interpretation guard.</strong> AB, AF, and novelty values are automated routing priors. KCB names are similarity anchors, not product identities.</div><script>'+r"""
(()=>{const all=D.priority;const uniq=k=>[...new Set(all.map(r=>r[k]).filter(Boolean))].sort();for(const [id,k] of [['boundary','boundary'],['tier','lead_tier']]){const s=document.getElementById(id);uniq(k).forEach(v=>s.insertAdjacentHTML('beforeend',`<option>${esc(v)}</option>`))}let shown=[];function draw(){const xk=x.value,yk=y.value,b=boundary.value,t=tier.value,qq=q.value.toLowerCase();shown=all.filter(r=>(!b||r.boundary===b)&&(!t||r.lead_tier===t)&&(!qq||[r.bgc_id,r.products,r.kcb_top,r.cctt,r.standing_rule,r.misanchor].join(' ').toLowerCase().includes(qq)));const xs=shown.map(r=>+r[xk]||0),ys=shown.map(r=>+r[yk]||0),xmax=Math.max(1,...xs),ymax=Math.max(1,...ys),L=70,R=25,T=25,B=55,W=900,H=500;let s='';for(let i=0;i<=5;i++){const xx=L+(W-L-R)*i/5,yy=T+(H-T-B)*i/5;s+=line(xx,T,xx,H-B)+line(L,yy,W-R,yy);s+=`<text x="${xx}" y="${H-25}" text-anchor="middle">${(xmax*i/5).toFixed(0)}</text><text x="55" y="${H-B-(H-T-B)*i/5+4}" text-anchor="end">${(ymax*i/5).toFixed(0)}</text>`}s+=line(L,H-B,W-R,H-B,'axis')+line(L,T,L,H-B,'axis');s+=`<text x="470" y="492" text-anchor="middle">${esc(x.options[x.selectedIndex].text)}</text><text x="16" y="250" transform="rotate(-90 16 250)" text-anchor="middle">${esc(y.options[y.selectedIndex].text)}</text>`;for(const r of shown){const cx=L+(W-L-R)*(+r[xk]||0)/xmax,cy=H-B-(H-T-B)*(+r[yk]||0)/ymax,guard=r.standing_rule||r.misanchor,col=r.boundary==='Interior'?'#176b87':r.boundary==='Edge'?'#c69422':'#a43f4d';s+=`<circle cx="${cx}" cy="${cy}" r="6" fill="${col}" fill-opacity="${guard?'.3':'.78'}" ${guard?'stroke="#a43f4d" stroke-width="2" stroke-dasharray="2,2"':''}><title>${esc(r.bgc_id+' · '+r.products+' · '+r.lead_tier+(guard?' · GUARD (excluded from lead ranking): '+guard:'')+' · '+xk+' '+r[xk]+' · '+yk+' '+r[yk])}</title></circle>`}chart.innerHTML=s;rows.innerHTML=shown.slice(0,250).map(r=>{const g=r.standing_rule||r.misanchor,rowStyle=g?' style="background:#fdf1f1;opacity:.82"':'',badge=g?`<span style="display:inline-block;padding:1px 6px;border-radius:3px;background:#a43f4d;color:#fff;font-size:.72em;font-weight:600" title="${esc(g)}">EXCLUDED</span>`:'';return `<tr${rowStyle}><td>${r.rank}</td><td><strong>${esc(r.bgc_id)}</strong></td><td>${esc(r.products)}</td><td>${esc(r.boundary)}</td><td>${esc(r.lead_tier)}</td><td>${r.ab}</td><td>${r.af}</td><td>${r.novelty}</td><td>${esc(r.kcb_top)}</td><td>${badge}</td></tr>`}).join('');n.textContent=`${shown.length.toLocaleString()} of ${all.length.toLocaleString()} BGC rows shown`}[x,y,boundary,tier,q].forEach(e=>e.addEventListener(e.tagName==='INPUT'?'input':'change',draw));csv.onclick=()=>exportCsv(shown,D.meta.strain_id+'_priority_filtered.csv');draw()})();
"""+'</script>'
    return _shell(_PAGE_TITLES["priority"], body, data, active="priority")


def _domains_page(data: dict) -> str:
    body = '<section class="panel"><h2>Package-native domain architecture</h2><p>Domain counts come from the sealed F01 heatmap sidecar. An absent sidecar stays absent; this widget does not turn missing rows into biological zeros.</p><div class="controls"><label>Metric<br><select id="metric"><option value="total">All shown domains</option><option>PKS_KS</option><option>PKS_AT</option><option>PKS_KR</option><option>PKS_DH</option><option>NRPS_C</option><option>NRPS_A</option><option>NRPS_T_PCP</option><option>TE_release</option></select></label><label>Top rows<br><select id="limit"><option>15</option><option>30</option><option>60</option><option value="9999">All</option></select></label><button onclick="exportSvg(\'chart\',D.meta.strain_id+\'_domains.svg\')">Export SVG</button><button class="secondary" onclick="exportCsv(D.domains,D.meta.strain_id+\'_domains.csv\')">Export CSV</button></div><svg id="chart" class="chart" viewBox="0 0 900 560"></svg><div class="table-wrap"><table><thead><tr><th>BGC</th><th>Total</th><th>KS</th><th>AT</th><th>KR</th><th>DH</th><th>NRPS C</th><th>NRPS A</th><th>T/PCP</th><th>TE release</th><th>Guard</th></tr></thead><tbody id="rows"></tbody></table></div>'+_publication_details("domains",data)+'</section><div class="guard"><strong>Interpretation guard.</strong> Domain presence supports biosynthetic capacity and architecture. It does not demonstrate a complete product, expression, or production.</div><script>'+r"""
(()=>{const guardOf=Object.fromEntries((D.priority||[]).map(r=>[r.bgc_id,r.standing_rule||r.misanchor||'']));function draw(){const k=metric.value,n=+limit.value,arr=[...D.domains].sort((a,b)=>(+b[k]||0)-(+a[k]||0)||a.bgc_id.localeCompare(b.bgc_id)).slice(0,n),max=Math.max(1,...arr.map(r=>+r[k]||0)),L=150,R=40,T=20,B=30,W=900,H=560,rowH=(H-T-B)/Math.max(1,arr.length);let s='';arr.forEach((r,i)=>{const y=T+i*rowH+2,w=(W-L-R)*(+r[k]||0)/max,g=guardOf[r.bgc_id]||'',fill=g?'#a43f4d':'#176b87',op=g?'.4':'1';s+=`<text x="${L-8}" y="${y+Math.min(16,rowH*.75)}" text-anchor="end">${esc(r.bgc_id)}${g?' ⚑':''}</text><rect x="${L}" y="${y}" width="${w}" height="${Math.max(2,rowH-4)}" rx="2" fill="${fill}" fill-opacity="${op}" ${g?'stroke="#a43f4d" stroke-dasharray="3,2"':''}><title>${esc(r.bgc_id+' · '+k+' '+r[k]+(g?' · GUARD (excluded from lead ranking): '+g:''))}</title></rect><text x="${Math.min(W-R-5,L+w+5)}" y="${y+Math.min(16,rowH*.75)}">${r[k]}</text>`});chart.innerHTML=s;rows.innerHTML=arr.map(r=>{const g=guardOf[r.bgc_id]||'',badge=g?`<span class="badge bad" title="${esc(g)}">EXCLUDED</span>`:'';return `<tr${g?' style="background:#fdf1f1"':''}><td><strong>${esc(r.bgc_id)}</strong></td><td>${r.total}</td><td>${r.PKS_KS}</td><td>${r.PKS_AT}</td><td>${r.PKS_KR}</td><td>${r.PKS_DH}</td><td>${r.NRPS_C}</td><td>${r.NRPS_A}</td><td>${r.NRPS_T_PCP}</td><td>${r.TE_release}</td><td>${badge}</td></tr>`}).join('')}metric.onchange=limit.onchange=draw;draw()})();
"""+'</script>'
    return _shell(_PAGE_TITLES["domains"], body, data, active="domains")


def _evidence_page(data: dict) -> str:
    body = '<section class="panel"><h2>Diagnostic and similarity-anchor evidence</h2><p>This view keeps CCTT triggers, KCB anchors, standing rules, and mis-anchor flags adjacent so a strong-looking name cannot be read without its guard context.</p><div class="controls"><label>Evidence<br><select id="kind"><option value="all">All BGCs</option><option value="cctt">CCTT present</option><option value="kcb">KCB present</option><option value="guard">Standing/mis-anchor guard</option><option value="dark">No CCTT or KCB recorded</option></select></label><label>Search<br><input id="q" placeholder="BGC, class, trigger, anchor"></label><button class="secondary" id="csv">Export filtered CSV</button></div><div class="grid" id="kpis"></div><div class="table-wrap"><table><thead><tr><th>BGC</th><th>Products</th><th>CCTT triggers</th><th>KCB anchor</th><th>KCB score</th><th>Standing rule</th><th>Mis-anchor</th><th>Safe claim</th></tr></thead><tbody id="rows"></tbody></table></div>'+_publication_details("evidence",data)+'</section><div class="guard"><strong>Similarity-not-identity.</strong> A KCB name is a comparator anchor. A diagnostic trigger is evidence for a capacity hypothesis only in compatible architecture and context.</div><script>'+r"""
(()=>{const all=D.priority;let shown=[];function draw(){const k=kind.value,qq=q.value.toLowerCase();shown=all.filter(r=>{const ok=k==='all'||(k==='cctt'&&r.cctt)||(k==='kcb'&&r.kcb_top)||(k==='guard'&&(r.standing_rule||r.misanchor))||(k==='dark'&&!r.cctt&&!r.kcb_top);return ok&&(!qq||[r.bgc_id,r.products,r.cctt,r.kcb_top,r.standing_rule,r.misanchor].join(' ').toLowerCase().includes(qq))});const vals=[['Rows',shown.length],['CCTT present',shown.filter(r=>r.cctt).length],['KCB present',shown.filter(r=>r.kcb_top).length],['Guarded',shown.filter(r=>r.standing_rule||r.misanchor).length]];kpis.innerHTML=vals.map(x=>`<div class="card"><div class="eyebrow">${x[0]}</div><div class="kpi">${x[1].toLocaleString()}</div></div>`).join('');rows.innerHTML=shown.map(r=>`<tr><td><strong>${esc(r.bgc_id)}</strong></td><td>${esc(r.products)}</td><td>${esc(r.cctt)||'<span class="muted">not recorded</span>'}</td><td>${esc(r.kcb_top)||'<span class="muted">not recorded</span>'}</td><td>${r.kcb_score||''}</td><td>${esc(r.standing_rule)}</td><td>${esc(r.misanchor)}</td><td>${esc(r.safe_claim)}</td></tr>`).join('')}kind.onchange=draw;q.oninput=draw;csv.onclick=()=>exportCsv(shown,D.meta.strain_id+'_evidence_filtered.csv');draw()})();
"""+'</script>'
    return _shell(_PAGE_TITLES["evidence"], body, data, active="evidence")


def _genes_page(data: dict) -> str:
    body = '<section class="panel"><h2>Exact-current gene evidence</h2><p>Select a current locus to inspect its genomic context, protein length, BGC class, enzyme-family reaction capacity, per-gene MIBiG/KnownCluster compound anchors, ClusterBlast genome-neighborhood matches, and channel-separated BLASTP evidence.</p><div class="controls"><label>Focus BGC<br><select id="geneBgc"><option value="">All BGCs</option></select></label><label>BGC class<br><select id="geneProduct"><option value="">All classes</option></select></label><label>Evidence<br><select id="geneEvidence"><option value="">All genes</option><option value="mibig">MIBiG/KnownCluster hit</option><option value="clusterblast">ClusterBlast hit</option><option value="blastp">Exact-current BLASTP hit</option><option value="reaction">Curated reaction hint</option></select></label><label>Search<br><input id="geneQ" placeholder="locus, domain, role, compound, reaction"></label><button class="secondary" id="geneCsv">Export filtered CSV</button><button id="geneMapSvg">Export map SVG</button><button id="geneSimilaritySvg">Export similarity SVG</button></div><div class="gene-overview"><div id="geneFocus" class="gene-focus" aria-live="polite"></div><svg id="geneMap" viewBox="0 0 1120 220" role="img" aria-label="BGC gene positions and capacity categories"></svg><div class="legend" id="geneCategoryLegend"></div><svg id="geneSimilarity" viewBox="0 0 1120 430" role="img" aria-label="Per-gene sequence similarity by evidence channel"></svg><div class="legend"><span><i class="shape circle"></i>nr BLASTp</span><span><i class="shape"></i>Swiss-Prot</span><span><i class="shape diamond"></i>MIBiG</span><span><i class="shape triangle"></i>ClusterBlast</span></div><p class="gene-figure-note">Marker area scales with protein length. Hollow symbols show other genes; blue-filled symbols and adjacent labels show the selected locus. Identity is plotted only when recorded. Coverage remains visible in tooltips and the evidence panel; an unreported coverage value is not treated as full-length support.</p></div><div id="geneDetail" class="gene-detail" aria-live="polite"></div><p id="geneN" class="muted"></p><div class="table-wrap"><table><thead><tr><th>Locus</th><th>BGC</th><th>Class</th><th>aa</th><th>Domains</th><th>Reaction capacity</th><th>Top MIBiG compound anchor</th><th>Exact BLASTP channels</th><th>Guard</th></tr></thead><tbody id="geneRows"></tbody></table></div>'+_publication_details("genes",data)+'</section><div class="guard"><strong>Capacity, similarity, and neighborhood—not identity or production.</strong> Compound names are MIBiG/KnownCluster comparator anchors. ClusterBlast supports neighborhood similarity. A reaction hint is an enzyme-family hypothesis whose exact substrate, product, stereochemistry, expression, and pathway role remain bounded by the displayed HOLD language.</div><script>'+r"""
(()=>{
const channels=['nr','clustered_nr','swissprot','ebi','online'];
const guardOf=Object.fromEntries((D.priority||[]).map(r=>[r.bgc_id,r.standing_rule||r.misanchor||'']));
const all=D.genes.map((r,i)=>({...r,_i:i,guard:guardOf[r.bgc_id]||''}));let shown=[];let selected=all[0]||null;
const pct=v=>v===undefined||v===null||Number(v)<0?'not reported':Number(v).toFixed(1)+'%';
const ev=v=>esc(v||'not reported');
const uniq=(xs)=>[...new Set(xs.filter(Boolean))].sort((a,b)=>a.localeCompare(b,undefined,{numeric:true}));
const NS='http://www.w3.org/2000/svg';
const categoryDefs={
  glycosyltransferase:['#58a8df','glycosyltransferase'],sugar:['#ef9a55','sugar pathway'],tailoring:['#63be7b','tailoring/redox'],
  regulator:['#df79a8','regulator'],activation:['#9a7bd8','activation/carrier'],transport:['#4dbab3','transport'],other:['#9ca7b5','other']
};
for(const v of uniq(all.map(r=>r.bgc_id)))geneBgc.insertAdjacentHTML('beforeend',`<option>${esc(v)}</option>`);
for(const v of uniq(all.flatMap(r=>String(r.products||'').split(';').map(x=>x.trim()))))geneProduct.insertAdjacentHTML('beforeend',`<option>${esc(v)}</option>`);
function mibigTable(g){if(!g.mibig_hits.length)return '<p class="muted">No same-package per-gene MIBiG/KnownCluster row was recorded.</p>';return `<div class="table-wrap"><table><thead><tr><th>Rank</th><th>Compound anchor</th><th>MIBiG</th><th>Reference class</th><th>Subject gene</th><th>Identity</th><th>Coverage</th></tr></thead><tbody>${g.mibig_hits.map(h=>`<tr><td>${h.reference_rank}</td><td>${esc(h.mibig_compound)}</td><td>${esc(h.mibig_accession)}</td><td>${esc(h.reference_type)}</td><td>${esc(h.subject_gene)}</td><td>${pct(h.pct_identity)}</td><td>${pct(h.pct_coverage)}</td></tr>`).join('')}</tbody></table></div><p class="muted">Showing ${g.mibig_hits.length} of ${g.mibig_hit_count} per-gene anchors. Recurrent enzyme matches across different compound families support reaction-family convergence, not compound identity.</p>`}
function clusterTable(g){if(!g.clusterblast_hits.length)return '<p class="muted">No exact-current ClusterBlast gene row was recorded.</p>';return `<div class="table-wrap"><table><thead><tr><th>Rank</th><th>Reference genome/region</th><th>Subject gene</th><th>Identity</th><th>Coverage</th></tr></thead><tbody>${g.clusterblast_hits.map(h=>`<tr><td>${h.reference_rank}</td><td><strong>${esc(h.reference)}</strong><br><span class="muted">${esc(h.reference_source)}</span></td><td>${esc(h.subject_gene)}</td><td>${pct(h.pct_identity)}</td><td>${pct(h.pct_coverage)}</td></tr>`).join('')}</tbody></table></div>`}
function blastpGrid(g){return `<div class="channel-grid">${channels.map(c=>{const h=g.blastp[c],status=g.blastp_channel_status[c];if(!h)return `<div class="channel hold"><strong>${esc(c)}</strong><br>${esc(status)}</div>`;return `<div class="channel"><strong>${esc(c)}</strong><br>${esc(h.subject_def)}<br><span class="muted">${esc(h.subject_organism)} · ${esc(h.subject_acc)}<br>${pct(h.pct_identity)} identity · ${pct(h.query_coverage)} query coverage · E=${ev(h.evalue)}</span></div>`}).join('')}</div>`}
function drawDetail(g){if(!g){geneDetail.innerHTML='<div class="gene-summary"><strong>No current gene matches the filters.</strong></div>';return}const exact=Object.keys(g.blastp).length;geneDetail.innerHTML=`<aside class="gene-summary"><div class="eyebrow">${esc(g.strain)} · ${esc(g.bgc_id)}</div>${g.guard?`<div class="badge bad" title="${esc(g.guard)}">EXCLUDED FROM LEAD RANKING</div>`:''}<h3>${esc(g.locus_tag)} · ${g.aa_length} aa</h3><p><strong>BGC class:</strong> ${esc(g.products)||'not recorded'}<br><strong>Boundary:</strong> ${esc(g.boundary)||'not recorded'}<br><strong>Contig:</strong> ${esc(g.contig)}<br><strong>Region:</strong> ${esc(g.region_locator)}</p><p><strong>Coordinates:</strong> ${g.cds_start>=0&&g.cds_end>=0?g.cds_start.toLocaleString()+'–'+g.cds_end.toLocaleString():'not recorded'} (${esc(g.strand)||'strand not recorded'})</p><p><strong>Domains:</strong> ${esc(g.domains)||'not recorded'}</p><p><strong>Package role:</strong> ${esc(g.function_text||g.role)||'not recorded'}</p><p class="muted">${g.mibig_hit_count} MIBiG/KnownCluster rows · ${g.clusterblast_hit_count} ClusterBlast rows · ${exact} exact-current BLASTP channels</p></aside><div class="evidence-stack"><section class="evidence-block"><div class="eyebrow">Enzyme-family interpretation · ${esc(g.reaction_status)}</div><h3>${esc(g.reaction_family)}</h3><p>${esc(g.reaction_hint)}</p></section><section class="evidence-block"><h3>MIBiG/KnownCluster compound anchors</h3>${mibigTable(g)}</section><section class="evidence-block"><h3>ClusterBlast genome-neighborhood matches</h3>${clusterTable(g)}</section><section class="evidence-block"><h3>BLASTP channels kept separate</h3>${blastpGrid(g)}</section></div>`}
function svgEl(tag,attrs={}){const e=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,v);return e}
function svgText(parent,x,y,text,attrs={}){const e=svgEl('text',{x,y,...attrs});e.textContent=text;parent.appendChild(e);return e}
function geneCategory(g){const t=[g.domains,g.function_text,g.role].join(' ').toLowerCase();if(/glycosyltransfer|mgt|duf1205|tigr04516/.test(t))return 'glycosyltransferase';if(/degt|dnrj|eryc1|sugar|rml|dehydrat|epimer|ectoine/.test(t))return 'sugar';if(/oxidoreduct|dehydrogenase|p450|methyltransf|tailor|luciferase|acyl-coa_dh/.test(t))return 'tailoring';if(/regulat|response_reg|hiska|trans_reg/.test(t))return 'regulator';if(/amp-binding|pp-binding|adenyl|carrier|pks|nrps|condensation/.test(t))return 'activation';if(/transport|abc_|eama|mfs|permease/.test(t))return 'transport';return 'other'}
function locusSuffix(g){const m=String(g.locus_tag).match(/(\d+)$/);return m?Number(m[1]):g._i}
function focusGenes(){const bgc=geneBgc.value||(selected&&selected.bgc_id);return bgc?all.filter(g=>g.bgc_id===bgc):[]}
function coordinateModel(genes){const valid=genes.filter(g=>g.cds_start>=0&&g.cds_end>g.cds_start);if(valid.length===genes.length&&valid.length){const lo=Math.min(...valid.map(g=>g.bgc_start>=0?g.bgc_start:g.cds_start)),hi=Math.max(...valid.map(g=>g.bgc_end>=0?g.bgc_end:g.cds_end));return {lo,hi,pos:g=>[(g.cds_start-lo)/(hi-lo||1),(g.cds_end-lo)/(hi-lo||1)],label:v=>((v-lo)/1000).toFixed(v===lo?0:1)+' kb'}}const ordered=[...genes].sort((a,b)=>locusSuffix(a)-locusSuffix(b));return {lo:0,hi:Math.max(1,ordered.length),pos:g=>{const i=ordered.indexOf(g);return [i/ordered.length,(i+0.8)/ordered.length]},label:v=>Math.round(v)+' gene'}}
function arrowPoints(x1,x2,y,h,strand){const w=Math.max(4,x2-x1),head=Math.min(9,w*.42);return strand==='-'?`${x1},${y+h/2} ${x1+head},${y} ${x2},${y} ${x2},${y+h} ${x1+head},${y+h}`:`${x1},${y} ${x2-head},${y} ${x2},${y+h/2} ${x2-head},${y+h} ${x1},${y+h}`}
function drawGeneMap(genes){geneMap.replaceChildren();const L=58,R=1090,axisY=124,model=coordinateModel(genes),x=f=>L+f*(R-L),muted=cssColor('--muted'),axis=cssColor('--axis'),plot=cssColor('--plot-background'),selectedStroke=cssColor('--selected-stroke');svgText(geneMap,L,24,'Genomic position and function',{'font-weight':'700','font-size':'15'});svgText(geneMap,R,46,((model.hi-model.lo)/1000).toFixed(1)+' kb governed interval',{'text-anchor':'end','fill':muted});geneMap.appendChild(svgEl('line',{x1:L,y1:axisY,x2:R,y2:axisY,stroke:axis}));for(let i=0;i<=4;i++){const f=i/4,px=x(f),v=model.lo+(model.hi-model.lo)*f;geneMap.appendChild(svgEl('line',{x1:px,y1:axisY-5,x2:px,y2:axisY+5,stroke:axis}));svgText(geneMap,px,151,model.label(v),{'text-anchor':'middle','fill':muted})}for(const g of genes){const [a,b]=model.pos(g),x1=x(a),x2=x(b),cat=geneCategory(g),col=categoryDefs[cat][0],y=g.strand==='-'?133:75,poly=svgEl('polygon',{points:arrowPoints(x1,x2,y,27,g.strand),fill:col,stroke:selected&&selected._i===g._i?selectedStroke:plot,'stroke-width':selected&&selected._i===g._i?3:1.2,tabindex:0,role:'button'});const tt=svgEl('title');tt.textContent=`${g.locus_tag} · ${g.aa_length} aa · ${categoryDefs[cat][1]} · ${g.reaction_family}`;poly.appendChild(tt);poly.addEventListener('click',()=>selectGene(g._i));geneMap.appendChild(poly)}const cats=uniq(genes.map(g=>geneCategory(g)));geneCategoryLegend.innerHTML=cats.map(c=>`<span><i style="display:inline-block;width:12px;height:9px;background:${categoryDefs[c][0]}"></i>${esc(categoryDefs[c][1])}</span>`).join('')}
const similarityChannels=[
 {key:'nr',shape:'circle',jitter:-7,hit:g=>g.blastp.nr,label:'nr BLASTp'},
 {key:'swissprot',shape:'square',jitter:-2,hit:g=>g.blastp.swissprot,label:'Swiss-Prot'},
 {key:'mibig',shape:'diamond',jitter:3,hit:g=>g.mibig_hits.reduce((a,h)=>!a||h.pct_identity>a.pct_identity?h:a,null),label:'MIBiG'},
 {key:'clusterblast',shape:'triangle',jitter:8,hit:g=>g.clusterblast_hits.reduce((a,h)=>!a||h.pct_identity>a.pct_identity?h:a,null),label:'ClusterBlast'}
];
function hitDetail(c,h){if(c.key==='mibig')return `${h.mibig_compound} · ${h.mibig_accession} · ${pct(h.pct_coverage)} coverage`;if(c.key==='clusterblast')return `${h.reference_source||h.reference} · ${pct(h.pct_coverage)} coverage`;return `${h.subject_def||h.subject_acc} · ${pct(h.query_coverage)} query coverage`}
function marker(shape,x,y,r,fill,stroke){if(shape==='circle')return svgEl('circle',{cx:x,cy:y,r,fill,stroke,'stroke-width':2});if(shape==='square')return svgEl('rect',{x:x-r,y:y-r,width:2*r,height:2*r,rx:1,fill,stroke,'stroke-width':2});if(shape==='diamond')return svgEl('polygon',{points:`${x},${y-r} ${x+r},${y} ${x},${y+r} ${x-r},${y}`,fill,stroke,'stroke-width':2});return svgEl('polygon',{points:`${x},${y-r} ${x+r},${y+r} ${x-r},${y+r}`,fill,stroke,'stroke-width':2})}
function drawSimilarity(genes){geneSimilarity.replaceChildren();const L=58,R=1090,T=45,B=370,model=coordinateModel(genes),x=f=>L+f*(R-L),y=v=>B-(Math.max(0,Math.min(100,v))/100)*(B-T),muted=cssColor('--muted'),grid=cssColor('--gridline'),plot=cssColor('--plot-background'),stroke=cssColor('--marker-stroke');svgText(geneSimilarity,L,23,'Per-gene sequence similarity',{'font-weight':'700','font-size':'15'});svgText(geneSimilarity,R,23,'Identity (%)',{'text-anchor':'end','fill':muted});for(const v of [0,25,50,75,100]){const py=y(v);geneSimilarity.appendChild(svgEl('line',{x1:L,y1:py,x2:R,y2:py,stroke:grid}));svgText(geneSimilarity,L-10,py+4,String(v),{'text-anchor':'end','fill':muted})}for(let i=0;i<=4;i++){const f=i/4,px=x(f),v=model.lo+(model.hi-model.lo)*f;svgText(geneSimilarity,px,397,model.label(v),{'text-anchor':'middle','fill':muted})}for(const g of genes){const [a,b]=model.pos(g),gx=x((a+b)/2);similarityChannels.forEach((c,ci)=>{const h=c.hit(g);if(!h||Number(h.pct_identity)<0)return;const py=y(Number(h.pct_identity)),r=Math.max(4,Math.min(9,Math.sqrt(Math.max(1,g.aa_length))*.38)),isSel=selected&&selected._i===g._i,m=marker(c.shape,gx+c.jitter,py,r,isSel?'#58a8df':plot,stroke);m.setAttribute('tabindex','0');m.setAttribute('role','button');const tt=svgEl('title');tt.textContent=`${g.locus_tag} · ${c.label} · ${pct(h.pct_identity)} identity · ${hitDetail(c,h)} · ${g.aa_length} aa`;m.appendChild(tt);m.addEventListener('click',()=>selectGene(g._i));geneSimilarity.appendChild(m);if(isSel){const offsets=[-13,15,-18,20],ly=Math.max(T+8,Math.min(B-4,py+offsets[ci]));svgText(geneSimilarity,gx+c.jitter+11,ly,`${g.locus_tag} · ${c.label} ${pct(h.pct_identity)}`,{'font-weight':'700','font-size':'11','paint-order':'stroke','stroke':plot,'stroke-width':'3'})}})}}
function drawOverview(){const genes=focusGenes();if(!genes.length){geneFocus.textContent='Select a BGC or gene to draw the governed interval.';geneMap.replaceChildren();geneSimilarity.replaceChildren();return}const bgc=genes[0].bgc_id,sel=selected&&selected.bgc_id===bgc?selected:genes[0];if(!selected||selected.bgc_id!==bgc)selected=sel;const topM=selected.mibig_hits[0],nr=selected.blastp.nr,sp=selected.blastp.swissprot,cb=selected.clusterblast_hits[0];geneFocus.innerHTML=`<strong>${esc(selected.locus_tag)} · ${selected.aa_length} aa · ${esc(selected.reaction_family)}</strong><br><span class="muted">${esc(bgc)} · ${genes.length} current genes · nr ${nr?pct(nr.pct_identity):'HOLD'} · Swiss-Prot ${sp?pct(sp.pct_identity):'HOLD'} · MIBiG ${topM?pct(topM.pct_identity):'not recorded'} · ClusterBlast ${cb?pct(cb.pct_identity):'not recorded'}</span>`;drawGeneMap(genes);drawSimilarity(genes)}
function draw(){const q=geneQ.value.toLowerCase(),b=geneBgc.value,p=geneProduct.value,k=geneEvidence.value;shown=all.filter(r=>{const text=[r.locus_tag,r.bgc_id,r.products,r.domains,r.role,r.function_text,r.reaction_family,r.reaction_hint,r.guard,...r.mibig_hits.map(h=>h.mibig_compound),...r.clusterblast_hits.map(h=>h.reference_source),...Object.values(r.blastp).map(h=>[h.subject_def,h.subject_organism,h.subject_acc].join(' '))].join(' ').toLowerCase();const ek=!k||(k==='mibig'&&r.mibig_hit_count)||(k==='clusterblast'&&r.clusterblast_hit_count)||(k==='blastp'&&Object.keys(r.blastp).length)||(k==='reaction'&&r.reaction_status==='CAPACITY_LEVEL');return (!b||r.bgc_id===b)&&(!p||String(r.products).split(';').map(x=>x.trim()).includes(p))&&ek&&(!q||text.includes(q))});if(!selected||!shown.some(r=>r._i===selected._i))selected=shown[0]||null;geneRows.innerHTML=shown.map(r=>{const top=r.mibig_hits[0],cls=(selected&&selected._i===r._i?'selected-row ':'')+(r.guard?'guarded-row':'');return `<tr class="${cls}"${r.guard?' style="background:#fdf1f1"':''}><td><button class="locus-button" data-i="${r._i}"><strong>${esc(r.locus_tag)}</strong></button></td><td>${esc(r.bgc_id)}</td><td>${esc(r.products)}</td><td>${r.aa_length}</td><td>${esc(r.domains)}</td><td>${esc(r.reaction_family)}</td><td>${top?esc(top.mibig_compound):'<span class="muted">not recorded</span>'}</td><td>${Object.keys(r.blastp).map(esc).join(', ')||'<span class="muted">HOLD</span>'}</td><td>${r.guard?`<span class="badge bad" title="${esc(r.guard)}">EXCLUDED</span>`:''}</td></tr>`}).join('');geneN.textContent=`${shown.length.toLocaleString()} of ${all.length.toLocaleString()} authoritative current genes`;drawOverview();drawDetail(selected)}
function selectGene(i){selected=all[Number(i)];draw()}
geneRows.onclick=e=>{const b=e.target.closest('button[data-i]');if(!b)return;selectGene(b.dataset.i)};
for(const el of [geneBgc,geneProduct,geneEvidence])el.onchange=draw;geneQ.oninput=draw;
geneCsv.onclick=()=>exportCsv(shown.map(r=>({strain:r.strain,bgc_id:r.bgc_id,contig:r.contig,region_locator:r.region_locator,locus_tag:r.locus_tag,aa_length:r.aa_length,bgc_start:r.bgc_start,bgc_end:r.bgc_end,cds_start:r.cds_start,cds_end:r.cds_end,strand:r.strand,products:r.products,boundary:r.boundary,domains:r.domains,reaction_family:r.reaction_family,reaction_hint:r.reaction_hint,mibig_compounds:r.mibig_hits.map(h=>h.mibig_compound).join('; '),clusterblast_references:r.clusterblast_hits.map(h=>h.reference_source).join('; '),blastp_channels:Object.keys(r.blastp).join('; ')})),D.meta.strain_id+'_gene_evidence_filtered.csv');
geneMapSvg.onclick=()=>exportSvg('geneMap',D.meta.strain_id+'_'+(geneBgc.value||(selected&&selected.bgc_id)||'BGC')+'_gene_map.svg');
geneSimilaritySvg.onclick=()=>exportSvg('geneSimilarity',D.meta.strain_id+'_'+(geneBgc.value||(selected&&selected.bgc_id)||'BGC')+'_gene_similarity.svg');
window.addEventListener('mamey-theme-change',draw);
draw();
})();
"""+'</script>'
    return _shell(_PAGE_TITLES["genes"], body, data, active="genes")


def _rggmci_page(data: dict) -> str:
    body = '<section class="panel"><h2>Candidate cross-contig relationships</h2><p>Filter ranked RG-GMCI pairs by confidence and score. These are reference-guided candidate relationships; they are not proof that two regions are physically linked or form one pathway.</p><div class="controls"><label>Confidence<br><select id="conf"><option value="">All</option></select></label><label>Minimum score<br><input id="min" type="number" value="0" min="0" step="0.1"></label><label>Search<br><input id="q" placeholder="pair, BGC, source, flag"></label><button onclick="exportSvg(\'chart\',D.meta.strain_id+\'_rggmci.svg\')">Export SVG</button><button class="secondary" id="csv">Export filtered CSV</button></div><svg id="chart" class="chart" viewBox="0 0 900 520"></svg><p id="n" class="muted"></p><div class="table-wrap"><table><thead><tr><th>Pair</th><th>Score</th><th>Confidence</th><th>Reference support</th><th>Geometry</th><th>Functional rescue</th><th>Tiling verdict</th><th>Guard</th><th>Exclusion</th></tr></thead><tbody id="rows"></tbody></table></div>'+_publication_details("rggmci",data)+'</section><div class="guard"><strong>No physical-linkage inference.</strong> RG-GMCI relationships prioritize follow-up. Confirm assembly geometry, same-BGC context, gene architecture, and orthogonal evidence before pathway interpretation.</div><script>'+r"""
(()=>{const all=D.rggmci;const guardOf=Object.fromEntries((D.priority||[]).map(r=>[r.bgc_id,r.standing_rule||r.misanchor||'']));function pairGuard(r){const ga=guardOf[r.bgc_a]||'',gb=guardOf[r.bgc_b]||'';return {ga,gb,any:!!(ga||gb)};}[...new Set(all.map(r=>r.confidence).filter(Boolean))].sort().forEach(v=>conf.insertAdjacentHTML('beforeend',`<option>${esc(v)}</option>`));let shown=[];function draw(){const c=conf.value,m=+min.value||0,qq=q.value.toLowerCase();shown=all.filter(r=>{const g=pairGuard(r);return (!c||r.confidence===c)&&r.score>=m&&(!qq||[r.pair,r.bgc_a,r.bgc_b,r.best_sources,r.flags,r.functional_rescue,g.ga,g.gb].join(' ').toLowerCase().includes(qq))});const arr=shown.slice(0,25),max=Math.max(1,...arr.map(r=>r.score)),L=175,R=55,T=20,B=25,W=900,H=520,rh=(H-T-B)/Math.max(1,arr.length);let s='';arr.forEach((r,i)=>{const y=T+i*rh+2,w=(W-L-R)*r.score/max,g=pairGuard(r),col=g.any?'#a43f4d':(String(r.confidence).toUpperCase().includes('HIGH')?'#176b87':String(r.confidence).toUpperCase().includes('MED')?'#c69422':'#8794a7');s+=`<text x="${L-8}" y="${y+Math.min(15,rh*.72)}" text-anchor="end">${esc(r.pair)}${g.any?' ⚑':''}</text><rect x="${L}" y="${y}" width="${w}" height="${Math.max(2,rh-4)}" rx="2" fill="${col}" fill-opacity="${g.any?'.55':'1'}" ${g.any?'stroke="#a43f4d" stroke-dasharray="3,2"':''}><title>${esc(r.pair+' · '+r.score+' · '+r.confidence+(g.any?' · GUARD: one or both BGCs excluded from lead ranking ('+[g.ga,g.gb].filter(Boolean).join('; ')+')':''))}</title></rect><text x="${Math.min(W-R-5,L+w+5)}" y="${y+Math.min(15,rh*.72)}">${r.score}</text>`});chart.innerHTML=s;rows.innerHTML=shown.slice(0,500).map(r=>{const g=pairGuard(r),excl=g.any?`<span class="badge bad" title="${esc([g.ga,g.gb].filter(Boolean).join('; '))}">EXCLUDED</span>`:'';return `<tr${g.any?' style="background:#fdf1f1"':''}><td><strong>${esc(r.pair)}</strong></td><td>${r.score}</td><td>${esc(r.confidence)}</td><td>${r.reference_support}</td><td>${esc(r.geometry)} (${r.geometry_support})</td><td>${esc(r.functional_rescue)}</td><td>${esc(r.tiling_verdict)}</td><td>${esc(r.interpretation_guard)}</td><td>${excl}</td></tr>`}).join('');n.textContent=`${shown.length.toLocaleString()} of ${all.length.toLocaleString()} pairs shown; chart displays top ${arr.length}`}[conf,min,q].forEach(e=>e.addEventListener(e.tagName==='INPUT'?'input':'change',draw));csv.onclick=()=>exportCsv(shown.map(r=>({...r,excluded_bgc_a:guardOf[r.bgc_a]||'',excluded_bgc_b:guardOf[r.bgc_b]||''})),D.meta.strain_id+'_rggmci_filtered.csv');draw()})();
"""+'</script>'
    return _shell(_PAGE_TITLES["rggmci"], body, data, active="rggmci")


def _completeness_page(data: dict) -> str:
    body = '<section class="panel"><h2>Package, gate, and missing-data state</h2><p>This page reports source statuses exactly as available. The widget renderer never upgrades a package, release, biological, or publication gate.</p><div class="grid" id="statuses"></div><h2>Missing-data worklist</h2><div class="controls"><label>Search<br><input id="q" placeholder="priority, item, workflow, status"></label><button class="secondary" id="csv">Export filtered CSV</button></div><div class="table-wrap"><table><thead id="head"></thead><tbody id="rows"></tbody></table></div>'+_publication_details("completeness",data)+'</section><div class="guard"><strong>Absence discipline.</strong> A missing or unrun evidence channel means “not established here,” not biological absence. Package completion remains separate from release approval, biological validation, and publication readiness.</div><script>'+r"""
(()=>{statuses.innerHTML=Object.entries(D.statuses).map(([k,v])=>`<div class="card"><div class="eyebrow">${esc(k.replaceAll('_',' '))}</div><div class="kpi ${statusClass(v)}" style="font-size:1.15rem">${esc(v)||'UNAVAILABLE'}</div></div>`).join('');const all=D.missing_worklist;let shown=[];function draw(){const qq=q.value.toLowerCase();shown=all.filter(r=>!qq||Object.values(r).join(' ').toLowerCase().includes(qq));const keys=[...new Set(all.flatMap(r=>Object.keys(r)))];head.innerHTML='<tr>'+keys.map(k=>`<th>${esc(k)}</th>`).join('')+'</tr>';rows.innerHTML=shown.map(r=>'<tr>'+keys.map(k=>`<td>${esc(r[k])}</td>`).join('')+'</tr>').join('')}q.oninput=draw;csv.onclick=()=>exportCsv(shown,D.meta.strain_id+'_missing_worklist_filtered.csv');draw()})();
"""+'</script>'
    return _shell(_PAGE_TITLES["completeness"], body, data, active="completeness")



def _safe_gene_roster(source, strain_id: str | None = None) -> dict:
    """Package-native per-gene roster model; empty (never fabricated) if unavailable."""
    empty = {"strain": "", "channels_present": [], "bgcs": []}
    try:
        if getattr(source, "kind", None) != "directory":
            return empty
        root = getattr(source, "_root", None) or source.path
        # Pass the manifest/intake-derived strain id through explicitly. Without it,
        # roster_v2.build_gene_roster() falls back to the first inventory row's
        # User_Label — a per-BGC display label (e.g. "NODE_10_..._region001 (BGC001)"),
        # never a strain id — which silently mislabels the roster's "strain" field on
        # every real package.
        return roster_v2.build_gene_roster(root, strain_id=strain_id)
    except Exception:
        return empty


_GENE_JS = r"""
(()=>{const R=D.gene_roster;if(!R||!R.bgcs||!R.bgcs.length){document.getElementById('gwrap').innerHTML='<p class="muted">No package-native locus_maps / channel stores found for a per-gene view.</p>';return;}
const CH=[['nr','nr BLASTp'],['swissprot','Swiss-Prot'],['mibig','MIBiG'],['clusterblast','ClusterBlast']];
const NS='http://www.w3.org/2000/svg';let st={bgc:0,focus:'all',on:{nr:1,swissprot:1,mibig:1,clusterblast:1}};
const $=i=>document.getElementById(i);const E=(t,a)=>{const e=document.createElementNS(NS,t);for(const k in(a||{}))e.setAttribute(k,a[k]);return e;};
const sfx=l=>{const m=/_(\d+)$/.exec(l);return m?+m[1]:0;};const cv=(g,c)=>{const x=g.channels[c];return x&&x.pid!=null?x.pid:null;};
function mk(sv,ch,x,y,col,fill){const o={fill:fill?col:'none',stroke:col,'stroke-width':fill?0:1.5};
 if(ch=='nr')return sv.appendChild(E('circle',{cx:x,cy:y,r:5,...o}));
 if(ch=='swissprot')return sv.appendChild(E('rect',{x:x-4,y:y-4,width:8,height:8,...o}));
 if(ch=='mibig')return sv.appendChild(E('rect',{x:x-4,y:y-4,width:8,height:8,transform:`rotate(45 ${x} ${y})`,...o}));
 return sv.appendChild(E('path',{d:`M ${x} ${y-5} L ${x+5} ${y+4} L ${x-5} ${y+4} Z`,...o}));}
function kcb(k){if(!k)return'—';const p=k.split('|').map(s=>s.trim());return p.length>1&&p[1]?`${p[1]} (${p[0].split('.')[0]})`:p[0].split('.')[0];}
const guardOf=Object.fromEntries((D.priority||[]).map(r=>[r.bgc_id,r.standing_rule||r.misanchor||'']));
const bsel=$('gbgc');R.bgcs.forEach((b,i)=>bsel.insertAdjacentHTML('beforeend',`<option value="${i}">${esc(b.bgc_id)} · ${esc((b.products||'').split(';')[0])}${guardOf[b.bgc_id]?' [EXCLUDED]':''}</option>`));
bsel.onchange=e=>{st.bgc=+e.target.value;st.focus='all';draw();};$('gfocus').onchange=e=>{st.focus=e.target.value;draw();};
CH.forEach(([c])=>{$('t_'+c).onchange=e=>{st.on[c]=e.target.checked?1:0;draw();};});
function draw(){const b=R.bgcs[st.bgc],G=b.genes,gd=guardOf[b.bgc_id]||'',gdBadge=gd?`<span class="badge bad" title="${esc(gd)}">EXCLUDED FROM LEAD RANKING</span> `:'';const f=$('gfocus');f.innerHTML=`<option value="all">All ${G.length} genes</option>`+G.map(g=>`<option${g.locus_tag==st.focus?' selected':''}>${esc(g.locus_tag)}</option>`).join('');
 let g=st.focus!='all'&&G.find(x=>x.locus_tag==st.focus);
 $('gcard').innerHTML=gdBadge+(g?`<strong>${esc(g.locus_tag)}</strong> · ${g.aa||'?'} aa · ${g.strand||'?'} · `+CH.map(([k,l])=>{const c=g.channels[k];return `${l} <strong>${c&&c.pid!=null?c.pid+'%':'—'}</strong>`;}).join(' · ')+` · role: ${esc(g.role)} · domains: ${esc((g.domains||[]).join(', ')||g.smcog||'—')}`
   :`<strong>${esc(b.bgc_id)}</strong> · ${esc(b.node)} · ${esc(b.products)} · ${esc(b.boundary||'')} · ${b.length_kb||'?'} kb · KCB: ${esc(kcb(b.kcb_top))} — hover a gene`);
 // arrow map
 const mp=$('gmap');mp.innerHTML='';const W=980,cx=60,cw=W-120,gc=G.filter(x=>x.start!=null&&x.end!=null);
 if(gc.length){const mn=Math.min(...gc.map(x=>x.start)),mx=Math.max(...gc.map(x=>x.end)),X=v=>cx+(v-mn)/(mx-mn||1)*cw,mid=60;
  mp.appendChild(E('line',{x1:cx,y1:mid,x2:cx+cw,y2:mid,stroke:'#8794a7'}));const roles={};
  gc.forEach(x=>{const a=X(x.start),z=X(x.end),up=x.strand!='-',y=up?mid-24:mid+24,h=13,w=Math.max(5,z-a),ar=Math.min(7,w*0.4),col=x.role_color||'#5aa9a0';roles[x.role_group]=col;
   const yt=y-h/2,yb=y+h/2,d=up?`M${a} ${yt} H${a+w-ar} L${a+w} ${y} L${a+w-ar} ${yb} H${a} Z`:`M${a+w} ${yt} H${a+ar} L${a} ${y} L${a+ar} ${yb} H${a+w} Z`;
   const pth=E('path',{d,fill:col,opacity:(st.focus=='all'||st.focus==x.locus_tag)?0.9:0.3,cursor:'pointer'});pth.addEventListener('click',()=>{st.focus=x.locus_tag;draw();});pth.appendChild(E('title')).textContent=x.locus_tag+' · '+x.role;mp.appendChild(pth);});
  $('gleg').innerHTML=Object.entries(roles).map(([r,c])=>`<span style="display:inline-flex;align-items:center;gap:5px;margin-right:12px"><i style="width:11px;height:11px;border-radius:3px;background:${c};display:inline-block"></i>${esc(r)}</span>`).join('');
 } else {$('gleg').innerHTML='<span class="muted">no coordinate data</span>';}
 // scatter
 const sv=$('gscat');sv.innerHTML='';const H=320,L=48,Rr=18,T=14,B=34;const sf=G.map(x=>sfx(x.locus_tag)),xm=Math.min(...sf),xM=Math.max(...sf),Xs=v=>L+(v-xm)/((xM-xm)||1)*(W-L-Rr),Ys=p=>T+(100-p)/100*(H-T-B);
 [0,25,50,75,100].forEach(p=>{const y=Ys(p);sv.appendChild(E('line',{x1:L,y1:y,x2:W-Rr,y2:y,class:'gridline'}));sv.appendChild(E('text',{x:L-6,y:y+4,'text-anchor':'end'})).textContent=p;});
 G.forEach(x=>{const px=Xs(sfx(x.locus_tag)),foc=st.focus==x.locus_tag;CH.forEach(([c])=>{if(!st.on[c])return;const v=cv(x,c);if(v==null)return;const m=mk(sv,c,px,Ys(v),foc?'#176b87':'#5e6b7f',foc);m.style.cursor='pointer';m.setAttribute('opacity',foc?1:(st.focus=='all'?0.85:0.3));m.addEventListener('click',()=>{st.focus=x.locus_tag;draw();});m.appendChild(E('title')).textContent=`${x.locus_tag} · ${c} ${v}%`;});});
}
draw();})();
"""


def _gene_page(data: dict) -> str:
    toggles = "".join(
        f'<label style="font-weight:650;color:var(--blue)"><input type="checkbox" id="t_{k}" checked> {html.escape(lbl)}</label>'
        for k, lbl in (("nr", "nr BLASTp"), ("swissprot", "Swiss-Prot"), ("mibig", "MIBiG"), ("clusterblast", "ClusterBlast")))
    body = (
        '<section class="panel" id="gwrap"><h2>Per-gene multi-channel homology</h2>'
        '<p>Best homology hit per gene in each channel (nr / Swiss-Prot / MIBiG / general ClusterBlast), '
        'beside the antiSMASH role and domains. An empty channel is <em>not run</em>, never a biological zero.</p>'
        '<div class="controls"><label>BGC<br><select id="gbgc"></select></label>'
        '<label>Focus gene<br><select id="gfocus"></select></label>' + toggles + '</div>'
        '<div class="card" id="gcard" style="margin:10px 0"></div>'
        '<h2 style="font-size:1rem">Genomic position and function</h2>'
        '<svg id="gmap" class="chart" viewBox="0 0 980 120" style="min-height:120px"></svg><div id="gleg" style="margin:6px 0"></div>'
        '<h2 style="font-size:1rem">Per-gene sequence similarity (identity %)</h2>'
        '<svg id="gscat" class="chart" viewBox="0 0 980 320"></svg>'
        + _publication_details("gene", data) + '</section>'
        '<div class="guard"><strong>Homology, not function.</strong> Every %id is a class-level lead — '
        '"capacity consistent with," never "produces." MIBiG compound names and ClusterBlast labels are '
        'similarity anchors, not product identity.</div><script>' + _GENE_JS + '</script>')
    return _shell(_PAGE_TITLES["gene"], body, data, active="gene")



def _publication_handoff(data: dict, source_fingerprint: str) -> str:
    m = data["meta"]
    return f"""# Publication handoff — {m['strain_id']} widget deliverable

## Scope and claim ceiling

{CLAIM_CEILING}

The widgets are deterministic reader-side re-projections of a sealed package. They do not re-run antiSMASH, re-score BGCs, author Mode B judgments, or change package, release, biological, figure, or publication gates.

## Reproducible export workflow

1. Open `OPEN_WIDGETS.html`, select a widget, and set filters/axes.
2. Export the current chart as SVG and the filtered rows as CSV.
3. Record the filter state in the final caption; keep the source fingerprint below.
4. Edit the SVG in a vector editor only for typography/layout. Do not alter values or silently remove rows.
5. Resolve every `citation_needed` item before manuscript submission; do not invent a reference.

## Methods text

Interactive views were generated by the Sapote-Mamey post-seal widget renderer from package-native inventory, triage, exact-current gene, per-gene MIBiG/KnownCluster, ClusterBlast, channel-separated BLASTP, domain-sidecar, RG-GMCI, gate, claim-safety, and missing-data artifacts. Values were parsed without re-scoring and rendered with dependency-free SVG/HTML. Filters alter only the displayed subset. Source package fingerprint: `{source_fingerprint}`. BGC product labels and KnownClusterBlast compound names were treated as class-level or similarity anchors, enzyme-family reaction text as capacity-level interpretation with explicit HOLDs, automated AB/AF/novelty values as routing priors, domain counts as capacity evidence, and RG-GMCI pairs as candidate relationships rather than physical linkage.

## Caption templates

- **Priority:** Routing-prior landscape for {m['strain_id']}. Points are sealed-package BGC rows; axes show automated routing priors or package-native length. Colours encode boundary state. These values prioritize follow-up and are not measured activity or final biological scores.
- **Domains:** Biosynthetic-domain architecture for {m['strain_id']}, re-projected from the sealed F01 domain sidecar. Bars report recorded domain counts; missing source layers were not zero-filled.
- **Evidence:** Diagnostic-trigger and KnownClusterBlast similarity-anchor evidence for {m['strain_id']}, shown with standing-rule and mis-anchor guards. Comparator names do not establish product identity.
- **Genes:** Exact-current gene evidence for {m['strain_id']}. The selected locus is shown with BGC class, protein length, domain-supported reaction capacity, MIBiG/KnownCluster compound anchors, ClusterBlast neighborhood similarity, and separately reported BLASTP channels. These are capacity and similarity evidence, not product identity, production, or activity.
- **RG-GMCI:** Ranked RG-GMCI candidate relationships for {m['strain_id']}. Scores prioritize cross-contig follow-up and do not establish physical linkage or a single pathway.
- **Completeness:** Package, gate, claim-safety, and missing-data state for {m['strain_id']}. Missing evidence is not interpreted as biological absence.

## Citation ledger

| Source | Status | Identifier / action |
|---|---|---|
| Sapote-Mamey software ({m['workflow_version']}) | operator_supplied | Cite the bundle's `CITATION.cff`; confirm the released version used. |
| antiSMASH 8.0 | verified_in_bundle_cff | Blin et al. 2025, Nucleic Acids Research 53:W32-W38. DOI: 10.1093/nar/gkaf334; PMID: 40276974. |
| Dataset / assembly accession | citation_needed | Add the deposited assembly or project accession used for this package. |
| Any biological interpretation beyond the plotted evidence | citation_needed | Resolve primary literature through the project's citation-verification protocol. |

## Provenance

- Strain: `{m['strain_id']}`
- Effective release label: `{m['release']}`
- Release label recorded in source: `{m['source_release']}`
- Release guard: `{m['release_guard']}`
- Source kind: `{m['source_kind']}`
- Source fingerprint: `{source_fingerprint}`
- Widget schema: `{SCHEMA_VERSION}`
"""


def render_widget_deliverable(package: str | Path, outdir: str | Path | None = None) -> dict:
    """Render a sibling widget bundle and return its deterministic manifest."""
    source = PackageSource(package)
    try:
        model = _load_model(source)
        source_fingerprint_before = source.fingerprint()
        supplied = source.path
        if outdir is None:
            stem = supplied.stem if source.kind == "zip" else supplied.name
            out = supplied.parent / f"{stem}_widgets"
        else:
            out = Path(outdir).expanduser().resolve()
        # A post-seal feature may never default into or be explicitly pointed at its source package.
        source_root = source._root.resolve() if source.kind == "directory" else None
        if source_root is not None and (out == source_root or source_root in out.parents):
            raise ValueError("widget output must be outside the sealed package directory")
        out.mkdir(parents=True, exist_ok=True)

        pages = {
            "OPEN_WIDGETS.html": _hub(model),
            "priority.html": _priority_page(model),
            "domains.html": _domains_page(model),
            "evidence.html": _evidence_page(model),
            "genes.html": _genes_page(model),
            "rggmci.html": _rggmci_page(model),
            "completeness.html": _completeness_page(model),
            "gene.html": _gene_page(model),
        }
        for name, content in pages.items():
            _atomic_write_text(out / name, content)
        _atomic_write_text(out / "widget_data.json", json.dumps(model, indent=2, ensure_ascii=False) + "\n")
        source_fingerprint_after = source.fingerprint()
        _atomic_write_text(out / "PUBLICATION_HANDOFF.md", _publication_handoff(model, source_fingerprint_before))
        pubmeta = {
            "schema_version": "mamey_widget_publication_handoff_v1",
            "strain_id": model["meta"]["strain_id"],
            "source_fingerprint": source_fingerprint_before,
            "claim_ceiling": CLAIM_CEILING,
            "citation_status": {"sapote_mamey": "operator_supplied", "antismash_8": "verified_in_bundle_cff", "dataset_accession": "citation_needed", "biological_interpretation": "citation_needed"},
            "export_formats": ["SVG", "CSV"],
            "source_artifacts": model["source_artifacts"],
        }
        _atomic_write_text(out / "publication_metadata.json", json.dumps(pubmeta, indent=2) + "\n")
        readme = f"""# {model['meta']['strain_id']} interactive widgets

Open `OPEN_WIDGETS.html` in a browser. No server, network connection, or external JavaScript is required.

This is a post-seal reader deliverable. It does not modify or upgrade the source package. See `PUBLICATION_HANDOFF.md` for SVG/CSV conversion, caption/methods text, citations, and claim ceilings.

Source fingerprint: `{source_fingerprint_before}`
"""
        _atomic_write_text(out / "README.md", readme)

        tracked = sorted(p for p in out.iterdir() if p.is_file() and p.name not in {"WIDGET_MANIFEST.json", "SHA256SUMS.txt"})
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "status": "PASS" if source_fingerprint_before == source_fingerprint_after else "FAIL_SOURCE_MUTATION_CHECK",
            "strain_id": model["meta"]["strain_id"],
            "source": {"path": str(source.path), "kind": source.kind, "fingerprint": source_fingerprint_before, "fingerprint_after_render": source_fingerprint_after, "mutation_check": "PASS" if source_fingerprint_before == source_fingerprint_after else "FAIL", "artifacts": [{"name": n, "sha256": d} for n, d in sorted(source.used.items())]},
            "counts": {"bgcs": len(model["priority"]), "gene_rows": len(model["genes"]), "domain_rows": len(model["domains"]), "rggmci_pairs": len(model["rggmci"]), "missing_worklist_rows": len(model["missing_worklist"]), "widgets": len(_PAGE_ORDER)},
            "claim_ceiling": CLAIM_CEILING,
            "outputs": [{"name": p.name, "bytes": p.stat().st_size, "sha256": _sha256(p.read_bytes())} for p in tracked],
        }
        _atomic_write_text(out / "WIDGET_MANIFEST.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
        checksum_files = sorted(p for p in out.iterdir() if p.is_file() and p.name != "SHA256SUMS.txt")
        _atomic_write_text(out / "SHA256SUMS.txt", "".join(f"{_sha256(p.read_bytes())}  {p.name}\n" for p in checksum_files))
        return {**manifest, "outdir": str(out)}
    finally:
        source.close()


def render_widgets_command(args) -> int:
    try:
        result = render_widget_deliverable(args.package, getattr(args, "outdir", None))
    except (FileNotFoundError, ValueError, zipfile.BadZipFile) as exc:
        emit(f"render-widgets: ERROR: {exc}", file=sys.stderr)
        return 1
    emit(f"render-widgets: {result['status']} · {result['counts']['widgets']} widgets · {result['counts']['bgcs']} BGC rows -> {result['outdir']}", '  source package unchanged; open OPEN_WIDGETS.html', sep="\n")
    return 0 if result["status"] == "PASS" else 1
