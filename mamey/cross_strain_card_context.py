"""cross_strain_card_context.py — Gap 2: per-card cross-strain context for Mode B cards.

THE GAP THIS FILLS
------------------
Mode B cards are generated one strain at a time and are cross-strain-blind. The engine's
`master_workbook.cross_strain_context()` returns habitat-peer counts but never reaches the card,
and it does not answer the reviewer's first question about any BGC: "is this cluster special to
this strain, or does every strain in the cohort carry this class?"

This module reads the COHORT MASTER (Cross_Strain_Class_Prevalence + B2_Product_Class_Matrix) and
emits, per BGC, a §X Cross-strain context block classifying each of the BGC's product classes as:
  - COHORT-UBIQUITOUS  (band CORE + informative_for_comparison == NO) -> down-weight; not a signal
  - COHORT-UNIQUE      (n_strains == 1)                                -> differentiating lead
  - COHORT-SHARED      (everything between)                            -> host-distribution context

WHAT IT IS / IS NOT
-------------------
- Capacity-level only. A class match means "carries biosynthetic capacity for class X", never
  product identity (KCB = similarity, not identity).
- Reads the engine's OWN prevalence classification (band + informative flag) — it does not
  re-derive ubiquity, so it stays consistent with the cohort heatmaps and cross_strain_threads.
- Deterministic; no scoring change; no LLM.
- PRIVATE by construction (cohort spans AS strains). In a public render, strain IDs redact to AS-XXX.

DEPENDENCY: requires a populated master with Cross_Strain_Class_Prevalence (recomputed for the
current cohort — see the denominator invariant). On a stale/empty prevalence sheet, returns "".
"""
from __future__ import annotations
from openpyxl import load_workbook
from pathlib import Path


# Classes that are biosynthetically uninformative as differentiators even when not flagged.
# Mirrors the standing permanent-exclusion / ubiquitous set used by cross_strain_threads.
_UBIQUITOUS_FALLBACK = {
    "other", "saccharide", "fatty_acid", "terpene", "NI-siderophore",
    "NRP-metallophore", "ectoine", "melanin", "NAPAA", "terpene-precursor",
}


def load_prevalence(master_path: str | Path) -> dict:
    """Read Cross_Strain_Class_Prevalence -> {class: {n_strains, pct, band, informative}}.

    Returns {} if the sheet is missing or empty (stale/unscored master) so the caller can
    skip the §X block rather than emit wrong context.
    """
    master_path = Path(master_path)
    if not master_path.exists():
        return {}
    from .xlsx_determinism import guard_workbook_size as _guard_xlsx  # v9.7.410
    _guard_xlsx(master_path)
    wb = load_workbook(master_path, read_only=True, data_only=True)
    if "Cross_Strain_Class_Prevalence" not in wb.sheetnames:
        # F4-class fix: the dedicated sheet is only added post-hoc; derive from
        # B2_Product_Class_Matrix (present in every base master) so cross-strain card
        # context is populated on a bare gold master instead of silently skipped.
        if "B2_Product_Class_Matrix" not in wb.sheetnames:
            return {}
        ws = wb["B2_Product_Class_Matrix"]
        b2rows = list(ws.iter_rows(min_row=1, values_only=True))
        if len(b2rows) < 2:
            return {}
        hdr = [str(h) for h in b2rows[0]]
        class_cols = [(i, c) for i, c in enumerate(hdr)
                      if c not in ("strain", "label_provenance", "counts_reliability")]
        provenance_i = hdr.index("label_provenance") if "label_provenance" in hdr else None
        strain_rows = [r for r in b2rows[1:] if r and r[0] and
                       (provenance_i is None or str(r[provenance_i]).upper() == "GENE_BACKED")]
        N = len(strain_rows)
        counts = {c: 0 for _, c in class_cols}
        for r in strain_rows:
            for i, c in class_cols:
                v = r[i] if i < len(r) else 0
                try:
                    if v is not None and float(v) > 0:
                        counts[c] += 1
                except (TypeError, ValueError):
                    continue
        out = {}
        for cls, n in counts.items():
            if n == 0:
                continue
            frac = n / N if N else 0
            band = ("ubiquitous" if N and n == N else "common" if frac >= 0.5
                    else "occasional" if frac >= 0.2 else "rare")
            out[cls] = {"n_strains": n, "pct": round(100 * frac, 1),
                        "band": band, "informative": 1 <= n < N}
        return out
    ws = wb["Cross_Strain_Class_Prevalence"]
    rows = list(ws.iter_rows(min_row=1, values_only=True))
    if len(rows) < 2:
        return {}
    hdr = [str(h) for h in rows[0]]
    idx = {h: i for i, h in enumerate(hdr)}
    out = {}
    for r in rows[1:]:
        if not r or not r[idx.get("product_class", 0)]:
            continue
        cls = str(r[idx["product_class"]])
        try:
            n = int(r[idx["n_strains"]])
        except (TypeError, ValueError, KeyError):
            continue
        informative = str(r[idx.get("informative_for_comparison", -1)]).lower()
        out[cls] = {
            "n_strains": n,
            "pct": r[idx.get("pct_strains", 0)] if "pct_strains" in idx else None,
            "band": str(r[idx.get("band", -1)]) if "band" in idx else "",
            "informative": informative.startswith("yes"),
        }
    return out


