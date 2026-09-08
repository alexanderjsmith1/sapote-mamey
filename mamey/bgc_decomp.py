"""bgc_decomp.py — BGC two-model decomposition analysis (v9.7.131).

Fits a two-BGC model to each antiSMASH detection window: assigns each gene a
broad biosynthetic class from its domain annotation alone (no KCB), finds the
best binary partition of core-engine genes into two spatially separated groups,
and scores how well the two-BGC model fits versus the one-BGC null.

This is a CAPACITY-LEVEL signal. It does not prove that two pathways exist. It
reports how consistent the gene architecture is with a two-pathway hypothesis,
so the analyst can decide how to frame the Mode B card.

Mirrored after RG-GMCI: ranked output, confidence tiers, explicit claim-safety
footer. Read TWO_MODEL_STRONG the same way you read HIGH_RG_GMCI_RESCUE:
it changes how you write the card, not what product you claim.

Confidence tiers
----------------
TWO_MODEL_STRONG      coherence >= 0.75, gap >= 15 kb, >= 2 anchor genes per side.
                      Describe both sub-BGCs in Mode B §1 and §3.
TWO_MODEL_CANDIDATE   coherence >= 0.50, gap >= 8 kb, >= 1 anchor gene per side.
                      Note architecture in §1.
ONE_MODEL_CONSISTENT  best partition below thresholds, or same class both sides,
                      or PKS+NRPS hybrid (one pathway by definition).

Output columns (one row per BGC, all BGCs)
------------------------------------------
bgc_id, contig, bgc_len_bp, antismash_products,
n_genes, n_anchor_genes, two_model_confidence,
group_a_class, group_a_anchor_genes, group_a_start_bp, group_a_end_bp,
group_b_class, group_b_anchor_genes, group_b_start_bp, group_b_end_bp,
gap_bp, gap_pct_window, class_coherence_score, null_reason,
kcb_anchor, kcb_support_group_a_pct, kcb_support_group_b_pct,
kcb_architectural_disconnect, interpretation_guard,
strain, node_id, antismash_region
"""
from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any


TWO_MODEL_DECOMP_HEADERS = (
    "bgc_id", "contig", "bgc_len_bp", "antismash_products",
    "n_genes", "n_anchor_genes", "two_model_confidence",
    "group_a_class", "group_a_anchor_genes", "group_a_start_bp", "group_a_end_bp",
    "group_b_class", "group_b_anchor_genes", "group_b_start_bp", "group_b_end_bp",
    "gap_bp", "gap_pct_window", "class_coherence_score", "null_reason",
    "kcb_anchor", "kcb_support_group_a_pct", "kcb_support_group_b_pct",
    "kcb_architectural_disconnect", "interpretation_guard",
    "strain", "node_id", "antismash_region",
)

