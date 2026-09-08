"""De-duplication / supersedure policy for Sapote–Mamey merges (v9.7.20).

WHY THIS EXISTS. When the same strain appears in two sources (e.g. a single-strain deep run AND a cohort
merge), a de-dup must keep one. Choosing by *schema tidiness* — "keep the cohort dialect, drop the standalone"
— silently discarded the richer AS-XXX standalone (full Mode B on 22 BGCs, DAPR scoring, 821 gene-by-gene +
635 domain-evidence rows, 44 A-domain substrate calls), an evidence-conservation failure. This module makes
the rule explicit and callable so the merge layer (which lives outside this engine tree) can enforce it:

  1. Prefer the RICHER source — more populated analytical evidence wins. Schema is normalized, never used as
     the tiebreaker that drops evidence.
  2. NEVER supersede a richer source with a tidier-but-poorer one.
  3. When neither source dominates (each is richer on some axis), do NOT auto-pick — CONSULT the user, because
     either choice loses evidence.

`signals` is a dict of named non-negative counts the merge already knows how to compute per source, e.g.
{"scored_bgcs": 64, "modeb_bgcs": 22, "domain_rows": 635, "gene_rows": 821, "adomain_calls": 44, "dapr_scored": 1}.
The policy is signal-agnostic: pass whatever richness signals you have; more is better.
"""
from __future__ import annotations


def _vec(signals: dict | None) -> dict:
    return {str(k): int(v or 0) for k, v in (signals or {}).items()}


def dominates(a: dict, b: dict) -> bool:
    """True if source-a's richness signals are >= b on every shared axis and > on at least one."""
    a, b = _vec(a), _vec(b)
    keys = set(a) | set(b)
    ge_all = all(a.get(k, 0) >= b.get(k, 0) for k in keys)
    gt_any = any(a.get(k, 0) > b.get(k, 0) for k in keys)
    return ge_all and gt_any


def choose_authoritative_source(sources: list[dict]) -> dict:
    """sources: [{"label": str, "signals": {name: count}}, ...] for the SAME strain.

    Returns {"verdict": "SUPERSEDE"|"CONSULT"|"NOOP", "keep": label|None, "drop": [labels], "reason": str}.
    SUPERSEDE -> one source dominates; keep it, drop the rest (after schema-normalizing the survivor).
    CONSULT   -> no single source dominates (each richer on some axis); surface the fork to the user.
    NOOP      -> 0 or 1 source; nothing to de-dup.
    """
    srcs = [{"label": s.get("label", f"src{i}"), "signals": _vec(s.get("signals"))}
            for i, s in enumerate(sources or [])]
    if len(srcs) <= 1:
        return {"verdict": "NOOP", "keep": srcs[0]["label"] if srcs else None, "drop": [], "reason": "nothing to de-dup"}

    # a source is authoritative iff it dominates every other source
    for cand in srcs:
        others = [s for s in srcs if s is not cand]
        if all(dominates(cand["signals"], o["signals"]) for o in others):
            drop = [o["label"] for o in others]
            return {"verdict": "SUPERSEDE", "keep": cand["label"], "drop": drop,
                    "reason": f"{cand['label']} richness dominates {', '.join(drop)} on all axes — "
                              f"superseding (normalize its schema; do not drop it for tidiness)"}

    # no dominator: at least two sources are each richer on some axis -> evidence loss either way
    labels = ", ".join(s["label"] for s in srcs)
    return {"verdict": "CONSULT", "keep": None, "drop": [],
            "reason": f"no source dominates ({labels}); each carries evidence the others lack — "
                      f"consult the user before superseding (a merge-union may be required, not a pick)"}


# ── T-3: summary/footer-row sentinel ─────────────────────────────────────────────────────────────────
# A merged Strain_Master carries a footer row whose strain value is "TOTAL" and which has no cohort tag.
# A cohort-keyed parser (groupby(cohort)) counts it as a phantom strain. The merge layer should tag such
# rows with this reserved sentinel (or emit them outside the data range); every cohort-keyed consumer should
# skip rows where is_summary_row(value) is True. Defined here so the merge (out of tree) and in-tree readers
# share one convention.
SUMMARY_ROW_SENTINEL = "__SUMMARY__"
_SUMMARY_TOKENS = {"__SUMMARY__", "TOTAL", "TOTALS", "GRAND TOTAL", "SUM", "ALL", "ALL STRAINS"}


def is_summary_row(value) -> bool:
    """True if a Strain_Master cell value is a footer/summary marker, not a real strain id."""
    if value is None:
        return False
    return str(value).strip().upper() in _SUMMARY_TOKENS
