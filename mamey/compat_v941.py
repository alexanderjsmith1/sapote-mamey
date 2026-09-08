"""Sapote-Mamey v9.4.1 additive compatibility fields.  version-sync-ok: bundle-compat shim, version is intentional.

This module adds forward-compatible output fields only.  It does not change
regex scan backend calls or legacy scoring.  The values are source-derived
claim-calibration helpers used by the workbook/package writers.
"""
from __future__ import annotations

from typing import Any

from .models import BGCRecord, SourceScanBundle
from .source_scans import CCTT_PATTERNS as _CCTT_PATTERNS

# Tier-1 diagnostic CCTT triggers = the full class-definitive T43 trigger set, derived from the
# active scanning backend (source_scans.CCTT_PATTERNS) so it CANNOT drift out of sync with the
# triggers. The previous hand-typed token subset ("DKP","HAL","LAN","ENE","PHO","THA","LASSO","TET")
# silently dropped IDC/NUC/BLA/AMC/NN (under-tiering e.g. an indolocarbazole-core BGC's T43-IDC) and only matched
# PTM/XHAL by substring accident ("TET" inside "tetramate", "HAL" inside "XHAL"). Matching on the
# full trigger name (below) removes those accidents and the omissions in one move.
_DIAGNOSTIC_CCTT_TRIGGERS = tuple(_CCTT_PATTERNS.keys())


def _is_diagnostic_cctt(hit: Any) -> bool:
    """True if a CCTT hit names a Tier-1 class-definitive T43 trigger.

    Matches the full trigger name (not a 3-letter substring), so unrelated tokens can't collide.
    """
    s = str(hit)
    return any(trig in s for trig in _DIAGNOSTIC_CCTT_TRIGGERS)

EFLS_CEILING = "edge/linkage candidate; flank evidence is source-derived; not a merged-cluster claim without long-read closure"
DKP_CEILING = "candidate DKP-scaffold BGC; same-family-not-same-product; specific dipeptide requires isolation"


def _safe_join(values: list[Any] | tuple[Any, ...] | set[Any] | None) -> str:
    if not values:
        return ""
    return "; ".join(str(v) for v in values if v not in (None, ""))


def _cctt_per_bgc(ss: SourceScanBundle | None) -> dict[str, list[str]]:
    return ((ss.cctt or {}).get("bgc_coupling", {}) if ss else {}) or {}


def _dss_per_bgc(ss: SourceScanBundle | None) -> dict[str, dict[str, Any]]:
    return ((ss.per_bgc_dss or {}).get("per_bgc", {}) if ss else {}) or {}


def _resistance_per_bgc(ss: SourceScanBundle | None) -> dict[str, dict[str, Any]]:
    return ((ss.resistance_tiers or {}).get("per_bgc", {}) if ss else {}) or {}


def _efls_pairs_by_bgc(ss: SourceScanBundle | None) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    if not ss:
        return out
    for p in (ss.efls or {}).get("candidate_pairs", []) or []:
        for key in ("bgc_a", "bgc_b"):
            bid = p.get(key)
            if bid:
                out.setdefault(str(bid), []).append(p)
    return out


def _dkp_calls_by_bgc(ss: SourceScanBundle | None) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not ss:
        return out
    dkp = ((ss.cctt or {}).get("dkp_cdps_context", {}) or {})
    for c in dkp.get("calls", []) or []:
        bid = c.get("bgc_id")
        if bid:
            out[str(bid)] = dict(c)
    return out