# ---------------------------------------------------------------------------
# Gene classification — broad biosynthetic classes from sec_met_domains only
# ---------------------------------------------------------------------------
#
# Design notes (v9.7.130 — domain classifier expansion):
#
#   INCLUSION RULE: a domain enters _CLASS_DOMAINS only if it is the PRIMARY
#   CATALYTIC ENGINE of a distinct biosynthetic pathway AND is unambiguous
#   within a BGC context (antiSMASH already provides the BGC filter).
#   Support/tailoring domains that always co-occur with a primary engine are
#   added for completeness but are not sole determinants.
#
#   PKS_KR / PKSI-KR_m1: IN PKS. Catalytic PKS module domains, not tailoring.
#   PKS_ER / PKSI-ER_m*: IN PKS. Enoylreductase within PKS module assembly line.
#   ECH / ECH_1: IN PKS. Enoyl-CoA hydratase — PKS beta-processing domain.
#     Risk: also in fatty acid metabolism, but antiSMASH BGC context guards this.
#   Polyketide_cyc / cyc2: IN PKS. T2PKS aromatase/cyclase. Uniquely PKS.
#
#   Cy4: IN NRPS. Heterocyclisation domain producing thiazole/oxazole rings.
#     Found in NRPS pathways. Distinct from Condensation but functionally
#     equivalent as a route-defining domain. Validated: BGC055 ctg49_241.
#   MbtH: IN NRPS. MbtH-like chaperone; always co-occurs with AMP-binding.
#     Adding for completeness; will not change anchor assignments.
#   NRPS-te1: IN NRPS. NRPS-specific thioesterase. NOT bare Thioesterase
#     (which appears in PKS too). The 'NRPS-' prefix is the discriminant.
#
#   Trp_halogenase: NOT in RiPP (tailoring, not core engine). Modifies Trp
#     in both NRPS and RiPP contexts. Keeping as tailoring — see v9.7.129 note.
#
#   NEW CLASS lasso: Stand_Alone_Lasso_RRE is definitive; Transglut_core3
#     is the lasso peptidase B1 catalytic domain. NOT added: PqqD (appears in
#     coenzyme PQQ primary metabolism too), Asn_synthase (widespread primary
#     metabolite enzyme — the lasso cyclase IS an Asn_synthase but the domain
#     alone is ambiguous). Stand_Alone_Lasso_RRE alone is sufficient anchor.
#     Validated: BGC055 Sub-BGC B (ctg49_221 Stand_Alone_Lasso_RRE).
#
#   NEW CLASS thioamide: TfuA is the thioamide-forming enzyme (unique to
#     thioamide-RiPP / thioamitide pathway). TIGR03605/03882/03889/03888 are
#     thioamitide-specific TIGRFAMs. Thiopeptide_F_RRE and
#     Heterocycloanthracin_C_RRE are thioamitide/thiopeptide RREs.
#     Validated: BGC055 Sub-BGC A (ctg49_198 TfuA, ctg49_199/202 YcaO,
#     ctg49_201 Thiopeptide_F_RRE + Heterocycloanthracin_C_RRE).
#
#   SPASM / TIGR03975 / TIGR03988 / TIGR03962: IN RiPP. Radical SAM SPASM
#     domain and cognate TIGRFAMs mark ranthipeptide/sactipeptide pathways.
#     NOT adding Radical_SAM alone (137 unknown genes; appears in primary metab,
#     terpene tailoring, etc. — too promiscuous without SPASM co-occurrence).
#
#   NEW CLASS phosphonate: PEP_mutase (phosphoenolpyruvate mutase) is the
#     initiating enzyme of phosphonate biosynthesis. Unique in BGC context.
#
#   terpene additions: polyprenyl_synt (polyprenyl synthase, IPP chain
#     elongation), Terpene_syn_C_2 (C-terminal variant of terpene synthase),
#     SQS_PSY (squalene/phytoene synthase family — phytoene_synt already
#     present; SQS_PSY is the Pfam equivalent for sesquiterpene/diterpene).
#
#   PKS+NRPS excluded from two-model (canonical single hybrid pathway).
#   All other class pairs are legitimate two-model signals — do NOT expand
#   _HYBRID_PAIRS: lasso+NRPS, thioamide+NRPS, etc. are exactly the splits
#   the detector should fire on (as demonstrated by BGC055).
#
#   Evidence base: 28 SID sealed packages, 1,756 BGCs, 3,894 distinct domains.
#   BGC055 (SID-XXX) three-sub-BGC dissection, June 2026.

_CLASS_DOMAINS: dict[str, set[str]] = {
    "PKS": {
        # Core ketosynthase / starter / extension module domains
        "PKS_KS", "ketoacyl-synt", "mod_KS", "PKS_AT", "hglE", "t2pks",
        "Ketoacyl-synt_C", "PKSI-KS_m5",
        # Reductive-loop domains within PKS modules (v9.7.129)
        "PKS_KR", "PKSI-KR_m1",
        # v9.7.130 additions — PKS module completion domains
        "PKS_ER",                       # enoylreductase (169 unknowns corrected)
        "Polyketide_cyc", "Polyketide_cyc2",  # T2PKS aromatase/cyclase (176 unknowns)
        "ECH", "ECH_1",                 # enoyl-CoA hydratase, PKS beta-processing
    },
    "NRPS": {
        # Core condensation / adenylation domains
        "Condensation", "AMP-binding", "A-OX", "AMP-binding_C",
        "NRPS-A_a3", "NRPS-A_a6",
        # v9.7.130 additions
        "Cy4",       # heterocyclisation domain (azole-forming NRPS); validated BGC055
        "MbtH",      # MbtH-like chaperone; always co-occurs with AMP-binding
        "NRPS-te1",  # NRPS-specific thioesterase (NOT bare Thioesterase)
    },
    "RiPP": {
        # Lanthipeptide core enzymes
        "YcaO", "Lant_dehydr", "LANC_like", "Lant_dehydr_C",
        # v9.7.130 additions — radical SAM RiPP (ranthipeptide/sactipeptide)
        # SPASM is the discriminating domain; Radical_SAM alone is NOT added (too promiscuous)
        "SPASM",       # radical SAM SPASM domain — uniquely marks radical SAM RiPPs
        "TIGR03975",   # sactipeptide radical SAM enzyme
        "TIGR03988",   # ranthipeptide/sactipeptide
        "TIGR03962",   # ranthipeptide
    },
    "terpene": {
        "Terpene_synth", "Terpene_synth_C", "SQHop_cyclase", "phytoene_synt",
        "Lycopene_cycl",
        # v9.7.130 additions
        "polyprenyl_synt",  # polyprenyl synthase, IPP chain elongation (152 unknowns)
        "Terpene_syn_C_2",  # terpene synthase C-terminal variant (89 unknowns)
        "SQS_PSY",          # squalene/phytoene synthase Pfam (80 unknowns)
    },
    # NEW v9.7.130 — lassopeptide
    # Anchor: Stand_Alone_Lasso_RRE (definitive lasso recognition element).
    # NOT added: PqqD (primary metab ambiguity), Asn_synthase (too promiscuous).
    "lasso": {
        "Stand_Alone_Lasso_RRE",  # definitive lasso RRE; validated BGC055 Sub-BGC B
        "Lasso_Fused_RRE",        # fused variant
        "Transglut_core3",        # lasso peptidase B1 catalytic domain
        "Transglut_core",         # variant
    },
    # NEW v9.7.130 — thioamide-RiPP / thioamitide
    # TfuA is the route-defining thioamide-forming enzyme.
    # TIGRFAMs 03605/03882/03889/03888/03883/03886 are thioamitide-specific.
    # RREs Thiopeptide_F_RRE and Heterocycloanthracin_C_RRE confirmed in BGC055.
    "thioamide": {
        "TfuA",                          # thioamide-forming enzyme; validated BGC055
        "TIGR03605",                     # thioamitide biosynthesis (16 unknowns)
        "TIGR03882",                     # thioamitide TIGRFAM (44 total, 2 unknown)
        "TIGR03889",                     # thioamitide (2 unknown)
        "TIGR03888",                     # thioamitide (2 unknown)
        "TIGR03883",                     # thioamitide (1 unknown)
        "TIGR03886",                     # thioamitide (1 unknown)
        "Thiopeptide_F_RRE",             # RRE for thioamitide precursor; validated BGC055
        "Heterocycloanthracin_C_RRE",    # RRE for heterocycloanthracin class; validated BGC055
    },
    # NEW v9.7.130 — phosphonate
    # PEP_mutase initiates phosphonate biosynthesis. Unique in BGC context.
    "phosphonate": {
        "PEP_mutase",        # phosphoenolpyruvate mutase — initiating step
    },
}

