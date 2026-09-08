"""Tests for RG-GMCI R1/R2/R3 gate rules (v9.7.61).

R1: both-DROP-class pair suppression  
R2: strong_refs >= 1 co-requirement for HIGH
R3: noise-class-only cap
"""
import pytest
from mamey.rggmci import (
    _r1_drop_pair_gate, _r2_strong_ref_gate, _r3_noise_class_gate,
    _is_drop_only, _is_noise_only,
)

# _is_drop_only
def test_drop_only_hgle_pks(): assert _is_drop_only("PKS; hglE-KS") is True
def test_drop_only_saccharide(): assert _is_drop_only("saccharide") is True
def test_drop_only_napaa(): assert _is_drop_only("NAPAA") is True
def test_drop_only_t1pks_not_drop(): assert _is_drop_only("PKS; T1PKS") is False
def test_drop_only_nrps_hgle_not_drop(): assert _is_drop_only("NRPS; PKS; hglE-KS") is False
def test_drop_only_empty(): assert _is_drop_only("") is False

# _is_noise_only
def test_noise_fatty_other(): assert _is_noise_only("fatty_acid; other") is True
def test_noise_other(): assert _is_noise_only("other") is True
def test_noise_t1pks_not_noise(): assert _is_noise_only("PKS; T1PKS") is False
def test_noise_nrps_not_noise(): assert _is_noise_only("NRPS; fatty_acid") is False
def test_noise_hgle_alone(): assert _is_noise_only("hglE-KS") is True
def test_noise_pks_not_noise(): assert _is_noise_only("PKS; hglE-KS") is False

# R1 gate
def test_r1_hgle_hgle_demoted():
    c, g = _r1_drop_pair_gate("HIGH_RG_GMCI_RESCUE", "PKS; hglE-KS", "PKS; hglE-KS")
    assert c == "MODERATE_RG_GMCI_CANDIDATE" and "R1" in g

def test_r1_sacch_sacch_demoted():
    c, _ = _r1_drop_pair_gate("HIGH_RG_GMCI_RESCUE", "saccharide", "saccharide")
    assert c == "MODERATE_RG_GMCI_CANDIDATE"

def test_r1_one_side_committed_preserved():
    c, g = _r1_drop_pair_gate("HIGH_RG_GMCI_RESCUE", "PKS; hglE-KS", "NRPS; PKS")
    assert c == "HIGH_RG_GMCI_RESCUE" and g == "OK"

def test_r1_nrps_pks_preserved():
    c, _ = _r1_drop_pair_gate("HIGH_RG_GMCI_RESCUE", "NRPS; PKS", "NRPS; T1PKS")
    assert c == "HIGH_RG_GMCI_RESCUE"

def test_r1_moderate_unchanged():
    c, g = _r1_drop_pair_gate("MODERATE_RG_GMCI_CANDIDATE", "PKS; hglE-KS", "PKS; hglE-KS")
    assert c == "MODERATE_RG_GMCI_CANDIDATE" and g == "OK"

def test_r1_low_unchanged():
    c, _ = _r1_drop_pair_gate("LOW_SHARED_REFERENCE_SIGNAL", "saccharide", "saccharide")
    assert c == "LOW_SHARED_REFERENCE_SIGNAL"

# R2 gate
def test_r2_sr0_demoted():
    c, g = _r2_strong_ref_gate("HIGH_RG_GMCI_RESCUE", 0)
    assert c == "MODERATE_RG_GMCI_CANDIDATE" and "R2" in g

def test_r2_sr1_preserved():
    c, g = _r2_strong_ref_gate("HIGH_RG_GMCI_RESCUE", 1)
    assert c == "HIGH_RG_GMCI_RESCUE" and g == "OK"

def test_r2_sr17_preserved():
    c, _ = _r2_strong_ref_gate("HIGH_RG_GMCI_RESCUE", 17)
    assert c == "HIGH_RG_GMCI_RESCUE"

def test_r2_moderate_sr0_unchanged():
    c, g = _r2_strong_ref_gate("MODERATE_RG_GMCI_CANDIDATE", 0)
    assert c == "MODERATE_RG_GMCI_CANDIDATE" and g == "OK"

# R3 gate
def test_r3_fatty_other_both_demoted():
    c, g = _r3_noise_class_gate("HIGH_RG_GMCI_RESCUE", "fatty_acid; other", "fatty_acid; other")
    assert c == "MODERATE_RG_GMCI_CANDIDATE" and "R3" in g

def test_r3_other_other_demoted():
    c, _ = _r3_noise_class_gate("HIGH_RG_GMCI_RESCUE", "other", "other")
    assert c == "MODERATE_RG_GMCI_CANDIDATE"

def test_r3_one_side_nrps_preserved():
    c, g = _r3_noise_class_gate("HIGH_RG_GMCI_RESCUE", "NRPS; fatty_acid", "fatty_acid; other")
    assert c == "HIGH_RG_GMCI_RESCUE" and g == "OK"

