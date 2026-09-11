"""Regression tests for the v1.9.99 CCTT triggers: T43-PYE (polyene→AF),
T43-GPA (glycopeptide→AB), T43-BLT (betalactone→AB).

Audit focus: each new trigger must (1) fire on a genuine positive, (2) NOT fire on
its documented cross-reactor, (3) be correctly axis-assigned, and (4) for T43-PYE,
respect the ks_domain_count>=4 architecture gate that keeps it consistent with the
polyene mis-anchor guard.
"""
import re
from mamey.source_scans import CCTT_PATTERNS, CCTT_CLASS_COMPAT, cctt_trigger_corroborated
from mamey.scoring import AF_DIAGNOSTIC_TRIGGERS, AB_DIAGNOSTIC_TRIGGERS


def _fires(trigger_key, text):
    """True if any pattern for trigger_key matches text (case-insensitive)."""
    pats = CCTT_PATTERNS[trigger_key]
    return any(re.search(p, text, re.I) for p in pats)


# ── registration / axis assignment ──────────────────────────────────────────

def test_three_new_triggers_registered():
    assert "T43-PYE_polyene_macrolide" in CCTT_PATTERNS
    assert "T43-GPA_glycopeptide" in CCTT_PATTERNS
    assert "T43-BLT_betalactone" in CCTT_PATTERNS
    assert len(CCTT_PATTERNS) == 18


def test_pye_is_antifungal_axis():
    assert any("T43-PYE" in t for t in AF_DIAGNOSTIC_TRIGGERS)
    assert not any("T43-PYE" in t for t in AB_DIAGNOSTIC_TRIGGERS)


def test_gpa_blt_are_antibacterial_axis():
    assert any("T43-GPA" in t for t in AB_DIAGNOSTIC_TRIGGERS)
    assert any("T43-BLT" in t for t in AB_DIAGNOSTIC_TRIGGERS)
    assert not any("T43-GPA" in t for t in AF_DIAGNOSTIC_TRIGGERS)
    assert not any("T43-BLT" in t for t in AF_DIAGNOSTIC_TRIGGERS)


# ── T43-PYE: polyene ─────────────────────────────────────────────────────────

def test_pye_fires_on_genuine_polyene_names():
    for name in ("nystatin", "amphotericin B", "candicidin", "pimaricin",
                 "natamycin", "polyene macrolide", "a heptaene macrolide"):
        assert _fires("T43-PYE_polyene_macrolide", name), name


def test_pye_excludes_arylpolyene_pigment():
    # the canonical false positive — arylpolyene is an orange pigment, not antifungal
    assert not _fires("T43-PYE_polyene_macrolide", "arylpolyene")
    assert not _fires("T43-PYE_polyene_macrolide", "arylpolyene biosynthesis cluster")


def test_pye_excludes_ionophore_and_other_macrolide():
    for name in ("monensin", "salinomycin", "lasalocid", "nigericin",   # ionophores -> AB elsewhere
                 "erythromycin", "tylosin", "spiramycin", "spinosyn"):   # macrolide_other -> unscored
        assert not _fires("T43-PYE_polyene_macrolide", name), name


def test_pye_corroborated_by_pks_class():
    assert cctt_trigger_corroborated("T43-PYE_polyene_macrolide", ["T1PKS"])
    assert cctt_trigger_corroborated("T43-PYE_polyene_macrolide", ["transAT-PKS"])
    # not corroborated by an unrelated class
    assert not cctt_trigger_corroborated("T43-PYE_polyene_macrolide", ["terpene"])


# ── T43-GPA: glycopeptide ────────────────────────────────────────────────────

def test_gpa_fires_on_committed_markers_and_names():
    for txt in ("OxyB oxidative coupling P450", "DPGS dehydrogenase",
                "3,5-dihydroxyphenylglycine synthase", "vancomycin aglycone",
                "teicoplanin biosynthesis", "balhimycin", "pekiskomycin"):
        assert _fires("T43-GPA_glycopeptide", txt), txt


def test_gpa_does_not_fire_on_bare_glycosyltransferase():
    # a lone GT in a saccharide cluster must NOT read as glycopeptide
    assert not _fires("T43-GPA_glycopeptide", "glycosyltransferase family 1")
    assert not _fires("T43-GPA_glycopeptide", "sugar biosynthesis dTDP-glucose")


def test_gpa_corroboration_rejects_saccharide_only():
    assert cctt_trigger_corroborated("T43-GPA_glycopeptide", ["NRPS"])
    assert not cctt_trigger_corroborated("T43-GPA_glycopeptide", ["saccharide"])


# ── T43-BLT: betalactone ─────────────────────────────────────────────────────

def test_blt_fires_on_betalactone_and_named_compounds():
    for txt in ("betalactone", "beta-lactone synthase", "salinosporamide A",
                "platensimycin", "platencin", "lactacystin"):
        assert _fires("T43-BLT_betalactone", txt), txt


def test_blt_does_not_fire_on_primary_biotin_carboxylase():
    # biotin carboxylase ALONE is primary metabolism — must not fire without the PEP-utilizer pair
    assert not _fires("T43-BLT_betalactone", "biotin carboxylase subunit")
    assert not _fires("T43-BLT_betalactone", "acetyl-CoA carboxylase")


def test_blt_corroborated_by_betalactone_class():
    assert cctt_trigger_corroborated("T43-BLT_betalactone", ["betalactone"])
    assert not cctt_trigger_corroborated("T43-BLT_betalactone", ["terpene"])