_TAILORING_PREFIXES = (
    "p450", "Methyltransf_", "FAD_binding_", "Acyl-CoA_dh_", "UDPGT",
    "Aminotran_", "adh_short", "Trp_halogenase",   # halogenase = tailoring, not core engine
    "adh_short_C",
    "Oxidored_", "Epimerase", "Thioredox", "MFS_",
    "ABC_tran", "PP-binding", "Abhydrolase_", "Flavin_Reduct",
)

_REGULATOR_PREFIXES = (
    "TetR_", "HTH_", "GntR", "LuxR", "LysR_", "MarR", "Sigma70_",
    "Trans_reg_", "Response_reg", "HATPase_", "HisKA", "BTAD",
    "GerE", "HAMP", "DJ-1",
)

# Class pairs that form a standard single pathway — do NOT flag as two BGCs.
# PKS<->NRPS is the canonical hybrid (trans-AT PKS-NRPS, PKS-NRPS, etc.).
# RiPP and terpene do not co-assemble with non-ribosomal/non-cyclase machinery
# into one product, so those pairings are genuine two-pathway signals.
_HYBRID_PAIRS: set[frozenset] = {frozenset({"PKS", "NRPS"})}

# v9.7.131 follow-up: lasso, thioamide, and phosphonate are route-defining classes and
# therefore must be anchor classes for two-model fitting. RiPP sub-classes are
# scored hierarchically as one RiPP family for binary coherence, but exact
# labels are still retained in group_a_class/group_b_class and anchor-gene lists.
_CORE_CLASSES = {"PKS", "NRPS", "RiPP", "terpene", "lasso", "thioamide", "phosphonate"}
_RIPP_FAMILY_CLASSES = {"RiPP", "lasso", "thioamide"}
_CLASS_FAMILY = {cls: "RiPP-family" for cls in _RIPP_FAMILY_CLASSES} | {
    "PKS": "PKS",
    "NRPS": "NRPS",
    "terpene": "terpene",
    "phosphonate": "phosphonate",
}
_CLASS_TIE_PRIORITY = ("thioamide", "lasso", "RiPP", "PKS", "NRPS", "terpene", "phosphonate")
_FAMILY_TIE_PRIORITY = ("RiPP-family", "PKS", "NRPS", "terpene", "phosphonate")

# Calibrated thresholds (K_albida + 6-strain validation).
COHERENCE_STRONG = 0.75
COHERENCE_CANDIDATE = 0.50
GAP_STRONG_BP = 15_000
GAP_CANDIDATE_BP = 8_000
MIN_ANCHORS_STRONG = 2     # per side
MIN_ANCHORS_CANDIDATE = 1  # per side


