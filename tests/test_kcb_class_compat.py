"""test_kcb_class_compat.py — v9.7.63

Tests for KCB class-compatibility mismatch detection (_check_kcb_class_compat).
Worst-list item 7: KCB anchors that are chemically incompatible with the BGC's
own antiSMASH product class were not auto-flagged. The new check catches these
as class-mismatch mis-anchors (suppresses anchor-derived credit).

All test cases calibrated from the 16-strain cohort empirical data.
"""
import pytest
from mamey.source_scans import _check_kcb_class_compat


# ── Helper ────────────────────────────────────────────────────────────────────

def _kcb(compound: str, bgc_acc: str = "BGC0000001.1") -> str:
    return f"{bgc_acc} | {compound} | knownclusterblast #1"


# ── True mismatches — should flag ─────────────────────────────────────────────

def test_kinamycin_on_ni_siderophore():
    """kinamycin (T2PKS aromatic polyketide) on NI-siderophore locus — mismatch.
    Confirmed in cohort: AS-XXX/AS-XXX/AS-XXX/AS-XXX/AS-XXX BGCs."""
    flag, reason = _check_kcb_class_compat(_kcb("kinamycin"), ["NI-siderophore", "other"])
    assert flag is True
    assert reason

def test_kinamycin_on_ni_siderophore_other():
    """NI-siderophore;other — kinamycin still flagged even with 'other' present."""
    flag, _ = _check_kcb_class_compat(_kcb("kinamycin"), ["NI-siderophore", "other", "saccharide"])
    assert flag is True

def test_prejadomycin_on_terpene():
    """prejadomycin (angucycline T2PKS) on terpene locus — mismatch.
    Confirmed: AS-XXX/AS-XXX/AS-XXX/AS-XXX/AS-XXX/AS-XXX BGCs."""
    flag, _ = _check_kcb_class_compat(
        "BGC0000262.5 | prejadomycin/rabelomycin/dehydrorabelomycin | knownclusterblast #1",
        ["terpene", "terpene-precursor"])
    assert flag is True

def test_rabelomycin_on_saccharide():
    """rabelomycin (angucycline T2PKS) on saccharide locus — mismatch.
    Caught via prejadomycin/rabelomycin pattern."""
    flag, _ = _check_kcb_class_compat(_kcb("rabelomycin/dehydrorabelomycin"), ["saccharide"])
    assert flag is True

def test_accramycin_on_saccharide():
    """accramycin A (anthracycline T2PKS) on saccharide/melanin locus — mismatch.
    Confirmed: AS-XXX/AS-XXX/AS-XXX/AS-XXX/AS-XXX BGCs."""
    flag, _ = _check_kcb_class_compat(
        "BGC0002315.2 | accramycin A | knownclusterblast #1",
        ["melanin", "other", "saccharide"])
    assert flag is True

def test_colibrimycin_on_halogenated_only():
    """colibrimycin (NRPS/PKS hybrid) on halogenated;other locus — mismatch.
    Confirmed: AS-XXX/AS-XXX/AS-XXX/AS-XXX/AS-XXX BGCs."""
    flag, _ = _check_kcb_class_compat(
        "BGC0002100.2 | colibrimycin | knownclusterblast #1",
        ["halogenated", "other"])
    assert flag is True

def test_cyphomycin_on_butyrolactone():
    """cyphomycin (T1PKS polyene) on butyrolactone locus — mismatch.
    Confirmed: AS-XXX/BGC066."""
    flag, _ = _check_kcb_class_compat(
        "BGC0001877.4 | cyphomycin | knownclusterblast #1",
        ["butyrolactone", "other"])
    assert flag is True

def test_difficidin_on_butyrolactone():
    """difficidin (NRPS/PKS macrolide) on butyrolactone locus — mismatch.
    Confirmed: AS-XXX/BGC005."""
    flag, _ = _check_kcb_class_compat(
        "BGC0000176.5 | difficidin | knownclusterblast #1",
        ["butyrolactone", "other"])
    assert flag is True

def test_zorbamycin_on_butyrolactone():
    """zorbamycin (NRPS glycopeptide) on butyrolactone locus — mismatch."""
    flag, _ = _check_kcb_class_compat(_kcb("zorbamycin"), ["butyrolactone", "other"])
    assert flag is True

def test_zorbamycin_on_terpene():
    """zorbamycin on terpene;saccharide locus — mismatch."""
    flag, _ = _check_kcb_class_compat(
        "BGC0001058.5 | zorbamycin | knownclusterblast #1",
        ["saccharide", "terpene"])
    assert flag is True

def test_showdomycin_on_butyrolactone():
    """showdomycin (nucleoside) on butyrolactone;ectoine locus — mismatch.
    Confirmed: AS-XXX/BGC025."""
    flag, _ = _check_kcb_class_compat(
        "BGC0001778.5 | showdomycin | knownclusterblast #1",
        ["butyrolactone", "ectoine", "other"])
    assert flag is True

def test_phosphonoglycans_on_saccharide_only():
    """phosphonoglycans on saccharide-only locus — mismatch (no phosphonate in products).
    Confirmed: AS-XXX/AS-XXX/AS-XXX/AS-XXX/AS-XXX/AS-XXX BGCs."""
    flag, _ = _check_kcb_class_compat(
        "BGC0000806.5 | phosphonoglycans | knownclusterblast #1",
        ["saccharide"])
    assert flag is True