def registry_size(master_path: str | Path) -> int:
    """Canonical N = number of strains in A2_Strain_Registry (the invariant denominator).

    AUDIT_374: missing-file guard, matching load_prevalence() immediately above (and
    called right alongside it in cohort_cards.py::run_cohort_cards -- prevalence, then N). A
    master workbook path that does not exist (no cohort master built yet, or a stale/typo'd
    --master path) previously crashed this function with a raw FileNotFoundError, even though
    the module's own documented contract is that a stale/empty master degrades gracefully ("the
    §X blocks are skipped ... the cards are never wrong, just un-annotated") -- load_prevalence()
    already honours that contract for a missing file; this function did not.
    """
    master_path = Path(master_path)
    if not master_path.exists():
        return 0
    wb = load_workbook(master_path, read_only=True, data_only=True)
    if "A2_Strain_Registry" not in wb.sheetnames:
        return 0
    ws = wb["A2_Strain_Registry"]
    return sum(1 for r in ws.iter_rows(min_row=2, values_only=True) if r and r[0])


def _prevalence_lookup(cls: str, prevalence: dict):
    """Case-normalised prevalence lookup, shared by classify_class() and card_context_block()
    so the two never disagree on which prevalence entry a class name resolves to.

    AUDIT_374: card_context_block()'s SHARED branch used to re-look-up `prevalence.get(cls)`
    directly (case-sensitive) after classify_class() had already resolved the SAME class via this
    case-insensitive fallback -- so a class whose casing didn't exactly match the prevalence
    sheet's key (the exact scenario the v9.7.116 comment below says happens) classified correctly
    as SHARED, but then rendered a garbled "cohort-shared by ?/N strains ()" line: p came back {},
    n_strains showed as a literal "?", and the shared-fraction/band both silently dropped.
    """
    p = prevalence.get(cls)
    if p is None:
        for k, v in prevalence.items():
            if k.lower() == cls.lower():
                p = v
                break
    return p


def classify_class(cls: str, prevalence: dict, N: int) -> str:
    """Return UBIQUITOUS | UNIQUE | SHARED | UNKNOWN for one product class.

    v9.7.116: lookups are case-normalised defensively. antiSMASH product classes are consistently
    lower-cased in both the prevalence sheet and BGC products, but a stray-case class name must not
    silently fall through to UNKNOWN (which would drop a genuine ubiquitous/unique signal).
    """
    if cls in _UBIQUITOUS_FALLBACK or cls.lower() in _UBIQUITOUS_FALLBACK:
        return "UBIQUITOUS"
    p = _prevalence_lookup(cls, prevalence)
    if p is None:
        return "UNKNOWN"
    if p["n_strains"] <= 1:
        return "UNIQUE"
    # engine flagged it uninformative (universal) -> ubiquitous
    if N and p["n_strains"] >= N and not p["informative"]:
        return "UBIQUITOUS"
    if not p["informative"]:
        return "UBIQUITOUS"
    return "SHARED"


def card_context_block(strain_id: str, bgc_id: str, products, prevalence: dict,
                       N: int, strain_of_unique: dict | None = None) -> str:
    """Build the §X Cross-strain context block for one BGC. Returns "" if nothing informative."""
    if isinstance(products, str):
        products = [products]
    informative_lines = []
    ubi_present = []
    for cls in products:
        verdict = classify_class(cls, prevalence, N)
        if verdict == "UBIQUITOUS":
            ubi_present.append(cls)
            continue
        if verdict == "UNIQUE":
            informative_lines.append(
                f"{cls}: COHORT-UNIQUE to {strain_id} (1/{N} strains) — differentiating "
                f"biosynthetic capacity; no other cohort strain carries this class. "
                f"Priority for characterisation."
            )
        elif verdict == "SHARED":
            p = _prevalence_lookup(cls, prevalence) or {}
            n = p.get("n_strains", "?")
            if N and isinstance(n, int) and n >= N:
                informative_lines.append(
                    f"{cls}: present in all {N} cohort strains ({p.get('band','')}) but flagged "
                    f"comparison-informative — a shared backbone class, not strain-differentiating."
                )
            else:
                frac = (n / N) if (N and isinstance(n, int)) else 0
                bias = "narrowly shared" if frac <= 0.4 else "broadly shared"
                informative_lines.append(
                    f"{cls}: cohort-shared by {n}/{N} strains ({p.get('band','')}, {bias}). "
                    f"Compare against the other carriers for a conserved-cluster vs convergence call."
                )
        # UNKNOWN: silent (class not in prevalence sheet)
    if not informative_lines and not ubi_present:
        return ""
    lines = ["§X. Cross-strain context"]
    lines.extend(informative_lines)
    if ubi_present:
        lines.append(
            f"(Cohort-ubiquitous classes present — {', '.join(ubi_present[:4])} — "
            f"excluded from differentiation per standing rule.)"
        )
    return "\n".join(lines)