def _classify_gene(domains_str: str) -> str:
    """Assign one broad class to a gene from its sec_met_domains string.

    Returns: PKS | NRPS | RiPP | terpene | lasso | thioamide | phosphonate | tailoring | regulator | unknown.
    Uses domain annotation only — no KCB, no product label, no positional context.
    """
    if not domains_str or str(domains_str).strip() in ("—", "None", ""):
        return "unknown"
    doms = [
        d.strip().split(" ")[0]
        for d in re.split(r"[;,]+", str(domains_str))
        if d.strip()
    ]

    # Core engine classes — checked first, highest priority
    for cls, dset in _CLASS_DOMAINS.items():
        if any(d in dset for d in doms):
            return cls

    # Chal_sti_synt* family: T3PKS chalcone/stilbene synthase.
    # antiSMASH emits Chal_sti_synt_C / Chal_sti_synt_N — prefix match catches all variants.
    if any(d.startswith("Chal_sti_synt") for d in doms):
        return "PKS"

    # PKSI-ER_m* family: iterative PKS enoylreductase module variants.
    # antiSMASH emits PKSI-ER_m1, _m2, _m4, _m5, _m7, _m9 etc.
    # ECH / ECH_1 are exact-matched above; PKSI-ER_m* caught here by prefix.
    if any(d.startswith("PKSI-ER_m") for d in doms):
        return "PKS"

    # PKSI-KR_m* family: iterative PKS ketoreductase module variants (mirrors PKSI-ER_m*
    # immediately above). antiSMASH emits PKSI-KR_m1, _m2, _m4, _m5, _m7, _m9 etc., the same
    # per-module reductive-loop naming convention as the ER family. Only "PKSI-KR_m1" was
    # exact-matched in _CLASS_DOMAINS above (design note: "PKS_KR / PKSI-KR_m1: IN PKS.
    # Catalytic PKS module domains, not tailoring") -- m2/m4/m5/m7/m9 fell through to the
    # _TAILORING_PREFIXES "PKSI-KR_m" prefix entry and were misclassified as tailoring,
    # contradicting that same design note. Caught here by prefix, same as PKSI-ER_m*.
    if any(d.startswith("PKSI-KR_m") for d in doms):
        return "PKS"

    # Tailoring and regulatory — checked by prefix (order matters: tailoring before regulator)
    for d in doms:
        if any(d.startswith(p) for p in _TAILORING_PREFIXES):
            return "tailoring"
        if any(d.startswith(p) for p in _REGULATOR_PREFIXES):
            return "regulator"

    return "unknown"


# ---------------------------------------------------------------------------
# Two-model fitter
# ---------------------------------------------------------------------------

def _class_family(cls: str) -> str:
    """Return the broad scoring family for a class label."""
    return _CLASS_FAMILY.get(cls, cls)


def _dominant_label(values: list[str], priority: tuple[str, ...] = ()) -> str:
    """Return the most frequent label, resolving ties deterministically."""
    if not values:
        return ""
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    priority_index = {value: i for i, value in enumerate(priority)}
    return max(
        counts,
        key=lambda value: (
            counts[value],
            -priority_index.get(value, len(priority_index)),
            value,
        ),
    )


def _class_coherence(classes: list[str], *, family_aware: bool = False) -> float:
    """Fraction of the dominant class/family in a group. 1.0 = all one class/family.

    The binary fitter uses family_aware=True so RiPP, lasso,
    and thioamide anchors do not dilute confidence when they sit on the same
    side of a split. The default remains exact-class coherence for callers that
    need the old primitive.
    """
    if not classes:
        return 0.0
    labels = [_class_family(c) for c in classes] if family_aware else classes
    counts: dict[str, int] = {}
    for c in labels:
        counts[c] = counts.get(c, 0) + 1
    return max(counts.values()) / len(labels)


def _split_confidence(coherence: float, gap: int, n_a: int, n_b: int) -> tuple[int, str]:
    """Return (tier_rank, label) for a candidate split.

    The fitter selects by tier first, then by combined score. This prevents a
    biologically less useful, short-gap perfect-family split from displacing a
    threshold-qualified large-gap split in mixed RiPP-family/NRPS windows such
    as SID-XXX BGC055.
    """
    if (
        coherence >= COHERENCE_STRONG
        and gap >= GAP_STRONG_BP
        and n_a >= MIN_ANCHORS_STRONG
        and n_b >= MIN_ANCHORS_STRONG
    ):
        return 2, "TWO_MODEL_STRONG"
    if (
        coherence >= COHERENCE_CANDIDATE
        and gap >= GAP_CANDIDATE_BP
        and n_a >= MIN_ANCHORS_CANDIDATE
        and n_b >= MIN_ANCHORS_CANDIDATE
    ):
        return 1, "TWO_MODEL_CANDIDATE"
    return 0, "ONE_MODEL_CONSISTENT"


