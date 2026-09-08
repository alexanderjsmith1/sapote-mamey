#!/usr/bin/env python3
"""Audit a Mode B support card and, optionally, its task progress ledger.

This gate checks provenance structure and claim ceilings. It does not judge the
biology and does not replace BLASTP verification or the claim-safety linter.
"""
from __future__ import annotations

import os as _os, sys as _sys  # v9.7.407: resolve the tools-local emitter from any cwd
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
from _console import emit  # noqa: E402

import argparse
import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

# v9.7.363 NOTE: the literal author paths below are DETECTION PATTERNS, not configuration.
# This tool exists to FIND workspace paths leaking into Mode B cards, so parametrising them
# through $SAPOTE_WORKSPACE_ROOT would break the guard. They are intentionally literal and are
# the documented exception to the .361/.363 path-genericisation pass.

ALLOWED_TIERS = {
    "THESIS_READY",
    "USEFUL_WITH_LIMITATIONS",
    "CONTEXT_ONLY",
    "HOLD",
}

REQUIRED_TOPICS = {
    "recovery disposition": r"^##\s+Recovery disposition",
    "executive verdict": r"^##\s+Executive verdict",
    "source lock": r"^##\s+\d+\.\s+Source lock",
    "gene verdicts": r"^##\s+\d+\.\s+Complete gene-by-gene verdict",
    "homology channels": r"^##\s+\d+\.\s+Homology channels",
    "architecture": r"^##\s+\d+\.\s+Captured architecture",
    "cluster comparison": r"^##\s+\d+\.\s+Cluster-comparison evidence",
    "cohort/cross-contig": r"^##\s+\d+\.\s+Cohort and cross-contig context",
    "taxonomy/ecology/activity": r"^##\s+\d+\.\s+Taxonomy, ecology, and activity",
    "value tier": r"^##\s+\d+\.\s+Value tier",
    "missing evidence": r"^##\s+\d+\.\s+Missing evidence",
    "QA receipt": r"^##\s+\d+\.\s+QA receipt",
}


@dataclass
class Result:
    path: str
    pass_gate: bool = True
    findings: list[dict] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def add(self, code: str, message: str, severity: str = "ERROR") -> None:
        self.findings.append({"severity": severity, "code": code, "message": message})
        if severity == "ERROR":
            self.pass_gate = False


def _meta(text: str, label: str) -> str | None:
    match = re.search(
        rf"^\s*-\s+\*\*{re.escape(label)}:\*\*\s*(.+?)\s*$",
        text,
        re.MULTILINE | re.IGNORECASE,
    )
    if not match:
        return None
    return match.group(1).strip().strip("`")


def _integer(value: str | None) -> int | None:
    if value is None:
        return None
    match = re.search(r"\d+", value)
    return int(match.group()) if match else None


def _absolute_sources(text: str) -> list[str]:
    sources = []
    for raw in re.findall(r"`((?:/Users|/home)/[^/`]+/[^`]+)`", text):
        path = raw.split("::", 1)[0]
        if not any(token in path for token in ("<", ">", "*")):
            sources.append(path)
    return sorted(set(sources))


def _ledger_row(ledger: Path, rank: int) -> dict | None:
    with ledger.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if _integer(row.get("priority_rank")) == rank:
                return row
    return None