def test_chlorizidine_on_fatty_acid():
    """chlorizidine A (NRPS-derived alkaloid) on fatty_acid;other locus — mismatch.
    Confirmed: AS-XXX/AS-XXX/AS-XXX/AS-XXX/AS-XXX BGCs."""
    flag, _ = _check_kcb_class_compat(
        "BGC0001172.5 | chlorizidine A | knownclusterblast #1",
        ["fatty_acid", "other"])
    assert flag is True

def test_methylenomycin_on_butyrolactone():
    """methylenomycin A (T1PKS) on butyrolactone locus — mismatch.
    Confirmed: AS-XXX/BGC011."""
    flag, _ = _check_kcb_class_compat(
        "BGC0000914.5 | methylenomycin A | knownclusterblast #1",
        ["butyrolactone", "other"])
    assert flag is True

def test_colabomycin_on_butyrolactone():
    """colabomycin E (aminoglycoside PKS) on butyrolactone locus — mismatch.
    Confirmed: AS-XXX/BGC023."""
    flag, _ = _check_kcb_class_compat(
        "BGC0000213.4 | colabomycin E | knownclusterblast #1",
        ["butyrolactone", "other"])
    assert flag is True


# ── True non-mismatches — should NOT flag ─────────────────────────────────────

def test_gamma_butyrolactone_on_butyrolactone():
    """γ-butyrolactone on butyrolactone locus — MATCH. Must not flag.
    AS-XXX/BGC013 confirmed correct anchor."""
    flag, _ = _check_kcb_class_compat(
        "BGC0000850.5 | γ-butyrolactone | knownclusterblast #1",
        ["butyrolactone", "other", "terpene"])
    assert flag is False

def test_phosphonoglycans_on_phosphonate_locus():
    """phosphonoglycans on phosphonate locus — MATCH. Must not flag.
    AS-XXX/BGC042 confirmed correct anchor."""
    flag, _ = _check_kcb_class_compat(
        "BGC0000806.5 | phosphonoglycans | knownclusterblast #1",
        ["other", "phosphonate"])
    assert flag is False

def test_kinamycin_on_t2pks_locus():
    """kinamycin on T2PKS locus — MATCH (correct class). Must not flag."""
    flag, _ = _check_kcb_class_compat(_kcb("kinamycin"), ["T2PKS", "other"])
    assert flag is False

def test_kinamycin_on_hr_t2pks_locus():
    """kinamycin on HR-T2PKS locus — MATCH. Must not flag."""
    flag, _ = _check_kcb_class_compat(_kcb("kinamycin"), ["hr-t2pks"])
    assert flag is False

def test_cyphomycin_on_t1pks_locus():
    """cyphomycin on T1PKS locus — MATCH. Must not flag."""
    flag, _ = _check_kcb_class_compat(_kcb("cyphomycin"), ["PKS", "T1PKS"])
    assert flag is False

def test_cyphomycin_on_nrps_pks_locus():
    """cyphomycin on NRPS;PKS;T1PKS locus — MATCH (PKS present). Must not flag."""
    flag, _ = _check_kcb_class_compat(_kcb("cyphomycin"), ["NRPS", "PKS", "T1PKS"])
    assert flag is False

def test_colibrimycin_on_nrps_locus():
    """colibrimycin on NRPS;PKS locus — MATCH. Must not flag."""
    flag, _ = _check_kcb_class_compat(_kcb("colibrimycin"), ["NRPS", "PKS"])
    assert flag is False

def test_no_kcb_anchor():
    """Empty KCB top — no anchor, no flag."""
    flag, _ = _check_kcb_class_compat("", ["NI-siderophore", "other"])
    assert flag is False

def test_genome_only_kcb():
    """KCB top is genome accession without BGC accession — compound name extracted
    from full string; should not fire unless a pattern matches the genome name."""
    flag, _ = _check_kcb_class_compat(
        "Streptomyces clavuligerus strain ATCC 27064 chromosome",
        ["NI-siderophore", "other"])
    assert flag is False

def test_unknown_compound_no_flag():
    """Compound not in the map — no flag. Conservative by design."""
    flag, _ = _check_kcb_class_compat(_kcb("streptolydigin"), ["terpene", "other"])
    assert flag is False


# ── AS-XXX audit regression pins ──────────────────────────────────────────────

def test_as902_bgc035_colibrimycin_mismatch():
    """AS-XXX BGC035: halogenated;other × colibrimycin — mismatch flagged."""
    flag, _ = _check_kcb_class_compat(
        "BGC0002100.2 | colibrimycin | knownclusterblast #1",
        ["halogenated", "other"])
    assert flag is True

def test_as902_bgc007_kinamycin_mismatch():
    """AS-XXX BGC007: NI-siderophore;other × kinamycin — mismatch flagged."""
    flag, _ = _check_kcb_class_compat(
        "BGC0000236.5 | kinamycin | knownclusterblast #1",
        ["NI-siderophore", "other"])
    assert flag is True

def test_as902_bgc039_phosphono_sacch_mismatch():
    """AS-XXX BGC039: saccharide × phosphonoglycans — mismatch flagged."""
    flag, _ = _check_kcb_class_compat(
        "BGC0000806.5 | phosphonoglycans | knownclusterblast #1",
        ["saccharide"])
    assert flag is True