def _fit_two_model(genes: list[dict]) -> dict:
    """Find the best binary partition of anchor genes by class coherence + spatial gap.

    genes: list of dicts with keys: locus_tag, cds_start, cds_end, broad_class.
           Must be sorted by cds_start ascending.

    Returns a result dict with two_model_confidence and all group/gap/coherence fields.
    """
    anchors = [g for g in genes if g.get("broad_class") in _CORE_CLASSES]

    base = {
        "n_genes": len(genes),
        "n_anchor_genes": len(anchors),
        "two_model_confidence": "ONE_MODEL_CONSISTENT",
        "group_a_class": "", "group_a_anchor_genes": "",
        "group_a_start_bp": "", "group_a_end_bp": "",
        "group_b_class": "", "group_b_anchor_genes": "",
        "group_b_start_bp": "", "group_b_end_bp": "",
        "gap_bp": "", "gap_pct_window": "",
        "class_coherence_score": "",
        "null_reason": "fewer than 2 anchor genes",
    }

    if len(anchors) < 2:
        return base

    bgc_len = max(
        (genes[-1]["cds_end"] - genes[0]["cds_start"]) if genes else 1,
        1,
    )

    best: dict[str, Any] = {}
    best_score: tuple[int, int, float] = (-1, -10**12, -1.0)

    for split_idx in range(1, len(anchors)):
        ga = anchors[:split_idx]
        gb = anchors[split_idx:]

        classes_a = [g["broad_class"] for g in ga]
        classes_b = [g["broad_class"] for g in gb]
        dom_a = _dominant_label(classes_a, _CLASS_TIE_PRIORITY)
        dom_b = _dominant_label(classes_b, _CLASS_TIE_PRIORITY)
        fam_a = _dominant_label([_class_family(c) for c in classes_a], _FAMILY_TIE_PRIORITY)
        fam_b = _dominant_label([_class_family(c) for c in classes_b], _FAMILY_TIE_PRIORITY)

        # Skip same exact-dominant-class splits and known exact-class hybrid pairs.
        # RiPP-family subtypes remain exact labels for reporting and can still form
        # legitimate split signals against NRPS/PKS/terpene/phosphonate anchors.
        if dom_a == dom_b:
            continue
        if frozenset({dom_a, dom_b}) in _HYBRID_PAIRS:
            continue

        # Do not split through a dominant exact class block. This prevents a
        # short downstream NRPS tail from being separated from an upstream NRPS
        # anchor simply because the upstream side is mostly RiPP-family.
        if dom_a in classes_b or dom_b in classes_a:
            continue

        coh_a = _class_coherence(classes_a, family_aware=True)
        coh_b = _class_coherence(classes_b, family_aware=True)
        coherence = (coh_a + coh_b) / 2.0

        last_a_end = max(g["cds_end"] for g in ga)
        first_b_start = min(g["cds_start"] for g in gb)
        gap = first_b_start - last_a_end
        tier_rank, tier_label = _split_confidence(coherence, gap, len(ga), len(gb))

        # Combined score: coherence weighted more heavily than gap for ties.
        # Selection is tier-first, then gap-first, so a threshold-qualified
        # large-gap two-BGC boundary is not eclipsed by a short-gap split created
        # inside a mixed RiPP-family/NRPS block.
        combined = coherence * 0.7 + min(gap / 60_000, 1.0) * 0.3

        selection_key = (tier_rank, gap, combined)
        if selection_key > best_score:
            best_score = selection_key
            best = {
                "ga": ga, "gb": gb,
                "dom_a": dom_a, "dom_b": dom_b,
                "fam_a": fam_a, "fam_b": fam_b,
                "coherence": round(coherence, 3),
                "gap": gap,
                "n_a": len(ga), "n_b": len(gb),
                "tier_label": tier_label,
            }

    if not best:
        base["null_reason"] = "no cross-class split found (hybrid or single-class window)"
        return base

    gap = best["gap"]
    coh = best["coherence"]
    n_a = best["n_a"]
    n_b = best["n_b"]
    bgc_len_safe = max(bgc_len, 1)

    confidence = best.get("tier_label", "ONE_MODEL_CONSISTENT")
    null_reason = ""
    if confidence == "ONE_MODEL_CONSISTENT":
        reasons = []
        if coh < COHERENCE_CANDIDATE:
            reasons.append(f"coherence {coh} < {COHERENCE_CANDIDATE}")
        if gap < GAP_CANDIDATE_BP:
            reasons.append(f"gap {gap} bp < {GAP_CANDIDATE_BP} bp")
        if n_a < MIN_ANCHORS_CANDIDATE or n_b < MIN_ANCHORS_CANDIDATE:
            reasons.append(
                f"anchor count below candidate threshold (group_a={n_a}, group_b={n_b})"
            )
        null_reason = "; ".join(reasons) or "best cross-class split below confidence thresholds"

    ga_genes = best["ga"]
    gb_genes = best["gb"]

    return {
        "n_genes": len(genes),
        "n_anchor_genes": len(anchors),
        "two_model_confidence": confidence,
        "group_a_class": best["dom_a"],
        "group_a_anchor_genes": "; ".join(g["locus_tag"] for g in ga_genes),
        "group_a_start_bp": min(g["cds_start"] for g in ga_genes),
        "group_a_end_bp": max(g["cds_end"] for g in ga_genes),
        "group_b_class": best["dom_b"],
        "group_b_anchor_genes": "; ".join(g["locus_tag"] for g in gb_genes),
        "group_b_start_bp": min(g["cds_start"] for g in gb_genes),
        "group_b_end_bp": max(g["cds_end"] for g in gb_genes),
        "gap_bp": gap,
        "gap_pct_window": round(gap / bgc_len_safe * 100, 1),
        "class_coherence_score": coh,
        "null_reason": null_reason,
    }


