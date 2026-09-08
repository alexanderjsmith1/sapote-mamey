"""lead_board.py — the per-strain Lead Board (Mamey output mode).

The honest per-strain output for a fragmented (Poor / Very-Poor) assembly is a SHORT ranked board
of genuinely interpretable leads, not a deep dive on every fragment. A lead is a BGC carrying a
**class-definitive marker** (CCTT cassette or curated TIGRFAM panel) OR a **complete (Interior)**
cluster. The board is **edge-agnostic** — a marker overrides edge status (Mamey spec §4.3) — so the
interpretable fragments that the corrected-count down-weighting and fragment-rescue tiering would
otherwise bury are surfaced and ranked.

This module is the single source of truth for the board: the package writer and the cohort
workbook sheet both call `build_lead_board`.
"""
from __future__ import annotations
import json
from typing import Any

# --- ITEM 2: the locked marker set --------------------------------------------------------------

# Class-definitive CCTT cassettes (committed-step / class-diagnostic; tailoring-only markers like
# halogenase are intentionally excluded — they don't define a class on their own).
CLASS_DEFINITIVE_CCTT = {
    "T43-ENE_enediyne":               "enediyne",
    "T43-PHO_phosphonate":            "phosphonate",
    "T43-NUC_nucleoside":             "nucleoside",
    "T43-IDC_indolocarbazole":        "indolocarbazole",
    "T43-TET_tetronate_spirotetronate": "tetronate",
    "T43-THA_thioamide":              "thioamide",
    "T43-DKP_cdps":                   "CDPS/DKP",
    "T43-LAN_lanthipeptide":          "lanthipeptide",
    "T43-AMC_aminocyclitol":          "aminocyclitol",
}

# Curated TIGRFAM diagnostic panel (per user request, now part of the lead signal).
# These come from antismash_evidence.DIAGNOSTIC_TIGRFAM; duplicated here as label map only.
TIGRFAM_PANEL = {
    "TIGR01454": "ansamycin (AHBA)",
    "TIGR03604": "thiopeptide",
    "TIGR03828": "enediyne",
    "TIGR04186": "nucleoside (NikJ)",
}


def _region_key(bgc) -> str:
    """Build the evidence by-region key (e.g. 'WWFW01000001.1_c1') from a BGC."""
    rn = getattr(bgc, "region_number", None)
    if rn is None:
        ar = getattr(bgc, "antismash_region", "") or ""
        rn = "".join(ch for ch in ar if ch.isdigit()).lstrip("0") or "1"
    return f"{getattr(bgc, 'contig', '')}_c{int(rn)}"


def _tigrfam_hits_for_region(antismash_evidence: dict, region_key: str) -> list[str]:
    """Return curated TIGRFAM panel accessions present in a region's gbk_pfam hits."""
    if not antismash_evidence:
        return []
    gbk = antismash_evidence.get("gbk_pfam_hits", {}) or {}
    hits = gbk.get(region_key)
    if not hits:
        return []
    blob = json.dumps(hits)
    # NOTE: substring match is safe because TIGRFAM accessions are fixed 5-digit (TIGRXXXXX);
    # no prefix-collision risk exists in the real TIGRFAM namespace for this 4-entry panel.
    return [acc for acc in TIGRFAM_PANEL if acc in blob]


def build_lead_board(run, cctt_coupling: dict, antismash_evidence: dict) -> list[dict[str, Any]]:
    """Compute the ranked Lead Board for a strain.

    Returns a list of dicts (already ranked) with the signals that qualified each BGC.
    A BGC qualifies if it has >=1 class-definitive CCTT marker, >=1 TIGRFAM panel hit, or is Interior.
    Ranking: more distinct signals first, then longer cluster first.
    """
    cctt_coupling = cctt_coupling or {}
    rows: list[dict[str, Any]] = []
    for b in run.bgcs:
        signals: list[str] = []
        # CCTT class-definitive cassettes coupled to this BGC
        for m in cctt_coupling.get(b.bgc_id, []) or []:
            if m in CLASS_DEFINITIVE_CCTT:
                signals.append(CLASS_DEFINITIVE_CCTT[m])
        # curated TIGRFAM panel hits in this BGC's region
        for acc in _tigrfam_hits_for_region(antismash_evidence, _region_key(b)):
            signals.append(TIGRFAM_PANEL[acc])
        interior = (getattr(b, "edge_status", "") == "Interior")
        if interior:
            signals.append("interior")
        signals = sorted(set(signals))
        if not signals:
            continue
        length_kb = round((getattr(b, "end", 0) - getattr(b, "start", 0)) / 1000, 1)
        # marker-bearing signals (everything except the bare 'interior' tag)
        markers = [s for s in signals if s != "interior"]
        rows.append({
            "strain": run.context.strain_id,
            "bgc_id": b.bgc_id,
            "products": "; ".join((getattr(b, "products", []) or [])[:6]),
            "length_kb": length_kb,
            "edge_status": getattr(b, "edge_status", ""),
            "markers": ", ".join(markers),
            "interior": "yes" if interior else "",
            "n_signals": len(signals),
            "kcb_anchor": getattr(b, "closest_candidate_kcb_product", None) or "",
            "contig": getattr(b, "contig", ""),
            "region": getattr(b, "antismash_region", ""),
            "locator": f"{getattr(b, 'contig', '')}:{getattr(b, 'antismash_region', '')}",
        })
    # rank: more distinct signals first, then longer cluster
    rows.sort(key=lambda r: (-r["n_signals"], -r["length_kb"]))
    for i, r in enumerate(rows, 1):
        r["rank"] = i
    return rows


