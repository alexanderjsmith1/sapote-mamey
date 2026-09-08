"""Regression test for Workstream A — provenance-aware claim-safe KCB display."""
from mamey.render_safe import safe_kcb_display


def test_resolved_mibig_shows_identity_with_similarity_qualifier():
    out = safe_kcb_display({"closest_product_provenance": "MIBIG_REFERENCE_LINE",
                            "kcb_top": "BGC0001234 | nikkomycin | knownclusterblast #1"})
    assert "(similarity)" in out and "nikkomycin" in out


def test_raw_self_hit_is_qualified_not_identity():
    out = safe_kcb_display({"closest_product_provenance": "KCB_TOP_FIELD",
                            "kcb_top": "NODE_5_self_hit", "closest_candidate_kcb_product": "UNRESOLVED"})
    assert "not product identity" in out
    assert out.startswith("~")


def test_safe_surface_preferred_when_present():
    out = safe_kcb_display({"closest_candidate_kcb_product": "streptomycin", "kcb_top": "raw"})
    assert "streptomycin" in out and "similarity anchor only" in out


def test_unresolved_when_empty():
    assert safe_kcb_display({}) == "unresolved"


def test_never_emits_bare_raw_kcb_top():
    # a raw self-hit must never come back without a qualifier
    out = safe_kcb_display({"kcb_top": "some_raw_genome_line", "closest_product_provenance": "KCB_TOP_FIELD"})
    assert out != "some_raw_genome_line"
    assert "similarity" in out or "not product identity" in out
