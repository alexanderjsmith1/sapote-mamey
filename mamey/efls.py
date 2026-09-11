"""EFLS Rewire: evidence-first linkage scoring for fragmented BGC groups.

EFLS = Evidence for Fragment Linkage and Split-pathway status.

The module consumes Pre-Sapote Lite gene evidence tables and optional user-defined
groups. It classifies each contig pair as:

- physical_linkage_supported
- possible_split_pathway
- functional_grouping_only
- do_not_merge

This prevents useful PKS fragment groups from being over-claimed as one physical
BGC while still preserving evidence that fragments may belong to a split pathway.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Literal
import csv
try:
    from .csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter  # v9.7.410 CSV formula-cell guard (CLAUDE_410_csv_writer_coverage)
except ImportError:
    from mamey.csv_safety import SafeDictWriter as _SafeDictWriter, SafeWriter as _SafeWriter
import itertools
import json
import re

LinkageClass = Literal[
    "physical_linkage_supported",
    "possible_split_pathway",
    "functional_grouping_only",
    "do_not_merge",
]

CORE_DOMAIN_TOKENS = {"KS", "AT", "DH", "KR", "ER", "ACP", "PP", "A", "PCP", "Cy", "TE", "CAL_domain", "CAL"}
DOCKING_TOKENS = {"Dock-N", "Dock-C", "TransAT-dock", "PKS_Docking_Nterm", "PKS_Docking_Cterm", "Trans-AT_docking"}
# v9.7.151 (bunny-hop): FORBIDDEN_PRIMARY_BACKGROUND_NODES = {"NODE_11"} removed —
# orphaned, zero readers anywhere in the codebase. The real, named strain-specific
# rule (calibrated on AS-XXX) lives in AS-XXX_forbidden_merge() below and uses the
# NODE_11 literal inline with its full exclusion set documented there.

@dataclass(frozen=True)
class FragmentSummary:
    group_id: str
    node: str
    gene_count: int
    tier_a_count: int
    core_gene_count: int
    pks_gene_count: int
    nrps_gene_count: int
    has_loading: bool
    has_chain_extension: bool
    has_terminal_release: bool
    has_docking: bool
    domain_tokens: tuple[str, ...]
    mibig_contexts: tuple[str, ...]
    mean_coverage: float | None = None
    gc_percent: float | None = None

@dataclass(frozen=True)
class LinkageEvidence:
    node_a: str
    node_b: str
    docking_support: float = 0.0
    domain_complementarity: float = 0.0
    shared_kcb_family: bool = False
    coverage_gc_consistency: float = 0.0
    assembly_penalty: float = 0.0
    forbidden_merge: bool = False

@dataclass(frozen=True)
class LinkageResult:
    group_id: str
    node_a: str
    node_b: str
    linkage_class: LinkageClass
    score: float
    docking_support: float
    domain_complementarity: float
    shared_kcb_family: bool
    coverage_gc_consistency: float
    assembly_penalty: float
    forbidden_merge: bool
    rationale: str

def _float_or_none(value: object) -> float | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return float(value)
    except Exception:
        return None

def _node_token(value: object) -> str:
    text = str(value)
    if text.startswith("NODE_"):
        return text
    try:
        return f"NODE_{int(float(text))}"
    except Exception:
        return text

def _split_domains(text: str) -> set[str]:
    if not text:
        return set()
    text = text.replace("–", ";").replace("-", "-")
    parts = re.split(r"[;,|/ ]+", text)
    tokens = {p.strip() for p in parts if p.strip()}
    # normalize common Pre-Sapote Lite labels
    aliases = {
        "PKS_KS": "KS",
        "PKS_AT": "AT",
        "PKS_DH": "DH",
        "PKS_KR": "KR",
        "PKS_ER": "ER",
        "PKS_PP": "PP",
        "AMP-binding": "A",
        "Thioesterase": "TE",
        "Heterocyclization": "Cy",
    }
    return {aliases.get(t, t) for t in tokens}

def _has_any(tokens: set[str], choices: set[str]) -> bool:
    return bool(tokens & choices)

def summarize_gene_evidence(gene_evidence_csv: Path) -> list[FragmentSummary]:
    by_node: dict[tuple[str, str], list[dict]] = {}
    with gene_evidence_csv.open(newline="") as handle:
        for row in csv.DictReader(handle):
            group = row.get("set_id") or "Ungrouped"
            node = row.get("node") or _node_token(row.get("node_num", "NODE_UNKNOWN"))
            by_node.setdefault((group, node), []).append(row)

    summaries: list[FragmentSummary] = []
    for (group, node), rows in sorted(by_node.items()):
        domain_tokens: set[str] = set()
        mibig_contexts: set[str] = set()
        coverages: list[float] = []
        gcs: list[float] = []
        core_count = pks_count = nrps_count = tier_a = 0
        for row in rows:
            tokens = _split_domains(row.get("antiSMASH_domains") or row.get("domains") or "")
            domain_tokens |= tokens
            if row.get("mibig_context"):
                mibig_contexts.add(row["mibig_context"])
            coverage = _float_or_none(row.get("coverage") or row.get("cov"))
            if coverage is not None:
                coverages.append(coverage)
            gc = _float_or_none(row.get("gc_percent") or row.get("gc"))
            if gc is not None:
                gcs.append(gc)
            role = (row.get("source_role") or row.get("role") or "").lower()
            if row.get("evidence_tier") == "A":
                tier_a += 1
            if "pks" in role or tokens & {"KS", "AT", "DH", "KR", "ER", "ACP", "PP", "CAL", "CAL_domain", "TE"}:
                core_count += 1
                pks_count += 1
            if "nrps" in role or "adenylation" in role or tokens & {"A", "PCP", "Cy"}:
                core_count += 1
                nrps_count += 1

        has_loading = _has_any(domain_tokens, {"CAL", "CAL_domain", "A"})
        has_chain_extension = _has_any(domain_tokens, {"KS", "AT", "DH", "KR", "ER", "ACP", "PP"})
        has_terminal_release = _has_any(domain_tokens, {"TE", "Thioesterase"})
        has_docking = _has_any(domain_tokens, DOCKING_TOKENS)
        summaries.append(FragmentSummary(
            group_id=group,
            node=node,
            gene_count=len(rows),
            tier_a_count=tier_a,
            core_gene_count=core_count,
            pks_gene_count=pks_count,
            nrps_gene_count=nrps_count,
            has_loading=has_loading,
            has_chain_extension=has_chain_extension,
            has_terminal_release=has_terminal_release,
            has_docking=has_docking,
            domain_tokens=tuple(sorted(domain_tokens)),
            mibig_contexts=tuple(sorted(mibig_contexts)),
            mean_coverage=(sum(coverages) / len(coverages)) if coverages else None,
            gc_percent=(sum(gcs) / len(gcs)) if gcs else None,
        ))
    return summaries

def shared_kcb_or_mibig(a: FragmentSummary, b: FragmentSummary) -> bool:
    if not a.mibig_contexts or not b.mibig_contexts:
        return False
    a_words = {w.lower() for ctx in a.mibig_contexts for w in re.findall(r"[A-Za-z0-9_.-]+", ctx)}
    b_words = {w.lower() for ctx in b.mibig_contexts for w in re.findall(r"[A-Za-z0-9_.-]+", ctx)}
    shared = a_words & b_words
    # ignore generic tokens
    shared = {w for w in shared if w not in {"bgc", "mibig", "like", "cluster", "unknown"} and len(w) > 3}
    return bool(shared)

def domain_complementarity_score(a: FragmentSummary, b: FragmentSummary) -> float:
    score = 0.0
    if (a.has_loading and b.has_chain_extension) or (b.has_loading and a.has_chain_extension):
        score += 0.75
    if (a.has_terminal_release and b.has_chain_extension) or (b.has_terminal_release and a.has_chain_extension):
        score += 0.75
    if a.has_chain_extension and b.has_chain_extension:
        score += 0.35
    if (a.pks_gene_count and b.nrps_gene_count) or (b.pks_gene_count and a.nrps_gene_count):
        score += 0.25
    shared_domains = set(a.domain_tokens) & set(b.domain_tokens)
    if {"KS", "AT"} & shared_domains:
        score += 0.15
    return round(min(score, 1.8), 3)

def docking_score(a: FragmentSummary, b: FragmentSummary) -> float:
    if a.has_docking and b.has_docking:
        return 1.2
    if a.has_docking or b.has_docking:
        return 0.55
    return 0.0

def coverage_gc_score(a: FragmentSummary, b: FragmentSummary) -> float:
    score = 0.0
    if a.mean_coverage is not None and b.mean_coverage is not None:
        denom = max(a.mean_coverage, b.mean_coverage, 1.0)
        rel_diff = abs(a.mean_coverage - b.mean_coverage) / denom
        if rel_diff <= 0.15:
            score += 0.4
        elif rel_diff <= 0.30:
            score += 0.2
    if a.gc_percent is not None and b.gc_percent is not None:
        if abs(a.gc_percent - b.gc_percent) <= 1.0:
            score += 0.3
        elif abs(a.gc_percent - b.gc_percent) <= 2.0:
            score += 0.15
    return round(score, 3)

def assembly_penalty(a: FragmentSummary, b: FragmentSummary) -> float:
    penalty = 0.0
    # Very small context-only fragments are weak linkage evidence.
    if a.tier_a_count == 0 or b.tier_a_count == 0:
        penalty += 0.25
    if a.core_gene_count == 0 or b.core_gene_count == 0:
        penalty += 0.35
    return round(penalty, 3)

_NODE_PREFIX_RE = re.compile(r"^(NODE_\d+)", re.I)

def _bare_node(node: object) -> str:
    """Extract the bare 'NODE_<int>' token from a possibly-suffixed contig/node string
    (e.g. 'NODE_11_length_45678_cov_32.1' -> 'NODE_11'), so the exact-literal AS-XXX
    forbidden-merge list below still matches regardless of whether the caller's node
    string is already bare or carries the standard SPAdes length/cov suffix used
    everywhere else in this codebase (crosswalk.py::contig_key, BGCRecord.node_id)."""
    m = _NODE_PREFIX_RE.match(str(node or "").strip())
    return (m.group(1) if m else str(node or "").strip()).upper()

def forbidden_node_merge(node_a: str, node_b: str) -> bool:
    nodes = {_bare_node(node_a), _bare_node(node_b)}
    return "NODE_11" in nodes and bool(nodes & {"NODE_96", "NODE_107", "NODE_24", "NODE_249", "NODE_456", "NODE_58"})

def classify_linkage(evidence: LinkageEvidence) -> LinkageClass:
    if evidence.forbidden_merge:
        return "do_not_merge"
    score = linkage_score(evidence)
    if score >= 3.2:
        return "physical_linkage_supported"
    if score >= 2.0:
        return "possible_split_pathway"
    if score >= 0.8:
        return "functional_grouping_only"
    return "do_not_merge"

def linkage_score(evidence: LinkageEvidence) -> float:
    return round(
        evidence.docking_support
        + evidence.domain_complementarity
        + (0.75 if evidence.shared_kcb_family else 0.0)
        + evidence.coverage_gc_consistency
        - evidence.assembly_penalty,
        3,
    )

def pair_evidence(a: FragmentSummary, b: FragmentSummary) -> LinkageEvidence:
    forbidden = forbidden_node_merge(a.node, b.node)
    return LinkageEvidence(
        node_a=a.node,
        node_b=b.node,
        docking_support=docking_score(a, b),
        domain_complementarity=domain_complementarity_score(a, b),
        shared_kcb_family=shared_kcb_or_mibig(a, b),
        coverage_gc_consistency=coverage_gc_score(a, b),
        assembly_penalty=assembly_penalty(a, b),
        forbidden_merge=forbidden,
    )

def rationale_for(evidence: LinkageEvidence, klass: LinkageClass) -> str:
    bits = []
    if evidence.forbidden_merge:
        bits.append("forbidden background/primary-hypothesis merge")
    if evidence.docking_support:
        bits.append(f"docking={evidence.docking_support}")
    if evidence.domain_complementarity:
        bits.append(f"domain_complementarity={evidence.domain_complementarity}")
    if evidence.shared_kcb_family:
        bits.append("shared comparator/KCB tokens")
    if evidence.coverage_gc_consistency:
        bits.append(f"coverage_gc={evidence.coverage_gc_consistency}")
    if evidence.assembly_penalty:
        bits.append(f"assembly_penalty={evidence.assembly_penalty}")
    if not bits:
        bits.append("insufficient direct linkage evidence")
    return f"{klass}: " + "; ".join(bits)

def build_efls_results(gene_evidence_csv: Path) -> tuple[list[FragmentSummary], list[LinkageResult]]:
    summaries = summarize_gene_evidence(gene_evidence_csv)
    by_group: dict[str, list[FragmentSummary]] = {}
    for summary in summaries:
        by_group.setdefault(summary.group_id, []).append(summary)
    results: list[LinkageResult] = []
    for group, fragments in by_group.items():
        for a, b in itertools.combinations(fragments, 2):
            evidence = pair_evidence(a, b)
            klass = classify_linkage(evidence)
            score = linkage_score(evidence)
            results.append(LinkageResult(
                group_id=group,
                node_a=a.node,
                node_b=b.node,
                linkage_class=klass,
                score=score,
                docking_support=evidence.docking_support,
                domain_complementarity=evidence.domain_complementarity,
                shared_kcb_family=evidence.shared_kcb_family,
                coverage_gc_consistency=evidence.coverage_gc_consistency,
                assembly_penalty=evidence.assembly_penalty,
                forbidden_merge=evidence.forbidden_merge,
                rationale=rationale_for(evidence, klass),
            ))
    return summaries, results

def write_efls_outputs(gene_evidence_csv: Path, out_dir: Path) -> dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    summaries, results = build_efls_results(gene_evidence_csv)

    frag_path = out_dir / "EFLS_Fragment_Summary.csv"
    with frag_path.open("w", newline="") as handle:
        fieldnames = list(asdict(summaries[0]).keys()) if summaries else ["group_id", "node"]
        writer = _SafeDictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for summary in summaries:
            row = asdict(summary)
            row["domain_tokens"] = ";".join(summary.domain_tokens)
            row["mibig_contexts"] = " | ".join(summary.mibig_contexts)
            writer.writerow(row)

    link_path = out_dir / "EFLS_Linkage_Table.csv"
    with link_path.open("w", newline="") as handle:
        fieldnames = list(asdict(results[0]).keys()) if results else ["group_id", "node_a", "node_b", "linkage_class"]
        writer = _SafeDictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for result in results:
            writer.writerow(asdict(result))

    group_path = out_dir / "EFLS_Group_Assignments.csv"
    group_rows = []
    by_group: dict[str, list[LinkageResult]] = {}
    for result in results:
        by_group.setdefault(result.group_id, []).append(result)
    for group in sorted({s.group_id for s in summaries}):
        group_results = by_group.get(group, [])
        classes = {r.linkage_class for r in group_results}
        if "physical_linkage_supported" in classes:
            assignment = "has_physical_linkage_support"
        elif "possible_split_pathway" in classes:
            assignment = "possible_split_pathway"
        elif "functional_grouping_only" in classes:
            assignment = "functional_grouping_only"
        else:
            assignment = "single_fragment_or_do_not_merge"
        group_rows.append({"group_id": group, "assignment": assignment, "pair_count": len(group_results)})
    with group_path.open("w", newline="") as handle:
        writer = _SafeDictWriter(handle, fieldnames=["group_id", "assignment", "pair_count"])
        writer.writeheader()
        writer.writerows(group_rows)

    report_path = out_dir / "EFLS_Report.md"
    lines = ["# EFLS Rewire Report", "", "## Group assignments", ""]
    for row in group_rows:
        lines.append(f"- **{row['group_id']}**: {row['assignment']} ({row['pair_count']} pairs)")
    lines += ["", "## Linkage classes", ""]
    for result in results:
        lines.append(f"- {result.group_id}: {result.node_a} ↔ {result.node_b} = **{result.linkage_class}** (score {result.score}) — {result.rationale}")
    report_path.write_text("\n".join(lines), encoding="utf-8")

    receipt = {
        "gene_evidence_csv": str(gene_evidence_csv),
        "fragment_count": len(summaries),
        "pair_count": len(results),
        "outputs": {
            "fragment_summary": str(frag_path),
            "linkage_table": str(link_path),
            "group_assignments": str(group_path),
            "report": str(report_path),
        },
    }
    receipt_path = out_dir / "EFLS_RECEIPT.json"
    receipt_path.write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return {**receipt["outputs"], "receipt": str(receipt_path)}