def test_r3_betalactone_not_noise():
    # betalactone is a specialist class - TRUE POSITIVE in AS-XXX
    c, _ = _r3_noise_class_gate("HIGH_RG_GMCI_RESCUE", "betalactone; other", "betalactone; other")
    assert c == "HIGH_RG_GMCI_RESCUE"

def test_r3_ni_siderophore_not_noise():
    # NI-siderophore preserved - AS-XXX BGC033xBGC055 TRUE POSITIVE
    c, _ = _r3_noise_class_gate("HIGH_RG_GMCI_RESCUE", "NI-siderophore; other", "NI-siderophore; other")
    assert c == "HIGH_RG_GMCI_RESCUE"

def test_r3_moderate_unchanged():
    c, g = _r3_noise_class_gate("MODERATE_RG_GMCI_CANDIDATE", "fatty_acid; other", "fatty_acid; other")
    assert c == "MODERATE_RG_GMCI_CANDIDATE" and g == "OK"

# True-positive preservation (16-strain calibration anchors)
def test_tp_bottromycin():
    "AS-XXX bottromycin RiPP split - must survive all three gates"
    r1c, _ = _r1_drop_pair_gate("HIGH_RG_GMCI_RESCUE", "RiPP; RiPP-like; bottromycin", "RRE-containing; RiPP")
    r2c, _ = _r2_strong_ref_gate("HIGH_RG_GMCI_RESCUE", 9)
    r3c, _ = _r3_noise_class_gate("HIGH_RG_GMCI_RESCUE", "RiPP; RiPP-like; bottromycin", "RRE-containing; RiPP")
    assert all(c == "HIGH_RG_GMCI_RESCUE" for c in [r1c, r2c, r3c])

def test_tp_desferrioxamine():
    "AS-XXX BGC033xBGC055 desferrioxamine - sr=17, NI-siderophore NOT noise"
    r1c, _ = _r1_drop_pair_gate("HIGH_RG_GMCI_RESCUE", "NI-siderophore; other", "NI-siderophore; other")
    r2c, _ = _r2_strong_ref_gate("HIGH_RG_GMCI_RESCUE", 17)
    r3c, _ = _r3_noise_class_gate("HIGH_RG_GMCI_RESCUE", "NI-siderophore; other", "NI-siderophore; other")
    assert r1c == r2c == r3c == "HIGH_RG_GMCI_RESCUE"

def test_tp_betalactone_pair():
    "AS-XXX BGC010xBGC023 betalactone - sr=17, must not be R3-demoted"
    c, _ = _r3_noise_class_gate("HIGH_RG_GMCI_RESCUE", "betalactone; other", "betalactone; other")
    assert c == "HIGH_RG_GMCI_RESCUE"

# Calibration-identified demotion targets
def test_r1_as365_hgle_pair():
    "AS-XXX BGC031xBGC034 hglE-KS x hglE-KS - R1 target"
    c, _ = _r1_drop_pair_gate("HIGH_RG_GMCI_RESCUE", "PKS; hglE-KS", "PKS; hglE-KS")
    assert c == "MODERATE_RG_GMCI_CANDIDATE"

def test_r2_sr0_as902_metallophore():
    "AS-XXX BGC016xBGC028 sr=0, gr=2 - R2 target"
    c, _ = _r2_strong_ref_gate("HIGH_RG_GMCI_RESCUE", 0)
    assert c == "MODERATE_RG_GMCI_CANDIDATE"

def test_r3_as815_fatty_acid_pairs():
    "AS-XXX fatty_acid x fatty_acid pairs - R3 target"
    c, _ = _r3_noise_class_gate("HIGH_RG_GMCI_RESCUE", "fatty_acid; other", "fatty_acid; other")
    assert c == "MODERATE_RG_GMCI_CANDIDATE"


# IDC pair (AS-XXX BGC001xBGC013) regression pin
def test_idc_pair_survives_all_gates():
    """AS-XXX BGC001xBGC013 indolocarbazole split (halogenated;other;saccharide x indole;other)
    must survive R1, R2, and R3. halogenated and indole are not noise tokens.
    This is the primary IDC recall case from the 16-strain calibration."""
    pa = "halogenated; other; saccharide"
    pb = "indole; other"
    sr = 2  # exact calibration value

    c = "HIGH_RG_GMCI_RESCUE"
    c, g = _r1_drop_pair_gate(c, pa, pb)
    assert c == "HIGH_RG_GMCI_RESCUE", f"R1 incorrectly demoted IDC pair: {g}"
    c, g = _r2_strong_ref_gate(c, sr)
    assert c == "HIGH_RG_GMCI_RESCUE", f"R2 incorrectly demoted IDC pair (sr={sr}): {g}"
    c, g = _r3_noise_class_gate(c, pa, pb)
    assert c == "HIGH_RG_GMCI_RESCUE", f"R3 incorrectly demoted IDC pair: {g}"

def test_halogenated_not_noise():
    """halogenated is a specialist class — must not be treated as noise."""
    assert not _is_noise_only("halogenated; other; saccharide")
    assert not _is_noise_only("halogenated; other")

def test_indole_not_noise():
    """indole is a specialist class — must not be treated as noise."""
    assert not _is_noise_only("indole; other")
    assert not _is_noise_only("indole")
