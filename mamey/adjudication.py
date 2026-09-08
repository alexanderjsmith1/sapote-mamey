"""adjudication.py — apply the curated adjudication overlay on top of the MIBiG reference base.

The overlay (`adjudications.json`) carries curated JUDGMENT only — `expected_marker_set`,
`hard_scan_verdict`, `architecture_capacity` flags, lit diagnostic genes — keyed by accession. It
carries NO BGC selection. Applied to a MIBiG-auto index entry:

  - matched accession  -> reference_tier="CURATED-ADJUDICATED": earns marker credit from the
    overlay's expected_marker_set, verdict/capacity surfaced, KS disagreement (curated vs auto) flagged.
  - unmatched accession -> reference_tier="MIBIG-AUTO": expected_marker_set forced empty (no marker
    credit), region+size-dominant similarity only.

This is the mechanism that lets MIBiG be the broad, current base while the session's curation rides
on top as a thin, accession-keyed layer — without treating the original scrape's BGC selection as
authoritative.
"""
from __future__ import annotations
import json

def load_adjudications(path) -> dict:
    """Return the by_accession overlay dict from an adjudications.json file."""
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    return d.get("by_accession", d if isinstance(d, dict) else {})

def adjudicate(entry: dict, by_accession: dict) -> dict:
    """Return a shallow-annotated copy of a MIBiG index entry with the overlay applied."""
    out = dict(entry)
    adj = by_accession.get(entry.get("accession"))
    if not adj:
        out["reference_tier"] = "MIBIG-AUTO"
        out["expected_marker_set"] = []          # no marker credit for un-adjudicated auto entries
        return out
    out["reference_tier"] = "CURATED-ADJUDICATED"
    out["expected_marker_set"] = adj.get("expected_marker_set", [])
    out["hard_scan_verdict"] = adj.get("hard_scan_verdict")
    out["architecture_capacity"] = adj.get("architecture_capacity")
    out["curated_signature"] = adj.get("curated_signature")
    # NOTE: the raw adj dict is NOT injected (leak-safety); only the named fields above are surfaced.
    csig = adj.get("curated_signature", {}) or {}
    cks = csig.get("pks_ks"); aks = (entry.get("architecture_signature") or {}).get("pks_ks")
    if cks is not None and aks is not None and cks != aks:
        out["ks_disagreement"] = {"curated": cks, "auto": aks}
    return out

def build_reference_space(mibig_index: dict, by_accession: dict) -> list:
    """Apply the overlay across a loaded MIBiG index dict -> list of adjudicated entries."""
    return [adjudicate(e, by_accession) for e in mibig_index.get("entries", [])]
