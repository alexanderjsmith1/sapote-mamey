"""B2 Phase 2 structured evaluator framework.

This module converts a small first batch of registry manual cassettes into
deterministic support/caution evaluators. It intentionally does NOT globally
activate Phase 2 backends (HMMER/DIAMOND/BLASTP), alter scoring, or claim
product identity.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from importlib import resources
from pathlib import Path
from typing import Any, Iterable
import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import json
import re


FIRST_BATCH_IDS = ("SMC-001", "SMC-002", "SMC-004", "SMC-009", "SMC-013", "SMC-016")


@dataclass(frozen=True)
class StructuredCassetteCall:
    cassette_id: str
    cassette_name: str
    status: str  # SUPPORT, CAUTION, ABSENT
    support_flags: list[str]
    caution_flags: list[str]
    evidence_loci: list[str]
    evidence_terms: list[str]
    claim_ceiling: str


def _data_path(name: str) -> Path:
    try:
        return Path(resources.files("mamey") / "data" / "b2_structured_evaluators" / name)
    except Exception:
        return Path(__file__).resolve().parent / "data" / "b2_structured_evaluators" / name


def load_structured_evaluator_rules(path: str | Path | None = None) -> dict[str, Any]:
    p = Path(path) if path else _data_path("b2_structured_evaluator_rules.json")
    return json.loads(p.read_text(encoding="utf-8"))


def normalize_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for r in rows:
        out.append({str(k): "" if v is None else str(v) for k, v in r.items()})
    return out


def read_annotation_rows_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return normalize_rows(csv.DictReader(handle))


def _row_blob(row: dict[str, str]) -> str:
    keys = [
        "product", "annotation", "gene_kind", "domains", "markers", "class_context",
        "bgc_class", "products", "context", "notes",
    ]
    return " ".join(row.get(k, "") for k in keys).lower()


def _all_blob(rows: list[dict[str, str]]) -> str:
    return "\n".join(_row_blob(r) for r in rows)


def _patterns_hit(blob: str, patterns: Iterable[str]) -> list[str]:
    hits: list[str] = []
    for pat in patterns:
        if re.search(pat, blob, re.I):
            hits.append(pat)
    return hits


def _patterns_all_hit(blob: str, patterns: Iterable[str]) -> list[str]:
    hits = _patterns_hit(blob, patterns)
    return hits if len(hits) == len(list(patterns)) else []


def _evidence_loci(rows: list[dict[str, str]], patterns: Iterable[str]) -> list[str]:
    loci: list[str] = []
    for r in rows:
        blob = _row_blob(r)
        if any(re.search(pat, blob, re.I) for pat in patterns):
            loc = r.get("locus_tag") or r.get("gene_id") or r.get("protein_id") or r.get("query_id") or "unknown_locus"
            if loc not in loci:
                loci.append(loc)
    return loci


def _call_absent(rule: dict[str, Any]) -> StructuredCassetteCall:
    return StructuredCassetteCall(
        cassette_id=rule["id"],
        cassette_name=rule.get("name", rule["id"]),
        status="ABSENT",
        support_flags=[],
        caution_flags=[],
        evidence_loci=[],
        evidence_terms=[],
        claim_ceiling=rule.get("claim_ceiling", "support/caution only"),
    )


def _support_call(rule: dict[str, Any], rows: list[dict[str, str]], hits: list[str], caution: list[str] | None = None) -> StructuredCassetteCall:
    caution = caution or []
    evidence_patterns = hits + caution
    return StructuredCassetteCall(
        cassette_id=rule["id"],
        cassette_name=rule.get("name", rule["id"]),
        status="SUPPORT" if not caution else "SUPPORT_WITH_CAUTION",
        support_flags=[f"{rule['id']}_SUPPORT"],
        caution_flags=[f"{rule['id']}_CAUTION_{i+1}" for i, _ in enumerate(caution)] if caution else [],
        evidence_loci=_evidence_loci(rows, evidence_patterns),
        evidence_terms=evidence_patterns,
        claim_ceiling=rule.get("claim_ceiling", "support/caution only"),
    )


def _caution_call(rule: dict[str, Any], rows: list[dict[str, str]], caution: list[str]) -> StructuredCassetteCall:
    return StructuredCassetteCall(
        cassette_id=rule["id"],
        cassette_name=rule.get("name", rule["id"]),
        status="CAUTION",
        support_flags=[],
        caution_flags=[f"{rule['id']}_CAUTION_{i+1}" for i, _ in enumerate(caution)],
        evidence_loci=_evidence_loci(rows, caution),
        evidence_terms=caution,
        claim_ceiling=rule.get("claim_ceiling", "support/caution only"),
    )


def evaluate_rule(rows: Iterable[dict[str, Any]], rule: dict[str, Any]) -> StructuredCassetteCall:
    rows_n = normalize_rows(rows)
    blob = _all_blob(rows_n)

    required_all = list(rule.get("requires_all") or [])
    required_any = list(rule.get("requires_any") or [])
    context_any = list(rule.get("context_any") or [])
    optional_any = list(rule.get("optional_any") or [])
    negative_any = list(rule.get("negative_context_any") or [])

    negative_hits = _patterns_hit(blob, negative_any)

    # SMC-016 is special: negative context blocks support and emits caution only.
    if rule["id"] == "SMC-016":
        support_hits = _patterns_hit(blob, required_any)
        if support_hits and negative_hits:
            return _caution_call(rule, rows_n, negative_hits)
        if support_hits:
            return _support_call(rule, rows_n, support_hits)
        return _call_absent(rule)

    # SMC-004 guard: APH/AAC or sugar context alone must not support aminocyclitol.
    if rule["id"] == "SMC-004" and negative_hits and not _patterns_hit(blob, required_any):
        return _caution_call(rule, rows_n, negative_hits)

    # SMC-009 guard: FkbH+ACP can support, but mobile context produces support-with-caution.
    if required_all:
        hits = _patterns_all_hit(blob, required_all)
        if hits:
            return _support_call(rule, rows_n, hits, negative_hits)
        if negative_hits:
            return _caution_call(rule, rows_n, negative_hits)
        return _call_absent(rule)

    hits: list[str] = []
    if required_any:
        hits.extend(_patterns_hit(blob, required_any))
    if context_any:
        ctx = _patterns_hit(blob, context_any)
        if not hits or not ctx:
            return _call_absent(rule)
        hits.extend(ctx)
    if optional_any:
        hits.extend(_patterns_hit(blob, optional_any))

    if hits:
        return _support_call(rule, rows_n, hits, negative_hits)
    if negative_hits:
        return _caution_call(rule, rows_n, negative_hits)
    return _call_absent(rule)


def evaluate_structured_cassettes(
    rows: Iterable[dict[str, Any]],
    *,
    rules: dict[str, Any] | None = None,
    cassette_ids: Iterable[str] = FIRST_BATCH_IDS,
) -> list[StructuredCassetteCall]:
    rules = rules or load_structured_evaluator_rules()
    wanted = set(cassette_ids)
    by_id = {r["id"]: r for r in rules.get("first_batch", [])}
    return [evaluate_rule(rows, by_id[cid]) for cid in cassette_ids if cid in by_id and cid in wanted]


def support_calls(calls: Iterable[StructuredCassetteCall]) -> list[StructuredCassetteCall]:
    return [c for c in calls if c.status in {"SUPPORT", "SUPPORT_WITH_CAUTION"}]


def caution_calls(calls: Iterable[StructuredCassetteCall]) -> list[StructuredCassetteCall]:
    return [c for c in calls if c.status in {"CAUTION", "SUPPORT_WITH_CAUTION"}]


def calls_to_dicts(calls: Iterable[StructuredCassetteCall]) -> list[dict[str, Any]]:
    return [asdict(c) for c in calls]


def write_structured_evaluator_report(calls: Iterable[StructuredCassetteCall], out_csv: str | Path) -> Path:
    path = Path(out_csv)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = calls_to_dicts(calls)
    fieldnames = [
        "cassette_id", "cassette_name", "status", "support_flags", "caution_flags",
        "evidence_loci", "evidence_terms", "claim_ceiling",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = _SafeDictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            row = dict(row)
            for key in ("support_flags", "caution_flags", "evidence_loci", "evidence_terms"):
                row[key] = "; ".join(row.get(key) or [])
            writer.writerow(row)
    return path
