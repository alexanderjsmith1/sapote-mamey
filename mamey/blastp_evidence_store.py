"""Durable BLASTP evidence store for iterative Sapote/Mamey workflows.

This module stores BLASTP follow-up evidence as an auditable, append-only-ish
run ledger. It is intentionally offline-first: users run NCBI web BLASTP,
download XML2 and Hit Table CSV, then ingest those files into a strain-local
store.

Design goals:
- keep raw NCBI files with SHA256 checksums;
- preserve normalized top-hit/all-hit tables from ``blastp_followup``;
- append per-round metadata so user effort is never lost;
- produce a BGC-level evidence ledger for Mode B cards;
- remain safe if called repeatedly for the same round id.
"""
from __future__ import annotations

import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import hashlib
import json
import shutil
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .blastp_followup import (
    HitRecord,
    CLAIM_SAFETY,
    merge_hit_xml,
    parse_hit_table_csv,
    parse_query_id,
    parse_xml2,
)

STORE_VERSION = "v9.7.142-blastp-store-rev5"

CLASS_DEFINING_TERMS = (
    "phosphoenolpyruvate mutase", "pep mutase", "pepm", "lantibiotic dehydratase",
    "lanthionine synthetase", "lankc", "lanm", "lanc", "ycaO", "thiazolylpeptide",
    "tomm", "lasso", "non-ribosomal peptide", "nonribosomal peptide", "adenylation domain",
    "condensation domain", "polyketide synthase", "ketosynthase", "type i polyketide",
    "halogenase", "siderophore", "nrp-metallophore", "terpene cyclase",
)
NEIGHBORHOOD_TERMS = (
    "transporter", "abc", "permease", "regulator", "response regulator", "histidine kinase",
    "resistance", "immunity", "dehydratase", "methyltransferase", "glycosyltransferase",
    "metallophosphoesterase", "atp-grasp", "ferredoxin", "substrate-binding protein",
)
GENERIC_TERMS = (
    "family protein", "domain-containing protein", "hydrolase", "oxidoreductase",
    "dehydrogenase", "peptidase", "isocitrate lyase", "ferredoxin", "hypothetical",
)


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _atomic_write_text(path: Path, text: str) -> None:
    """v9.7.374 fix: write to a temp sibling then atomically replace, so an interrupted write
    (crash, kill -9, disk full mid-write) never leaves a truncated evidence-store deliverable
    that a later reader (rebuild_cumulative_tables, a Mode B card) silently treats as complete.
    Same pattern as packaging.py::_atomic_write_text / blastp_followup.py's equivalent helper."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    import io
    buf = io.StringIO()
    w = _SafeDictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    w.writeheader()
    for row in rows:
        w.writerow({k: row.get(k, "") for k in fieldnames})
    _atomic_write_text(path, buf.getvalue())


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    out=[]
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def evidence_tier(record: HitRecord) -> str:
    # v9.7.335: record.query_id was included here, but it is OUR panel defline — its `reason=`
    # field is built from the query's own antiSMASH annotation using terms that are verbatim
    # members of CLASS_DEFINING_TERMS. That laundered antiSMASH's call back as BLASTp support: a
    # 19%-identity, 12-aa alignment with an EMPTY subject title graded TIER_A_CLASS_DEFINING.
    # Tier on subject fields only.
    text = " ".join([
        record.subject_title, record.subject_id, record.subject_sciname,
    ]).lower()
    if any(t.lower() in text for t in CLASS_DEFINING_TERMS):
        return "TIER_A_CLASS_DEFINING"
    if any(t.lower() in text for t in NEIGHBORHOOD_TERMS):
        return "TIER_B_NEIGHBORHOOD_SUPPORT"
    if any(t.lower() in text for t in GENERIC_TERMS):
        return "TIER_C_GENERIC_FUNCTION_CONFIRMED"
    return "TIER_D_UNINFORMATIVE_OR_WEAK"


def next_action(record: HitRecord) -> str:
    tier = evidence_tier(record)
    if tier == "TIER_A_CLASS_DEFINING":
        return "RETAIN_FOR_CLASS_PROOF_TABLE"
    if tier == "TIER_B_NEIGHBORHOOD_SUPPORT":
        return "RETAIN_FOR_CONTEXT_TABLE"
    qcov = record.query_coverage
    # BLP-04 (v9.7.338): query_coverage is None when the query length is genuinely unknown.
    # Unknown coverage is not evidence of good coverage — route it to rerun/domain-followup,
    # the same recommendation as the low-coverage branch.
    if qcov is None or qcov < 0.5:
        return "RERUN_OR_DOMAIN_FOLLOWUP"
    return "DOWNGRADE_FOR_NEXT_FASTA"


def _hit_to_row(record: HitRecord, round_id: str) -> dict[str, Any]:
    meta = parse_query_id(record.query_id)
    return {
        "round_id": round_id,
        "strain": meta.get("strain", ""),
        "bgc_id": meta.get("bgc_id", ""),
        "query_gene": meta.get("gene", ""),
        "node": meta.get("node", ""),
        "region": meta.get("region", ""),
        "query_id": record.query_id,
        "subject_id": record.subject_id,
        "subject_accession": record.subject_accession,
        "subject_title": record.subject_title,
        "subject_sciname": record.subject_sciname,
        "subject_taxid": record.subject_taxid,
        "pct_identity": record.pct_identity,
        "pct_positive": record.pct_positive if record.pct_positive is not None else "",
        "align_len": record.align_len,
        "query_len": record.query_len or "",
        "query_coverage": (f"{record.query_coverage:.4f}" if record.query_coverage is not None else "NA"),
        "evalue": record.evalue,
        "bitscore": record.bitscore,
        "evidence_tier": evidence_tier(record),
        "next_action": next_action(record),
        "claim_safety": CLAIM_SAFETY,
    }


HIT_FIELDS = [
    "round_id", "strain", "bgc_id", "query_gene", "node", "region", "query_id",
    "subject_id", "subject_accession", "subject_title", "subject_sciname", "subject_taxid",
    "pct_identity", "pct_positive", "align_len", "query_len", "query_coverage",
    "evalue", "bitscore", "evidence_tier", "next_action", "claim_safety",
]

BGC_FIELDS = [
    "strain", "bgc_id", "round_ids", "query_count", "top_titles", "best_pct_identity",
    "best_query_coverage", "tier_a_count", "tier_b_count", "tier_c_count", "tier_d_count",
    "current_claim_level", "recommended_next_action", "claim_safety",
]


def summarize_bgc_rows(top_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in top_rows:
        groups[(row.get("strain", ""), row.get("bgc_id", ""))].append(row)
    out=[]
    for (strain, bgc_id), rows in sorted(groups.items()):
        tiers=defaultdict(int)
        for r in rows:
            tiers[r.get("evidence_tier", "")] += 1
        best=max(rows, key=lambda r: float(r.get("bitscore") or 0))
        titles=[]
        for r in rows:
            t=str(r.get("subject_title", ""))
            if t and t not in titles:
                titles.append(t)
        if tiers["TIER_A_CLASS_DEFINING"]:
            claim="CLASS_SUPPORTED_BY_BLASTP"
            rec="MODE_B_PROOF_READY_OR_NEAR_READY"
        elif tiers["TIER_B_NEIGHBORHOOD_SUPPORT"]:
            claim="GENE_FUNCTION_AND_NEIGHBORHOOD_SUPPORTED"
            rec="KEEP_AS_CONTEXT_OR_ADD_DIAGNOSTIC_CORE"
        else:
            claim="GENE_FUNCTION_ONLY_OR_WEAK"
            rec="DOWNGRADE_UNLESS_PHENOTYPE_OR_ADD_DIAGNOSTIC_CORE"
        out.append({
            "strain": strain,
            "bgc_id": bgc_id,
            "round_ids": ";".join(sorted({str(r.get("round_id", "")) for r in rows})),
            "query_count": len({r.get("query_id", "") for r in rows}),
            "top_titles": " | ".join(titles[:6]),
            "best_pct_identity": best.get("pct_identity", ""),
            "best_query_coverage": best.get("query_coverage", ""),
            "tier_a_count": tiers["TIER_A_CLASS_DEFINING"],
            "tier_b_count": tiers["TIER_B_NEIGHBORHOOD_SUPPORT"],
            "tier_c_count": tiers["TIER_C_GENERIC_FUNCTION_CONFIRMED"],
            "tier_d_count": tiers["TIER_D_UNINFORMATIVE_OR_WEAK"],
            "current_claim_level": claim,
            "recommended_next_action": rec,
            "claim_safety": CLAIM_SAFETY,
        })
    return out


def ingest_blastp_round(
    store_dir: str | Path,
    *,
    strain: str,
    round_id: str,
    hit_table_csv: str | Path,
    xml2: str | Path | None = None,
    fasta: str | Path | None = None,
    purpose: str = "manual_iterative_blastp",
    operator_note: str = "",
    allow_update: bool = False,
) -> dict[str, Any]:
    """Ingest one NCBI BLASTP round into a durable evidence store.

    Re-ingesting the same round_id raises by default to prevent accidental
    duplicate evidence. Use allow_update=True to replace tables/raw files for
    a corrected local parse.
    """
    store = Path(store_dir)
    raw_dir = store / "raw_ncbi_downloads" / round_id
    parsed_dir = store / "parsed_rounds" / round_id
    cumulative_dir = store / "cumulative"
    manifest_path = store / "BLASTP_round_manifest.jsonl"
    existing = [r for r in _read_jsonl(manifest_path) if r.get("round_id") == round_id]
    if existing and not allow_update:
        raise ValueError(f"round_id already ingested: {round_id}")
    if existing and allow_update:
        # Remove old parsed/raw for this round; cumulative files are rebuilt below.
        if raw_dir.exists():
            shutil.rmtree(raw_dir)
        if parsed_dir.exists():
            shutil.rmtree(parsed_dir)
        rows=[r for r in _read_jsonl(manifest_path) if r.get("round_id") != round_id]
        _atomic_write_text(manifest_path, "".join(json.dumps(r, sort_keys=True)+"\n" for r in rows))

    raw_dir.mkdir(parents=True, exist_ok=True)
    parsed_dir.mkdir(parents=True, exist_ok=True)
    cumulative_dir.mkdir(parents=True, exist_ok=True)

    copied=[]
    for label, src in (("hit_table_csv", hit_table_csv), ("xml2", xml2), ("fasta", fasta)):
        if src:
            srcp=Path(src)
            dst=raw_dir / srcp.name
            shutil.copy2(srcp, dst)
            copied.append({"kind": label, "path": str(dst.relative_to(store)), "sha256": sha256_file(dst), "bytes": dst.stat().st_size})

    hits = parse_hit_table_csv(hit_table_csv)
    if xml2:
        hits = merge_hit_xml(hits, parse_xml2(xml2))
    # Top 10 all-hit table: input already usually top 10, but preserve order.
    all_rows = [_hit_to_row(h, round_id) for h in hits]
    # One best row per query by bitscore.
    by_query: dict[str, HitRecord] = {}
    for h in hits:
        if h.query_id not in by_query or h.bitscore > by_query[h.query_id].bitscore:
            by_query[h.query_id] = h
    top_rows = [_hit_to_row(h, round_id) for h in by_query.values()]

    _write_csv(parsed_dir / "BLASTP_all_hits_top10.csv", all_rows, HIT_FIELDS)
    _write_csv(parsed_dir / "BLASTP_top_hits_by_query.csv", top_rows, HIT_FIELDS)
    _write_csv(parsed_dir / "BLASTP_BGC_summary.csv", summarize_bgc_rows(top_rows), BGC_FIELDS)

    row={
        "store_version": STORE_VERSION,
        "ingested_utc": datetime.now(timezone.utc).isoformat(),
        "strain": strain,
        "round_id": round_id,
        "purpose": purpose,
        "operator_note": operator_note,
        "query_count": len(by_query),
        "all_hit_count": len(hits),
        "raw_files": copied,
        "claim_safety": CLAIM_SAFETY,
    }
    _append_jsonl(manifest_path, row)
    rebuild_cumulative_tables(store)
    return row


def rebuild_cumulative_tables(store_dir: str | Path) -> None:
    store=Path(store_dir)
    all_rows=[]; top_rows=[]
    for p in sorted((store / "parsed_rounds").glob("*/BLASTP_all_hits_top10.csv")):
        with p.open(newline="", encoding="utf-8") as fh:
            all_rows.extend(csv.DictReader(fh))
    for p in sorted((store / "parsed_rounds").glob("*/BLASTP_top_hits_by_query.csv")):
        with p.open(newline="", encoding="utf-8") as fh:
            top_rows.extend(csv.DictReader(fh))
    cum=store / "cumulative"
    _write_csv(cum / "BLASTP_all_hits_top10_all_rounds.csv", all_rows, HIT_FIELDS)
    _write_csv(cum / "BLASTP_top_hits_by_query_all_rounds.csv", top_rows, HIT_FIELDS)
    _write_csv(cum / "BLASTP_BGC_summary_all_rounds.csv", summarize_bgc_rows(top_rows), BGC_FIELDS)
    write_store_readme(store)


def write_store_readme(store: Path) -> None:
    txt = f"""# BLASTP Evidence Store\n\nStore version: `{STORE_VERSION}`\n\nThis directory preserves iterative NCBI BLASTP evidence. Raw XML2/Hit Table CSV\nfiles are stored under `raw_ncbi_downloads/`; parsed per-round tables are stored\nunder `parsed_rounds/`; cumulative all-round tables are stored under `cumulative/`.\n\nClaim safety: {CLAIM_SAFETY}\n\nRecommended reader-facing report use: cite BGC-level summaries and representative\nclass-defining rows. Keep raw files in the archive for auditability.\n"""
    _atomic_write_text(store / "README_BLASTP_EVIDENCE_STORE.md", txt)
