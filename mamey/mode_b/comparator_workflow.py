"""Comparator workflow detection for Mode B (v9.7.143a).

When repeated BLASTP evidence points to the same external comparator strain,
Sapote–Mamey should guide the user to the next decisive evidence step: run or
upload comparator antiSMASH, then perform synteny/missing-gene/domain analysis.
"""
from __future__ import annotations

from typing import Any

COMPARATOR_WORKFLOW_REQUIRED: list[str] = [
    "node",
    "locus",
    "protein_length_aa",
    "top_hit_accession",
    "top_hit_species",
    "percent_identity",
    "percent_similarity",
    "query_coverage_pct",
    "gene_function_call",
    "modeb_role",
]


def _accession_series_hint(accessions: list[str]) -> bool:
    nums = []
    for acc in accessions:
        acc = str(acc or "")
        digits = "".join(ch for ch in acc if ch.isdigit())
        if digits:
            try:
                nums.append(int(digits[-9:]))
            except Exception:
                pass
    if len(nums) < 3:
        return False
    nums = sorted(set(nums))
    return (max(nums) - min(nums)) <= 100 and len(nums) >= 3


def detect_comparator_workflows(modeb_gene_table) -> list[dict[str, Any]]:
    """Detect comparator strains/genomes that should trigger user next-step cards.

    Accepts a pandas DataFrame-like object. Pandas is not imported at module import
    time so this helper does not change core package import behavior.
    """

    missing = [c for c in COMPARATOR_WORKFLOW_REQUIRED if c not in modeb_gene_table.columns]
    if missing:
        raise ValueError(f"Comparator workflow cannot run; missing columns: {missing}")

    grouped = (
        modeb_gene_table
        .dropna(subset=["top_hit_species"])
        .groupby("top_hit_species", dropna=True)
        .agg(
            n_genes=("locus", "count"),
            n_nodes=("node", "nunique"),
            nodes=("node", lambda x: ";".join(sorted(set(str(v) for v in x)))),
            genes=("locus", lambda x: ";".join(str(v) for v in x)),
            accessions=("top_hit_accession", lambda x: ";".join(str(v) for v in x if str(v) != "nan")),
        )
        .reset_index()
    )

    workflows: list[dict[str, Any]] = []
    for _, row in grouped.iterrows():
        accessions = [a for a in str(row["accessions"]).split(";") if a]
        accession_hint = _accession_series_hint(accessions)
        if int(row["n_genes"]) >= 3 or int(row["n_nodes"]) >= 2 or accession_hint:
            workflows.append({
                "schema_version": "mode_b_comparator_workflow_v1",
                "comparator": row["top_hit_species"],
                "trigger": "multi-gene or multi-node comparator signal" + ("; neighborhood-like accession series" if accession_hint else ""),
                "nodes": row["nodes"],
                "genes": row["genes"],
                "accessions": row["accessions"],
                "external_antismash_needed": True,
                "user_action": f"Run antiSMASH on {row['top_hit_species']} or upload existing antiSMASH output.",
                "after_upload": [
                    "locate matching accession neighborhood",
                    "build comparator locus map",
                    "score synteny, strand, and missing intervals",
                    "update Mode B claim-safety status",
                ],
                "claim_safety": "candidate linkage only until comparator synteny/domain evidence is reviewed",
            })

    return workflows


def render_comparator_workflow_card(workflow: dict[str, Any]) -> str:
    """Render a user-facing comparator workflow card."""

    after_upload = workflow.get("after_upload") or []
    after = "\n".join(f"  - {item}" for item in after_upload)
    return f"""Comparator next step detected

Several genes in this Mode B candidate map to the same external comparator:
  {workflow.get('comparator', 'UNKNOWN')}

Trigger:
  {workflow.get('trigger', 'multi-gene comparator signal')}

Nodes:
  {workflow.get('nodes', '')}

Genes:
  {workflow.get('genes', '')}

Recommended user action:
  {workflow.get('user_action', '')}

Why:
  This is needed to test whether the contigs represent a split/composite BGC,
  a parallel related BGC, or unrelated conserved modules.

After upload, Sapote–Mamey will:
{after}

Claim safety:
  {workflow.get('claim_safety', 'candidate linkage only')}
"""