# ---------------------------------------------------------------------------
# KCB architectural-disconnect check (requires extended parse_cb)
# ---------------------------------------------------------------------------

def _kcb_support_by_group(
    rank1_hits: list[dict],
    group_a_loci: set[str],
    group_b_loci: set[str],
) -> tuple[float, float, bool]:
    """Split rank-1 KCB blast score between group A and group B.

    rank1_hits: list of {query, subject, blast_score} dicts from parse_cb().
    Returns (pct_in_a, pct_in_b, architectural_disconnect).

    architectural_disconnect = True when one group drives >= 70% of the blast score
    AND the other group's anchor genes are entirely absent from the hit set.
    This means the KCB anchor is effectively anchored to one sub-BGC only.
    """
    if not rank1_hits:
        return 0.0, 0.0, False

    total = sum(h.get("blast_score", 0) for h in rank1_hits)
    if total == 0:
        return 0.0, 0.0, False

    score_a = sum(h.get("blast_score", 0) for h in rank1_hits if h["query"] in group_a_loci)
    score_b = sum(h.get("blast_score", 0) for h in rank1_hits if h["query"] in group_b_loci)

    pct_a = round(score_a / total * 100, 1)
    pct_b = round(score_b / total * 100, 1)

    hit_queries = {h["query"] for h in rank1_hits}
    a_has_hits = bool(group_a_loci & hit_queries)
    b_has_hits = bool(group_b_loci & hit_queries)
    disconnect = (pct_a >= 70 and not b_has_hits) or (pct_b >= 70 and not a_has_hits)

    return pct_a, pct_b, disconnect


# ---------------------------------------------------------------------------
# Package-level runner
# ---------------------------------------------------------------------------

_INTERP_GUARD = (
    "Gene-architecture two-model analysis. Class assignments use domain "
    "annotation only (no KCB, no product label). RiPP, lasso, and thioamide use "
    "family-level coherence for binary partition scoring while exact labels are reported. "
    "Confidence tiers reflect consistency "
    "of the gene architecture with a two-BGC hypothesis — they are NOT product claims "
    "and do NOT prove two pathways exist. "
    "TWO_MODEL_STRONG: describe both sub-BGCs in Mode B §1 and §3; note that the "
    "single antiSMASH product label covers only one of them. "
    "TWO_MODEL_CANDIDATE: note the architecture in §1. "
    "ONE_MODEL_CONSISTENT: single-pathway framing is supported by gene architecture; "
    "null_reason explains why the two-model was rejected. "
    "KCB_DISCONNECT (when present): the KCB anchor is driven by one sub-BGC's genes; "
    "the other sub-BGC is architecturally dark for KCB — treat the anchor as applying "
    "to one sub-BGC only."
)