LEAD_BOARD_HEADERS = [
    "Rank", "strain", "BGC_ID", "Products", "Length_kb", "Edge_Status",
    "Markers", "Interior", "N_Signals", "KCB_Anchor", "Locator",
]


def lead_board_csv_rows(board: list[dict[str, Any]]) -> list[list[Any]]:
    return [[
        r["rank"], r["strain"], r["bgc_id"], r["products"], r["length_kb"], r["edge_status"],
        r["markers"], r["interior"], r["n_signals"], r["kcb_anchor"], r["locator"],
    ] for r in board]


# v9.7.45 (B-8/F-9): dedicated single-axis (AB or AF) lead boards. The AB/AF board previously lived only
# as the AB_auto/AF_auto columns inside the triage board, ranked by one general Rank — so the antibacterial
# and antifungal lead boards were not directly locatable. These pre-sorted views put standing-rule-clean
# leads first (a saccharide/NAPAA/hglE/primary-metab row is marked in `Downgrade` and sunk, not dropped),
# so the #1 row is always a usable lead while downgraded rows stay visible for transparency.
AXIS_LEAD_BOARD_HEADERS = [
    "Board_rank", "BGC_ID", "Contig", "Node_ID", "Products",
    "Score", "Lead_tier", "KCB_top", "Downgrade", "Corrected_rank",
    "Strain", "antiSMASH_Region",
]


def axis_lead_board_rows(
    triage,
    bgc_by_id: dict,
    axis: str,
    *,
    strain: str | None = None,
) -> list[dict[str, Any]]:
    """Build a pre-sorted single-axis lead board. axis is 'ab' or 'af'.

    Clean leads first (sorted by descending axis score); rows carrying a standing-rule or
    primary-metabolism downgrade are marked in `Downgrade` and sorted to the bottom.
    """
    score_attr = "ab_score" if axis == "ab" else "af_score"
    rows: list[dict[str, Any]] = []
    for t in triage:
        bgc = bgc_by_id.get(t.bgc_id)
        if bgc is None:
            continue
        native_anchor: dict[str, str] = {}
        if strain is not None:
            # A package CSV is independently locatable only when it carries the
            # validated native roles; do not recreate them from filenames or aliases.
            from .exact_identity import exact_locus_from_native_manifest_bgc

            identity = exact_locus_from_native_manifest_bgc(
                strain,
                {
                    "contig": getattr(bgc, "contig", ""),
                    "node_id": getattr(bgc, "node_id", ""),
                    "antismash_region": getattr(bgc, "antismash_region", ""),
                    "bgc_id": t.bgc_id,
                },
            )
            native_anchor = {
                "Strain": identity.strain,
                "Contig": identity.full_contig,
                "Node_ID": identity.normalized_node_id,
                "antiSMASH_Region": identity.region,
            }
        # BC2-408 (rebased from a .407 finding, unlanded before seal): mobile_element_flag is
        # the THIRD corrected_rank-gating exclusion signal alongside standing_rule_flag/
        # primary_metabolism_flag (scoring.py's own comment: "Downgraded rows keep their raw
        # scores but get corrected_rank=None" applies uniformly to all three). This file was
        # missed by the AUDIT_378 sweep that added mobile_element_flag to card_verdicts.py/
        # boundary_audit.py/domain_level.py/cli.py/serialize.py -- confirmed by af_dossier.py's
        # own docstring, which explicitly names this exact omission ("lead_board.py's
        # `Downgrade` cell is built from only standing_rule_flag/primary_metabolism_flag, never
        # mobile_element_flag") as the reason it reads Corrected_rank instead of trusting this
        # column. Without this fix, a mobile-dominant ICE/transposon region (uncorroborated,
        # AB/AF already capped by scoring.py) shows a BLANK Downgrade cell and sorts among
        # genuine clean leads by score alone, instead of being visibly marked and sorted to the
        # bottom like the other two exclusion reasons.
        downgrade = (getattr(t, "standing_rule_flag", "") or
                     ("primary_metabolism" if getattr(t, "primary_metabolism_flag", False) else "") or
                     (getattr(t, "mobile_element_flag", "") or ""))
        rows.append({
            "BGC_ID": t.bgc_id,
            "Contig": native_anchor.get("Contig", getattr(bgc, "contig", "") or ""),
            "Node_ID": native_anchor.get("Node_ID", getattr(bgc, "node_id", "") or ""),
            "Products": "; ".join(getattr(bgc, "products", [])[:6]),
            "Score": getattr(t, score_attr, "") if getattr(t, score_attr, None) is not None else "",
            "Lead_tier": getattr(t, "lead_tier", "") or "",
            "KCB_top": getattr(bgc, "closest_candidate_kcb_product", "") or getattr(bgc, "kcb_top", "") or "",
            "Downgrade": downgrade,
            "Corrected_rank": getattr(t, "corrected_rank", "") if getattr(t, "corrected_rank", None) is not None else "",
            "Strain": native_anchor.get("Strain", ""),
            "antiSMASH_Region": native_anchor.get("antiSMASH_Region", ""),
        })
    rows.sort(key=lambda r: (bool(r["Downgrade"]), -(float(r["Score"]) if r["Score"] not in ("", None) else 0.0)))
    for i, r in enumerate(rows, 1):
        r["Board_rank"] = i
    return rows