def audit_card(
    card: Path,
    *,
    ledger: Path | None = None,
    rank_min: int | None = None,
    rank_max: int | None = None,
    check_sources: bool = True,
) -> Result:
    result = Result(str(card))
    if not card.is_file():
        result.add("CARD_MISSING", f"card does not exist: {card}")
        return result

    text = card.read_text(encoding="utf-8")
    lower = text.lower()

    if "/Users/<user>/<workspace>" in text:
        result.add("FORBIDDEN_WORKSPACE", "card cites the forbidden Claude workspace")

    for topic, pattern in REQUIRED_TOPICS.items():
        if not re.search(pattern, text, re.MULTILINE | re.IGNORECASE):
            result.add("SECTION_MISSING", f"required section missing: {topic}")

    rank = _integer(_meta(text, "Priority rank"))
    tier = _meta(text, "Value tier")
    qa = _meta(text, "QA status")
    expected = _integer(_meta(text, "Expected proteins"))
    direct = _integer(_meta(text, "Direct-hit union"))
    no_hit = _integer(_meta(text, "No-significant-hit proteins"))
    unresolved = _integer(_meta(text, "Unresolved/unavailable direct-query proteins"))
    unresolved = unresolved if unresolved is not None else 0

    for field_name, value in (
        ("Priority rank", rank),
        ("Value tier", tier),
        ("QA status", qa),
        ("Expected proteins", expected),
        ("Direct-hit union", direct),
        ("No-significant-hit proteins", no_hit),
    ):
        if value is None:
            result.add("METADATA_MISSING", f"required metadata missing: {field_name}")

    if rank is not None:
        if rank_min is not None and rank < rank_min:
            result.add("RANK_OUT_OF_RANGE", f"rank {rank} is below {rank_min}")
        if rank_max is not None and rank > rank_max:
            result.add("RANK_OUT_OF_RANGE", f"rank {rank} is above {rank_max}")

    if tier is not None and tier not in ALLOWED_TIERS:
        result.add("VALUE_TIER_INVALID", f"unsupported value tier: {tier}")

    if qa and qa == "PENDING_FINAL_VALIDATION":
        result.add("QA_PENDING", "QA status still PENDING_FINAL_VALIDATION")

    if _meta(text, "Claim ceiling") is None:
        result.add("CLAIM_CEILING_MISSING", "claim ceiling metadata is missing")

    genes = set(re.findall(r"`(ctg\d+_\d+)`", text))
    if expected is not None and len(genes) != expected:
        result.add(
            "GENE_DENOMINATOR_MISMATCH",
            f"expected {expected} unique locus tags but found {len(genes)}: {sorted(genes)}",
        )

    if None not in (expected, direct, no_hit):
        accounted = int(direct) + int(no_hit) + int(unresolved)
        if accounted != expected:
            result.add(
                "DIRECT_COVERAGE_MISMATCH",
                f"direct + no-hit + unresolved = {accounted}, expected {expected}",
            )

    for channel in ("NCBI nr", "EBI", "Local Swiss-Prot"):
        if channel.lower() not in lower:
            result.add("CHANNEL_MISSING", f"homology channel missing: {channel}")

    for comparison in (
        "General ClusterBlast",
        "KnownClusterBlast",
        "SubClusterBlast",
        "BiG-SCAPE",
        "RG-GMCI",
    ):
        if comparison.lower() not in lower:
            result.add("COMPARISON_MISSING", f"comparison channel missing: {comparison}")

    urls = re.findall(r"https?://[^\s)>]+", text)
    if direct and direct > 0 and not urls:
        result.add("VISIBLE_URL_MISSING", "direct-hit union is nonzero but no public URL is visible")

    if "rggmci" in lower or "rg-gmci" in lower:
        # v9.7.371 fix: the 4th disjunct checked "physical linkage" in lower and "not" in lower
        # as two INDEPENDENT, unanchored substring tests over the ENTIRE card text -- not "not"
        # adjacent to "physical linkage". "not" is a substring of extremely common words
        # (annotation, note, noted, notes, nothing, cannot), so it is present in virtually any
        # real card regardless of whether an actual linkage-ceiling disclaimer exists. As soon as
        # the phrase "physical linkage" appeared ANYWHERE (even just naming the concept with no
        # negation) and "not" appeared ANYWHERE ELSE (near-certain), has_linkage_ceiling was
        # always True and this claim-safety gate silently passed cards asserting RG-GMCI evidence
        # with no real disclaimer that RG-GMCI does not establish physical linkage. Require the
        # negation to actually be near the phrase instead of anywhere in the document.
        has_linkage_ceiling = (
            "not_linked_across_contigs" in lower
            or "not physically linked" in lower
            or "no physical" in lower
            or bool(re.search(r"\bnot\b[^.]{0,60}physical linkage|physical linkage[^.]{0,60}\bnot\b", lower))
        )
        if not has_linkage_ceiling:
            result.add("RGGMCI_CEILING_MISSING", "RG-GMCI appears without a physical-linkage ceiling")

    if "strain_level_capture" in lower or "strain-level capture" in lower:
        if not (
            "secondary aggregation" in lower
            or "not independent validation" in lower
            or "secondary synthesis" in lower
        ):
            result.add(
                "STRAIN_CAPTURE_CEILING_MISSING",
                "strain-level capture appears without a secondary-aggregation ceiling",
            )

    production = re.search(
        r"\b(?:BGC\d+|locus|cluster)\s+(?:produces|makes|synthesizes|"
        r"biosynthesizes|is active against)\b",
        text,
        re.IGNORECASE,
    )
    if production:
        result.add("LOCUS_PHENOTYPE_OVERCLAIM", f"unqualified locus claim: {production.group(0)}")

    if check_sources:
        for source in _absolute_sources(text):
            if not Path(source).exists():
                result.add("SOURCE_PATH_MISSING", f"cited source does not exist: {source}")

    if ledger is not None:
        if not ledger.is_file():
            result.add("LEDGER_MISSING", f"ledger does not exist: {ledger}")
        elif rank is not None:
            row = _ledger_row(ledger, rank)
            if row is None:
                result.add("LEDGER_ROW_MISSING", f"ledger has no row for rank {rank}")
            else:
                checks = {
                    "markdown_path": str(card),
                    "value_tier": tier,
                    "qc_status": qa,
                    "expected_genes": str(expected) if expected is not None else None,
                    "direct_hit_union": str(direct) if direct is not None else None,
                    "no_significant_hit": str(no_hit) if no_hit is not None else None,
                }
                for key, expected_value in checks.items():
                    if expected_value is not None and (row.get(key) or "").strip() != expected_value:
                        result.add(
                            "LEDGER_MISMATCH",
                            f"{key}: card={expected_value!r}, ledger={(row.get(key) or '').strip()!r}",
                        )

    result.stats = {
        "priority_rank": rank,
        "value_tier": tier,
        "qa_status": qa,
        "expected_genes": expected,
        "unique_gene_tags": len(genes),
        "direct_hit_union": direct,
        "no_significant_hit": no_hit,
        "unresolved": unresolved,
        "visible_urls": len(urls),
        "absolute_sources": len(_absolute_sources(text)),
        "errors": sum(f["severity"] == "ERROR" for f in result.findings),
        "warnings": sum(f["severity"] == "WARN" for f in result.findings),
    }
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit a Mode B support card.")
    parser.add_argument("card", type=Path)
    parser.add_argument("--ledger", type=Path)
    parser.add_argument("--rank-min", type=int)
    parser.add_argument("--rank-max", type=int)
    parser.add_argument("--skip-source-existence", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = audit_card(
        args.card,
        ledger=args.ledger,
        rank_min=args.rank_min,
        rank_max=args.rank_max,
        check_sources=not args.skip_source_existence,
    )
    payload = {
        "pass": result.pass_gate,
        "path": result.path,
        **result.stats,
        "findings": result.findings,
    }
    if args.json:
        emit(json.dumps(payload, indent=2))
    else:
        emit(f"modeb-support-card — {'PASS' if result.pass_gate else 'FAIL'} — {args.card}")
        for finding in result.findings:
            emit(f"  {finding['severity']} {finding['code']}: {finding['message']}")
    return 0 if result.pass_gate else 1


if __name__ == "__main__":
    raise SystemExit(main())

