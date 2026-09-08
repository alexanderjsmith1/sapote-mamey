"""comparative_pairs.py — E2_Comparative_Pairs populator (v9.7.88, 9.7.88-J).

THE GAP THIS FILLS
------------------
E2_Comparative_Pairs was declared in the master schema and referenced by the schema check, but
no function ever populated it — there was no between-strain pairwise BGC-similarity layer at all.
Concrete need (AS-cohort session): two BGCs in different strains sharing a
PepM+Ppd+aminotransferase+PLP+adenylation cassette look homologous; E2 is where that comparison
belongs.

WHAT IT COMPUTES (and what it does NOT)
---------------------------------------
This is a deterministic SIMILARITY layer, not a sequence-identity layer. It compares BGC pairs
across strains on signals already banked: shared product/subprogram classes, shared sec_met
domain signatures (from the v9.7.88 gene context when available), and KCB-anchor overlap. Per the
standing rules, KCB is similarity not identity, and no product/identity claim is made.

The schema columns `mean_pct_id_core` / `mean_pct_id_all` / `a_domain_match` are reserved for a
future alignment-backed layer. Until that exists they are filled as "not_computed" (NOT blank and
NOT zero) so a consumer can distinguish "no alignment run" from "no similarity" (worst-list #30).
When gene context is present we DO populate `a_domain_match` with a deterministic shared-A-domain
count (adenylation/AMP-binding domains common to both BGCs) — a real signal, clearly labelled as
domain-presence overlap, not percent identity.

Claim-safety: every interpretation string is capacity/similarity-framed; physical homology
requires sequence alignment and is never asserted here.
"""
from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path
from typing import Any


# A-domain / adenylation-family domain names worth counting as a shared-A-domain signal
_ADENYLATION = {"AMP-binding", "AMP-binding_C", "A_domain", "Condensation", "ACP", "PCP",
                "PP-binding", "Thioesterase"}


def _products_set(s: str | list) -> set[str]:
    if isinstance(s, list):
        items = s
    else:
        items = str(s or "").replace(",", ";").split(";")
    return {p.strip().lower() for p in items if p.strip()}


def _domain_signature(cds_rows: list[dict]) -> set[str]:
    sig = set()
    for r in cds_rows or []:
        for d in r.get("sec_met_domains", []) or []:
            if d:
                sig.add(d)
    return sig


def _shared_a_domains(sig_a: set[str], sig_b: set[str]) -> int:
    return len((sig_a & sig_b) & _ADENYLATION)


def _interpretation(shared_prod: set[str], shared_dom: int, kcb_overlap: bool) -> str:
    bits = []
    if shared_prod:
        bits.append(f"shared product class(es): {', '.join(sorted(shared_prod))}")
    if shared_dom:
        bits.append(f"{shared_dom} shared adenylation/PKS-PCP domain(s)")
    if kcb_overlap:
        bits.append("overlapping KCB anchor (similarity, not identity)")
    if not bits:
        return "no shared class/domain/KCB signal between this pair (similarity layer)"
    return ("Capacity-level similarity signal — " + "; ".join(bits)
            + ". Physical homology requires sequence alignment; not asserted.")


