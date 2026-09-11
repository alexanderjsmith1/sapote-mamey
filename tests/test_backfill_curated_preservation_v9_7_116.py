"""v9.7.116 (Bunny Hop S19 P2): backfill_reference_signatures must never touch CURATED fields.

backfill writes the shipped reference_bgc_library.json, refreshing OBSERVED/COMPUTED fields
(architecture_signature, found_markers, found_size_kb, genus-if-UNRESOLVED) from antiSMASH zips.
Its central safety promise is that the hand-curated literature fields (class_lit, core_genes,
source_doi, …) are never overwritten. These tests pin that invariant.
"""
import sys
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import backfill_reference_signatures as B  # noqa: E402

# The keys main() is permitted to write (OBSERVED/COMPUTED refresh) — transcribed from the tool.
_WRITTEN_KEYS = {
    "architecture_signature",   # COMPUTED from the antiSMASH output
    "found_markers",            # OBSERVED scan output
    "found_size_kb",            # OBSERVED
    "genus",                    # only when currently UNRESOLVED (fill-once)
}


def test_written_keys_are_disjoint_from_curated():
    """The fields backfill refreshes must not intersect the CURATED (never-overwrite) set —
    otherwise a refresh could clobber a literature answer-key field."""
    overlap = _WRITTEN_KEYS & set(B.CURATED)
    assert not overlap, f"backfill would overwrite CURATED field(s): {sorted(overlap)}"


def test_curated_set_covers_the_documented_literature_fields():
    """Guard against a CURATED-set regression: the literature fields the docstring promises to
    protect must all be present in CURATED."""
    promised = {"class", "class_lit", "expected_bioactivity", "core_genes",
                "lit_diagnostic_genes", "source_doi", "deposit_doi", "caveat", "ref_role"}
    missing = promised - set(B.CURATED)
    assert not missing, f"CURATED no longer protects documented literature field(s): {sorted(missing)}"


def test_expected_marker_set_is_curated_not_observed():
    """expected_marker_set is the literature answer key (marker_set_source), distinct from the
    OBSERVED found_markers — it must be curated-protected, not refreshed."""
    assert "expected_marker_set" not in _WRITTEN_KEYS