def efls_fields_for_bgc(bgc: BGCRecord, ss: SourceScanBundle | None) -> dict[str, str]:
    """Return additive EFLS fields for a BGC."""
    if bgc.edge_status == "Interior":
        return {
            "efls_status": "NOT_APPLICABLE_INTERIOR",
            "flank_census_tier1": "N/A_interior",
            "flank_census_tier2_todo": "N/A_interior",
            "cross_contig_candidate_set": "N/A_interior",
            "efls_claim_ceiling": "N/A_interior",
        }
    cctt = _cctt_per_bgc(ss).get(bgc.bgc_id, [])
    tier1 = [x for x in cctt if _is_diagnostic_cctt(x)]
    dss = _dss_per_bgc(ss).get(bgc.bgc_id, {})
    tier2 = []
    if dss.get("dss") not in (None, "", 0, "0"):
        tier2.append(f"DSS={dss.get('dss')} external confirmation")
    pairs = _efls_pairs_by_bgc(ss).get(bgc.bgc_id, [])
    linked: list[str] = []
    for p in pairs:
        other = p.get("bgc_b") if p.get("bgc_a") == bgc.bgc_id else p.get("bgc_a")
        if other and other not in linked:
            linked.append(str(other))
    return {
        "efls_status": "FLANK_REVIEWED" if tier1 or tier2 or linked else "FLANK_PENDING",
        "flank_census_tier1": _safe_join(tier1),
        "flank_census_tier2_todo": _safe_join(tier2),
        "cross_contig_candidate_set": _safe_join(linked) if linked else "none",
        "efls_claim_ceiling": EFLS_CEILING,
    }


def _has_dkp_trigger(bgc: BGCRecord, ss: SourceScanBundle | None) -> bool:
    products = " ".join(bgc.products).lower()
    if "cdps" in products or "cyclodipeptide" in products or "diketopiperazine" in products:
        return True
    return any("DKP" in str(x) or "cdps" in str(x).lower() for x in _cctt_per_bgc(ss).get(bgc.bgc_id, []))


def dkp_fields_for_bgc(bgc: BGCRecord, ss: SourceScanBundle | None) -> dict[str, str]:
    """Return additive DKP/CDPS rank and provenance fields."""
    call = _dkp_calls_by_bgc(ss).get(bgc.bgc_id, {})
    has_dkp = bool(call) or _has_dkp_trigger(bgc, ss)
    if not has_dkp:
        return {"dkp_rank": "", "dkp_cdps_evidence": "", "dkp_oxidase_homology": "", "dkp_provenance": "", "dkp_claim_ceiling": ""}

    cdo = str(call.get("cdo_adjacent", "")).lower() == "yes"
    products = " ".join(bgc.products).lower()
    accession = str(getattr(bgc, "closest_mibig_accession", ""))
    locator = str(getattr(bgc, "source_kcb_locator", ""))
    kcb_text = " ".join([accession, locator, str(getattr(bgc, "closest_candidate_kcb_product", "")), str(getattr(bgc, "kcb_top", ""))]).lower()
    dkp_reference = any(x in kcb_text for x in ["bgc0001986", "purincyclamide", "bgc0000851", "albonoursin"])

    tailoring = str(call.get("tailoring_context", "")).lower() == "yes"
    if cdo or dkp_reference:
        rank = "DKP-A"
        oxidase = call.get("cdo_loci") or "albonoursin/purincyclamide-family KCB context supports dehydro-DKP review"
    elif tailoring:
        rank = "DKP-B"
        oxidase = ""
    elif call:
        # v9.7.371 fix: was 'elif has_dkp:', which is tautologically True here (has_dkp gates
        # the early return above and is never reassigned), making the DKP-D branch dead code.
        # A formal per-BGC DKP scan call (this branch) is a stronger signal than a bare
        # products/CCTT substring trigger with no formal call (the DKP-D branch below) --
        # they must stay distinct so a weak trigger-only signal is not mislabeled
        # 'diagnostic-CDPS' at line ~156.
        rank = "DKP-C"
        oxidase = ""
    else:
        rank = "DKP-D"
        oxidase = ""

    evidence_bits = []
    if call.get("cdps_loci"):
        evidence_bits.append(f"CDPS={call.get('cdps_loci')}")
    elif has_dkp:
        evidence_bits.append("CDPS=source-derived product/trigger call")
    if call.get("cdo_loci"):
        evidence_bits.append(f"CDO/oxidase={call.get('cdo_loci')}")
    if call.get("tailoring_loci"):
        evidence_bits.append(f"tailoring={call.get('tailoring_loci')}")
    if not evidence_bits:
        evidence_bits.append("weak/ambiguous CDPS; needs confirmation")

    provenance = getattr(bgc, "closest_product_provenance", "UNRESOLVED") or "UNRESOLVED"
    gene_class = "diagnostic-CDPS" if rank in {"DKP-A", "DKP-B", "DKP-C"} else "weak-CDPS-needs-confirmation"
    if "housekeeping" in str(getattr(bgc, "product_claim_ceiling", "")).lower():
        gene_class = "housekeeping-downweighted"
    return {
        "dkp_rank": rank,
        "dkp_cdps_evidence": "; ".join(evidence_bits),
        "dkp_oxidase_homology": oxidase,
        "dkp_provenance": f"{provenance}; gene_driver={gene_class}",
        "dkp_claim_ceiling": DKP_CEILING,
    }


