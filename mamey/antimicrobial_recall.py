"""Antimicrobial recall layer (v9.7.120) — boost-only compound-anchor AB/AF capacity.

WHY THIS EXISTS
---------------
The keyword scorer (scoring.py) builds AB/AF from the antiSMASH product-class label
only. It deliberately ignores the resolved KCB compound name to avoid genome-self-hit
contamination (the P-7 guard). The side effect: when a BGC has a clean, own-evidence
MIBiG anchor to a KNOWN antimicrobial (e.g. ristomycin -> glycopeptide, tetramycin ->
polyene), that activity-class knowledge never reaches AB/AF. Known antibacterials and
antifungals compress into a ~38-55 band indistinguishable from generic NRPS/PKS hybrids.

This layer adds a SECOND, parallel pair of scores — ab_recall / af_recall — whose only
job is to FIND antimicrobial BGCs the keyword scorer misses. It does NOT replace the
keyword scores and is NOT a bioactivity claim about any specific BGC.

DESIGN RULES (locked with the user, Jun 2026)
---------------------------------------------
1. BOOST-ONLY. The recall score is max(keyword_base, anchor_target). An anchor can only
   RAISE the AB/AF capacity call or leave it unchanged. It can never lower it.
2. NO PENALTIES. A non-antimicrobial anchor (cytotoxic, immunosuppressant, siderophore,
   pigment, signalling) carries ab=0/af=0 in the family table, so it contributes no
   boost and the BGC stays at its keyword baseline. Known non-antimicrobial compounds
   are neither boosted nor penalised.
3. OWN-EVIDENCE ONLY. The anchor is read from `closest_mibig_accession` (the P-7-clean
   resolved field), never from raw `kcb_top`. Preserves the genome-self-hit guard.
4. CONCORDANCE-GATED. The boost fires only when the anchor is not a suppressing
   mis-anchor and the architecture class is not DISCORDANT with the anchor. A discordant
   or suppressed anchor falls back to the keyword base (no boost).

Backward compatible: when no anchor resolves, ab_recall == ab_score and af_recall == af_score.
"""
from __future__ import annotations
import json
import os
import re

_DATA = os.path.join(os.path.dirname(__file__), "data", "families", "family_antimicrobial_recall.json")
_FAM_MAP = os.path.join(os.path.dirname(__file__), "data", "families", "kcb_compound_family.json")

# score-target shaping: a pure single-class antimicrobial (capacity ~0.9-0.95) should land
# in High/Exceptional. base + SPAN * capacity.
_AB_BASE, _AF_BASE = 25.0, 20.0
_AB_SPAN, _AF_SPAN = 70.0, 72.0

# A genuine SUPPRESSING mis-anchor (the engine also records informational anchor notes
# like '[polyene=nystatin]' in the same field — those are NOT suppression and must pass).
_SUPPRESSING_MISANCHOR = ("anchor_no_DOIS", "anchor_<", "no_ene_KS", "class_mismatch", "similarity_only")

_ACC_RE = re.compile(r"(BGC\d{7})")


def _load():
    with open(_DATA, encoding="utf-8") as fh:
        amr = json.load(fh)
    # kcb_compound_family.json is a MIBiG-accession -> compound-family BOOST map. It is not
    # shipped in the public release (user-regenerates it via tools/build_family_map.py); when
    # absent the family boost simply falls back to the keyword baseline (not a hard failure).
    # NOTE: this module is imported by core scoring.py, so an unguarded open() here fails the
    # whole engine import when the file is removed.
    fam = {}
    try:
        with open(_FAM_MAP, encoding="utf-8") as fh:
            fam = json.load(fh).get("by_accession", {})
    except FileNotFoundError:
        fam = {}
    return amr, fam


_AMR, _FAMBYACC = _load()
_BYFAM = _AMR["by_family"]
_OVERRIDE = _AMR["family_overrides_by_accession"]
_PIGMENT_MARKERS = tuple(_AMR.get("pigment_name_markers", []))


def family_for_accession(acc: str) -> str | None:
    """accession (BGC#######) -> compound family, override table first."""
    if not acc:
        return None
    if acc in _OVERRIDE:
        return _OVERRIDE[acc]
    return _FAMBYACC.get(acc)


def recall_scores(
    ab_keyword: float,
    af_keyword: float,
    *,
    closest_mibig_accession: str = "",
    closest_kcb_product: str = "",
    misanchor_flag: str = "",
    concordance_verdict: str = "",
) -> dict:
    """Compute boost-only ab_recall / af_recall for one BGC.

    All inputs are own-evidence fields already on the BGC/TriageRecord. Returns a dict:
      ab_recall, af_recall (floats), anchor_family (str|''), recall_applied (bool),
      recall_note (str).
    """
    ab_kw = float(ab_keyword or 0.0)
    af_kw = float(af_keyword or 0.0)

    acc = ""
    if closest_mibig_accession and closest_mibig_accession != "UNRESOLVED":
        m = _ACC_RE.search(closest_mibig_accession)
        if m:
            acc = m.group(1)

    fam = family_for_accession(acc) if acc else None
    prof = _BYFAM.get(fam) if fam else None

    # gate: pigment-name override (spore pigment resolves to a T2 aromatic family but is a
    # non-antimicrobial pigment -> no boost).
    name_l = (closest_kcb_product or "").lower()
    is_pigment = any(mk in name_l for mk in _PIGMENT_MARKERS)

    is_suppressed = any(tok in (misanchor_flag or "") for tok in _SUPPRESSING_MISANCHOR)
    discordant = (concordance_verdict or "").strip().upper() == "DISCORDANT"

    if not prof or is_pigment or is_suppressed or discordant:
        note = (
            "no_family" if not prof else
            "pigment_name" if is_pigment else
            "suppressed_misanchor" if is_suppressed else
            "discordant_anchor"
        )
        return {
            "ab_recall": round(ab_kw, 1),
            "af_recall": round(af_kw, 1),
            "anchor_family": fam or "",
            "recall_applied": False,
            "recall_note": f"keyword_baseline ({note})",
        }

    ab_target = _AB_BASE + _AB_SPAN * float(prof.get("ab", 0.0))
    af_target = _AF_BASE + _AF_SPAN * float(prof.get("af", 0.0))

    # BOOST-ONLY: never below the keyword base.
    ab_rec = max(ab_kw, ab_target)
    af_rec = max(af_kw, af_target)

    return {
        "ab_recall": round(min(ab_rec, 100.0), 1),
        "af_recall": round(min(af_rec, 100.0), 1),
        "anchor_family": fam,
        "recall_applied": (ab_rec > ab_kw or af_rec > af_kw),
        "recall_note": f"anchor_boost(fam={fam})",
    }