def build_comparative_pairs(bank: dict[str, Any],
                            gene_context_by_strain: dict[str, dict] | None = None,
                            min_signal: int = 1) -> list[dict]:
    """Build E2 rows from a cohort bank.

    bank: {"strains": {sid: meta}, "bgcs": [ {sid, bgc_id, products, kcb_top, length_kb, contig...} ]}
    gene_context_by_strain: optional {sid: {bgc_id: [cds_row,...]}} (from load_gene_context per strain)
    min_signal: minimum number of similarity signals (shared product OR shared A-domain OR KCB
                overlap) required to emit a pair — keeps the sheet to genuine candidates.

    Returns a list of E2-schema dicts. Pairs are cross-strain ONLY (same-strain pairs are the
    RG-GMCI within-strain layer's job, not this one). Deterministic ordering by pair_id.
    """
    gene_context_by_strain = gene_context_by_strain or {}
    bgcs = bank.get("bgcs", []) or []
    # v9.7.409 (DEEP_AUDIT2_resource_dos #3): bound the cross-strain all-vs-all pair scan to a sane
    # BGC count so a degenerate/crafted bank cannot blow up the O(n^2) loop.
    from .pair_scan_caps import cap_pair_scan_items
    bgcs = cap_pair_scan_items(bgcs, label="comparative_pairs")
    # group by strain; only compare across distinct strains
    rows: list[dict] = []
    for a, b in combinations(bgcs, 2):
        sa, sb = a.get("sid"), b.get("sid")
        if not sa or not sb or sa == sb:
            continue
        prod_a, prod_b = _products_set(a.get("products")), _products_set(b.get("products"))
        shared_prod = prod_a & prod_b
        if not shared_prod:
            continue  # no shared class — cheap reject before the more expensive domain work

        # sec_met domain signatures from gene context (when available)
        gc_a = gene_context_by_strain.get(sa, {}).get(a.get("bgc_id"), [])
        gc_b = gene_context_by_strain.get(sb, {}).get(b.get("bgc_id"), [])
        sig_a, sig_b = _domain_signature(gc_a), _domain_signature(gc_b)
        shared_dom = _shared_a_domains(sig_a, sig_b)
        shared_dom_all = len(sig_a & sig_b)

        # KCB anchor overlap (similarity signal only)
        kcb_a = str(a.get("kcb_top") or "").strip().lower()
        kcb_b = str(b.get("kcb_top") or "").strip().lower()
        kcb_overlap = bool(kcb_a and kcb_a == kcb_b)

        signal_count = (1 if shared_prod else 0) + (1 if shared_dom else 0) + (1 if kcb_overlap else 0)
        if signal_count < min_signal:
            continue

        # AUDIT_374: was `bool(gc_a or gc_b)` -- when only ONE side's gene context is
        # available (a real, common cohort scenario: not every strain has run through the
        # gene-context-generation step), the domain SET intersection with an empty other-side
        # signature is trivially empty, so `shared_dom` reads as a confirmed "0 shared domains"
        # and `diverged_genes` reads as "every one of this side's domains is divergent" -- both
        # false positives caused purely by missing data on the other strain, not real divergence.
        # This exact confusion (missing evidence read as a negative result) is the precise thing
        # this module's own "not_computed" design (see the module docstring / mean_pct_id_* below)
        # exists to prevent. Require BOTH sides' context before reporting a real domain-overlap
        # number; otherwise honestly report "not_computed" like the other reserved columns.
        have_gc = bool(gc_a) and bool(gc_b)
        pair_id = f"{sa}:{a.get('bgc_id')}__{sb}:{b.get('bgc_id')}"
        rows.append({
            "pair_id": pair_id,
            "strain_a": sa, "bgc_a": a.get("bgc_id"),
            "strain_b": sb, "bgc_b": b.get("bgc_id"),
            "length_a_kb": a.get("length_kb", ""), "length_b_kb": b.get("length_kb", ""),
            "products": "; ".join(sorted(shared_prod)),
            "subprogram_match": "; ".join(sorted(shared_prod)),
            # reserved for an alignment-backed layer — explicit "not_computed" so a consumer can
            # tell "no alignment run" from "no similarity"
            "mean_pct_id_core": "not_computed",
            "mean_pct_id_all": "not_computed",
            # real signal when gene context present: count of shared adenylation/PKS-carrier domains
            "a_domain_match": (str(shared_dom) if have_gc else "not_computed"),
            "diverged_genes": (str(max(len(sig_a), len(sig_b)) - shared_dom_all) if have_gc else "not_computed"),
            "interpretation": _interpretation(shared_prod, shared_dom, kcb_overlap),
        })

    rows.sort(key=lambda r: r["pair_id"])
    return rows


def load_bank(bank_path: str | Path) -> dict[str, Any]:
    """Read a cohort/single-strain bgc_data.json bank. Empty shell if absent/malformed."""
    p = Path(bank_path)
    if not p.exists():
        return {"strains": {}, "bgcs": []}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(d, dict) and "bgcs" in d:
            return d
    except Exception:
        pass
    return {"strains": {}, "bgcs": []}