def claim_calibration_fields_for_bgc(bgc: BGCRecord, triage: Any | None, ss: SourceScanBundle | None) -> dict[str, str | float | int]:
    """Return orthogonal priority/confidence calibration fields for a BGC."""
    cctt_hits = _cctt_per_bgc(ss).get(bgc.bgc_id, [])
    rt = _resistance_per_bgc(ss).get(bgc.bgc_id, {})
    dss_raw = _dss_per_bgc(ss).get(bgc.bgc_id, {}).get("dss", 0)
    try:
        dss = float(dss_raw or 0)
    except Exception:
        dss = 0.0
    diagnostic_count = len([h for h in cctt_hits if _is_diagnostic_cctt(h)])
    resistance_bonus = 2 if str(rt.get("tier", "")).startswith("T1") else (1 if rt.get("tier") else 0)
    diagnostic_signal_score = round(diagnostic_count * 3 + dss + resistance_bonus, 2)

    if diagnostic_count > 0:
        ewt = "TIER_1_DIAGNOSTIC"
    elif dss > 0 or rt.get("tier"):
        ewt = "TIER_2_CLASS_SUPPORTING"
    elif getattr(bgc, "kcb_cumulative", None):
        ewt = "TIER_3_CONTEXT"
    elif bgc.kcb_top:
        ewt = "TIER_4_GENERIC"
    else:
        ewt = "SOURCE_DERIVED_ONLY"

    provenance = getattr(bgc, "closest_product_provenance", "UNRESOLVED")
    if provenance == "MIBIG_REFERENCE_LINE" and diagnostic_count > 0:
        claim_conf = "HIGH"
    elif provenance == "MIBIG_REFERENCE_LINE" or diagnostic_count > 0:
        claim_conf = "MODERATE"
    elif provenance == "KCB_TOP_FIELD" or bgc.kcb_top:
        claim_conf = "SOURCE_DERIVED_ONLY"
    else:
        claim_conf = "LOW"
    if "housekeeping" in str(getattr(bgc, "product_claim_ceiling", "")).lower():
        ewt = "OVERINTERPRETATION_PRONE"
        claim_conf = "SOURCE_DERIVED_ONLY"

    ceiling = getattr(bgc, "product_claim_ceiling", "unresolved; do not use product name") or "unresolved; do not use product name"
    products = "; ".join(bgc.products) or "unresolved product class"
    if claim_conf in {"HIGH", "MODERATE"}:
        safe = f"{bgc.bgc_id} is a source-derived candidate {products} BGC with diagnostic marker support; product identity requires isolation."
    elif bgc.kcb_top:
        safe = f"{bgc.bgc_id} is a source-derived similarity/priority lead; do not assert product identity without chemistry."
    else:
        safe = f"{bgc.bgc_id} is a candidate BGC for follow-up; product identity is unresolved."
    return {
        "diagnostic_signal_score": diagnostic_signal_score,
        "evidence_weight_tier": ewt,
        "claim_confidence": claim_conf,
        "claim_ceiling": ceiling,
        "safe_claim": safe,
    }


def compatibility_fields_for_bgc(bgc: BGCRecord, triage: Any | None, ss: SourceScanBundle | None) -> dict[str, Any]:
    out: dict[str, Any] = {}
    out.update(efls_fields_for_bgc(bgc, ss))
    out.update(dkp_fields_for_bgc(bgc, ss))
    out.update(claim_calibration_fields_for_bgc(bgc, triage, ss))
    return out
