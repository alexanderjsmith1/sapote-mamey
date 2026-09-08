"""concordance.py — reference-BGC concordance check (Mamey, deterministic).

Given a BGC's KCB anchor + the engine markers it fired + its locus size, resolve the anchor against the
reference-BGC marker library and compute a ConcordanceResult: how many of the reference compound's expected
markers are present, and whether the locus is the right size. This is EVIDENCE the judgment layer (Sapote)
reasons over — it does NOT change triage scoring.

Verdicts (advisory):
  NO_REFERENCE        anchor does not resolve to a library entry (concordance not applicable)
  EXPECTED_PENDING_LIT entry exists but reference truth (expected markers/size) not yet populated by LIT
  CONCORDANT          >=50% of expected markers present and size within 0.5-2.0x  -> strengthens the call
  PARTIAL             some but <50% of expected markers present                    -> weak support
  DISCORDANT          anchor matches but NONE of the expected markers present       -> misanchor warning

Provenance: the check is COMPUTED from OBSERVED inputs (found markers/size) against SEED/LIT reference data;
a low concordance is the same claim-safety signal as the §4.3 misanchor guard, but driven by a real reference
gene/marker complement instead of a keyword.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional

_DEFAULT_LIB = os.path.join(os.path.dirname(__file__), "data", "reference_bgc_library.json")

CONCORDANT_MARKER_FRAC = 0.5
SIZE_LO, SIZE_HI = 0.5, 2.0


@dataclass
class ConcordanceResult:
    bgc_id: str
    anchor: str
    matched_compound: Optional[str]
    matched_genus: Optional[str]
    # v9.7.352 (AMBER_CORRECTNESS FIX 1): the pipeline wiring in source_scans.run_source_scans
    # serialises matched_class + size_ok onto concordance_per_bgc, but the dataclass never carried
    # them, so building that dict threw AttributeError (silently caught -> every BGC stored as
    # NO_REFERENCE). Carry them here so the wiring emits the real verdict/class.
    matched_class: Optional[str] = None
    size_ok: Optional[bool] = None
    expected_markers: list[str] = field(default_factory=list)
    found_markers: list[str] = field(default_factory=list)
    markers_present: list[str] = field(default_factory=list)
    markers_present_of_expected: Optional[float] = None
    found_size_kb: Optional[float] = None
    expected_size_kb: Optional[float] = None
    size_ratio: Optional[float] = None
    verdict: str = "NO_REFERENCE"
    notes: str = ""

    def as_evidence(self) -> str:
        """One-line claim-safe evidence string for Sapote."""
        if self.verdict == "NO_REFERENCE":
            return f"{self.bgc_id}: anchor '{self.anchor}' not in reference library — concordance N/A."
        if self.verdict == "EXPECTED_PENDING_LIT":
            return (f"{self.bgc_id}: matches reference '{self.matched_compound}' "
                    f"({self.matched_genus}); reference marker set pending LIT.")
        frac = f"{self.markers_present_of_expected:.0%}" if self.markers_present_of_expected is not None else "n/a"
        size = f"{self.size_ratio:.2f}x" if self.size_ratio is not None else "n/a"
        return (f"{self.bgc_id}: {self.verdict} with reference '{self.matched_compound}' "
                f"({self.matched_genus}) — {frac} of expected markers present "
                f"({'+'.join(self.markers_present) or 'none'}), locus size {size}.{(' ' + self.notes) if self.notes else ''}")


def _short(m: str) -> str:
    m = (m or "").strip()
    return m.split("_")[0] if m.startswith("T43-") else m


def load_reference_library(path: str = _DEFAULT_LIB) -> dict:
    # reference_bgc_library.json is the curated positive-control library. It is NOT shipped in
    # the public release (user-regenerates it via tools/seed_reference_library.py +
    # tools/build_mibig_index.py); when absent, concordance resolves no anchor and every BGC is
    # reported NO_REFERENCE -- the already-graceful path (see source_scans concordance wiring).
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def resolve_anchor(anchor: str, library: dict) -> Optional[dict]:
    """Resolve a KCB anchor string to a library entry by compound name / alias (case-insensitive substring,
    longest-alias-wins to avoid a short alias swallowing a more specific match)."""
    if not anchor:
        return None
    a = anchor.lower()
    best, best_len = None, 0
    for e in library.get("entries", []):
        for alias in e.get("aliases", []) + [e["compound"].lower()]:
            alias = alias.lower()
            if alias and alias in a and len(alias) > best_len:
                best, best_len = e, len(alias)
    return best


def concordance_check(bgc_id: str, anchor: str, found_markers, found_size_kb: Optional[float],
                      library: Optional[dict] = None) -> ConcordanceResult:
    library = library or load_reference_library()
    found = sorted({_short(m) for m in (found_markers or []) if m})
    entry = resolve_anchor(anchor, library)
    if entry is None:
        return ConcordanceResult(bgc_id=bgc_id, anchor=anchor, matched_compound=None, matched_genus=None,
                                 found_markers=found, found_size_kb=found_size_kb, verdict="NO_REFERENCE")

    expected = sorted({_short(m) for m in entry.get("expected_marker_set", []) if m})
    exp_size = entry.get("expected_size_kb", None)
    res = ConcordanceResult(
        bgc_id=bgc_id, anchor=anchor, matched_compound=entry["compound"], matched_genus=entry.get("genus"),
        matched_class=entry.get("class"),
        expected_markers=expected, found_markers=found, found_size_kb=found_size_kb, expected_size_kb=exp_size)

    # reference truth not yet populated -> pending
    if not expected and exp_size in (None, "", "UNRESOLVED", "PENDING_LIT"):
        res.verdict = "EXPECTED_PENDING_LIT"
        return res

    if expected:
        present = sorted(set(found) & set(expected))
        res.markers_present = present
        res.markers_present_of_expected = len(present) / len(expected)
    if isinstance(exp_size, (int, float)) and exp_size and found_size_kb:
        res.size_ratio = round(found_size_kb / exp_size, 2)
        if res.size_ratio < 0.3 or res.size_ratio > 3.0:
            res.notes = "locus size far from reference — possible fragment or over-bounded boundary."

    frac = res.markers_present_of_expected
    size_ok = res.size_ratio is None or (SIZE_LO <= res.size_ratio <= SIZE_HI)
    res.size_ok = size_ok
    if frac is None:
        res.verdict = "EXPECTED_PENDING_LIT"
    elif frac >= CONCORDANT_MARKER_FRAC and size_ok:
        res.verdict = "CONCORDANT"
    elif frac > 0:
        res.verdict = "PARTIAL"
    else:
        res.verdict = "DISCORDANT"
        if not res.notes:
            res.notes = "anchor matches but no expected class markers present — treat anchor as similarity only."
    return res


def concordance_for_bgc(bgc, found_markers, library=None) -> ConcordanceResult:
    """Run concordance on a BGCRecord using the CORRECT anchor field.

    The anchor MUST be ``closest_candidate_kcb_product`` (the MIBiG reference product), NOT ``kcb_top``:
    for a cluster excised from a sequenced genome, kcb_top can be the genome self-hit (v9.7.22 surfaces the
    MIBiG line there too, but closest_candidate_kcb_product is the canonical product field). Reading kcb_top
    would make concordance return NO_REFERENCE for exactly the genome-derived clusters it is meant to help.
    This wrapper exists so callers cannot pick the wrong field when concordance is wired into the pipeline.
    """
    anchor = getattr(bgc, "closest_candidate_kcb_product", "") or ""
    size = None
    if getattr(bgc, "start", None) is not None and getattr(bgc, "end", None) is not None:
        size = round((bgc.end - bgc.start) / 1000, 1)
    return concordance_check(getattr(bgc, "bgc_id", "?"), anchor, found_markers, size, library)