def run_bgc_decomp(
    bgcs: list,
    gene_table_csv: "str | Path | None",
    kcb_dir: "str | Path | None" = None,
    *,
    strain: str | None = None,
) -> dict:
    """Run two-model decomposition on all BGCs.

    Parameters
    ----------
    bgcs : list of BGCRecord (or SimpleNamespace with bgc_id, contig, start, end,
           products, node_id fields)
    gene_table_csv : path to *_gene_by_gene_all_bgcs.csv produced by Mamey
    kcb_dir : optional path to knownclusterblast/ directory (for KCB disconnect check)
    strain : current run strain for native CSV emission. When supplied, each BGC
        is fail-closed validated and receives complete-locus anchor fields.

    Returns
    -------
    dict with keys: status, rows (list[dict]), strong_count, candidate_count, summary_line
    """
    # Load gene table
    genes_by_bgc: dict[str, list[dict]] = {}
    if gene_table_csv and Path(gene_table_csv).exists():
        with open(gene_table_csv, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                bid = (row.get("bgc_id") or "").strip()
                if not bid:
                    continue
                try:
                    cds_s = int(row.get("cds_start") or 0)
                    cds_e = int(row.get("cds_end") or cds_s)
                except (TypeError, ValueError):
                    continue
                genes_by_bgc.setdefault(bid, []).append({
                    "locus_tag": (row.get("locus_tag") or "").strip(),
                    "cds_start": cds_s,
                    "cds_end": cds_e,
                    "broad_class": _classify_gene(row.get("sec_met_domains") or ""),
                })
        for bid in genes_by_bgc:
            genes_by_bgc[bid].sort(key=lambda g: g["cds_start"])

    # SCHEMA-P01: distinguish "decomposition ran on real per-CDS gene data" from "no gene data
    # was available". Without this, a missing/absent *_gene_by_gene_all_bgcs.csv (e.g. the caller's
    # glob returned None, or a wrong path) leaves genes_by_bgc empty, so _fit_two_model sees zero
    # anchors for every BGC and returns ONE_MODEL_CONSISTENT — a *silent all-PASS* that reads as a
    # clean "0 TWO_MODEL_STRONG" negative when in fact the analysis never happened.
    if not gene_table_csv:
        gene_table_status = "MISSING"       # no gene table supplied to the fitter
    elif not Path(gene_table_csv).exists():
        gene_table_status = "NOT_FOUND"     # a path was given but does not exist
    elif not genes_by_bgc:
        gene_table_status = "EMPTY"         # file present but produced no usable per-CDS rows
    else:
        gene_table_status = "OK"

    # Load KCB rank-1 hits (optional). Key by exact antiSMASH clusterblast
    # file stem (e.g. NODE_9_length_..._c2) and by (contig, region_number).
    # Earlier code collapsed all regions on the same node and split only _c1/_c2,
    # which silently blanked KCB_DISCONNECT support for multi-region contigs.
    kcb_by_key: dict[Any, list[dict]] = {}
    if kcb_dir and Path(kcb_dir).is_dir():
        try:
            from .diagnostic_rescue import parse_cb as _parse_cb
            for txt in Path(kcb_dir).glob("*.txt"):
                parsed = _parse_cb(str(txt))
                if not parsed:
                    continue
                rank1_acc = max(parsed, key=lambda a: parsed[a]["cum_score"])
                hits = parsed[rank1_acc]["hits"]
                stem = txt.stem
                kcb_by_key[stem] = hits
                m = re.match(r"(.+)_c(\d+)$", stem)
                if m:
                    kcb_by_key[(m.group(1), int(m.group(2)))] = hits
        except Exception:
            pass  # KCB is optional

    def _bgc_kcb_keys(bgc: Any) -> list[Any]:
        keys: list[Any] = []
        source = Path(str(getattr(bgc, "source_gbk", "") or "")).name
        source_stem = source[:-4] if source.endswith(".gbk") else (Path(source).stem if source else "")
        m = re.match(r"(.+)\.region0*(\d+)$", source_stem, flags=re.I)
        if m:
            keys.append(f"{m.group(1)}_c{int(m.group(2))}")
            keys.append((m.group(1), int(m.group(2))))
        region = getattr(bgc, "region_number", None)
        if region in (None, ""):
            am = re.search(r"region0*(\d+)", str(getattr(bgc, "antismash_region", "") or ""), flags=re.I)
            region = int(am.group(1)) if am else None
        try:
            region_int = int(region) if region not in (None, "") else None
        except Exception:
            region_int = None
        if region_int is not None:
            for c in (getattr(bgc, "contig", "") or "", getattr(bgc, "node_id", "") or ""):
                if c:
                    keys.append(f"{c}_c{region_int}")
                    keys.append((c, region_int))
        out: list[Any] = []
        seen: set[str] = set()
        for k in keys:
            sig = repr(k)
            if sig not in seen:
                out.append(k)
                seen.add(sig)
        return out

    rows = []
    strong_count = 0
    candidate_count = 0

    for bgc in sorted(bgcs, key=lambda b: b.bgc_id):
        bid = bgc.bgc_id
        native_anchor: dict[str, str] = {}
        if strain is not None:
            # Delegate identity validation to the canonical owner. The optional
            # keyword preserves the legacy in-memory analysis API; the package
            # writer always supplies the run strain before emitting CSV output.
            from .exact_identity import exact_locus_from_native_manifest_bgc

            identity = exact_locus_from_native_manifest_bgc(
                strain,
                {
                    "contig": getattr(bgc, "contig", ""),
                    "node_id": getattr(bgc, "node_id", ""),
                    "antismash_region": getattr(bgc, "antismash_region", ""),
                    "bgc_id": bid,
                },
            )
            native_anchor = {
                "strain": identity.strain,
                "contig": identity.full_contig,
                "node_id": identity.normalized_node_id,
                "antismash_region": identity.region,
            }
        bgc_genes = genes_by_bgc.get(bid, [])
        bgc_len = max(
            (getattr(bgc, "end", 0) - getattr(bgc, "start", 0)),
            1,
        )

        fit = _fit_two_model(bgc_genes)
        confidence = fit["two_model_confidence"]

        # KCB disconnect check
        kcb_pct_a: "float | str" = ""
        kcb_pct_b: "float | str" = ""
        kcb_disconnect = ""
        kcb_anchor = (
            getattr(bgc, "closest_candidate_kcb_product", "") or
            getattr(bgc, "kcb_top", "") or ""
        )

        if confidence in ("TWO_MODEL_STRONG", "TWO_MODEL_CANDIDATE") and kcb_by_key:
            rank1_hits: list[dict] = []
            for _key in _bgc_kcb_keys(bgc):
                rank1_hits = kcb_by_key.get(_key, [])
                if rank1_hits:
                    break
            if rank1_hits:
                ga_set = {
                    t.strip()
                    for t in str(fit.get("group_a_anchor_genes", "")).split(";")
                    if t.strip()
                }
                gb_set = {
                    t.strip()
                    for t in str(fit.get("group_b_anchor_genes", "")).split(";")
                    if t.strip()
                }
                pct_a, pct_b, disc = _kcb_support_by_group(rank1_hits, ga_set, gb_set)
                kcb_pct_a = pct_a
                kcb_pct_b = pct_b
                kcb_disconnect = "YES" if disc else "no"

        if confidence == "TWO_MODEL_STRONG":
            strong_count += 1
        elif confidence == "TWO_MODEL_CANDIDATE":
            candidate_count += 1

        rows.append({
            "bgc_id": bid,
            "contig": native_anchor.get("contig", bgc.contig),
            "bgc_len_bp": bgc_len,
            "antismash_products": "; ".join(
                (getattr(bgc, "products", None) or [])[:5]
            ),
            "n_genes": fit["n_genes"],
            "n_anchor_genes": fit["n_anchor_genes"],
            "two_model_confidence": confidence,
            "group_a_class": fit.get("group_a_class", ""),
            "group_a_anchor_genes": fit.get("group_a_anchor_genes", ""),
            "group_a_start_bp": fit.get("group_a_start_bp", ""),
            "group_a_end_bp": fit.get("group_a_end_bp", ""),
            "group_b_class": fit.get("group_b_class", ""),
            "group_b_anchor_genes": fit.get("group_b_anchor_genes", ""),
            "group_b_start_bp": fit.get("group_b_start_bp", ""),
            "group_b_end_bp": fit.get("group_b_end_bp", ""),
            "gap_bp": fit.get("gap_bp", ""),
            "gap_pct_window": fit.get("gap_pct_window", ""),
            "class_coherence_score": fit.get("class_coherence_score", ""),
            # SCHEMA-P01: when no gene table was available this BGC has zero genes; report the true
            # cause instead of the misleading "fewer than 2 anchor genes".
            "null_reason": (
                f"GENE_TABLE_{gene_table_status}: no per-CDS gene data — BGC not analyzed for two-model"
                if gene_table_status != "OK" and not bgc_genes
                else fit.get("null_reason", "")
            ),
            "kcb_anchor": (kcb_anchor[:80] if kcb_anchor else ""),
            "kcb_support_group_a_pct": kcb_pct_a,
            "kcb_support_group_b_pct": kcb_pct_b,
            "kcb_architectural_disconnect": kcb_disconnect,
            "interpretation_guard": _INTERP_GUARD,
            "strain": native_anchor.get("strain", ""),
            "node_id": native_anchor.get("node_id", ""),
            "antismash_region": native_anchor.get("antismash_region", ""),
        })

    # SCHEMA-P01: a run that never saw gene data is INCOMPLETE, not a clean PASS, and its
    # summary must not read as a "0 STRONG" negative. Callers key on summary_line/rows, and the
    # happy-path status contract ("PASS" with a real gene table) is preserved.
    if gene_table_status == "OK":
        return {
            "status": "PASS",
            "gene_table_status": gene_table_status,
            "rows": rows,
            "strong_count": strong_count,
            "candidate_count": candidate_count,
            "summary_line": (
                f"BGC two-model analysis: {strong_count} TWO_MODEL_STRONG, "
                f"{candidate_count} TWO_MODEL_CANDIDATE across {len(bgcs)} BGCs."
            ),
        }
    return {
        "status": "INCOMPLETE",
        "gene_table_status": gene_table_status,
        "rows": rows,
        "strong_count": strong_count,
        "candidate_count": candidate_count,
        "summary_line": (
            f"BGC two-model analysis NOT MEANINGFUL: gene table {gene_table_status} — no per-CDS "
            f"gene data loaded for {len(bgcs)} BGC(s); TWO_MODEL results are not a clean negative "
            f"(re-run after the gene table is written)."
        ),
    }


# ---------------------------------------------------------------------------
# Triage-board cell helper
# ---------------------------------------------------------------------------

def two_model_flag_cell(bgc_id: str, decomp_result: "dict | None") -> str:
    """Return the triage-board Two_Model_Flag cell for one BGC.

    Empty string for ONE_MODEL_CONSISTENT. For STRONG/CANDIDATE includes
    the class pair and gap so the analyst can act without opening the full CSV.
    """
    if not decomp_result:
        return ""
    row = next(
        (r for r in decomp_result.get("rows", []) if r["bgc_id"] == bgc_id),
        None,
    )
    if not row or row["two_model_confidence"] == "ONE_MODEL_CONSISTENT":
        return ""
    tier = row["two_model_confidence"].replace("TWO_MODEL_", "")
    cls_a = row.get("group_a_class", "?")
    cls_b = row.get("group_b_class", "?")
    gap = row.get("gap_bp", "")
    try:
        gap_str = f"{int(gap):,}bp"
    except (ValueError, TypeError):
        gap_str = str(gap)
    disc = " [KCB_DISCONNECT]" if row.get("kcb_architectural_disconnect") == "YES" else ""
    return f"TWO_MODEL_{tier}:{cls_a}+{cls_b} ({gap_str}){disc}"
