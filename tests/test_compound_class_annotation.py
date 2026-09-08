"""Regression tests for the v9.7.86 compound-class annotation layer.

Pins the chemotype calibration against the 32-MIBiG-reference set assembled 2026-06-19.
These tests do NOT require the reference zips: they exercise annotate_bgc() with
synthetic BGCRecord stand-ins carrying the same own-evidence (resolved product line /
products) and antiSMASH product_classes the real clusters produced, so the calibration
is locked without shipping reference data.
"""
from __future__ import annotations

import pytest

from mamey.compound_class import (
    annotate_bgc,
    CHEMOTYPES,
    PH_ANTIFUNGAL,
    PH_CYTOTOXIC,
)


class _FakeBGC:
    def __init__(self, products=None, resolved="UNRESOLVED", mibig_hits=None):
        self.products = products or []
        self.closest_candidate_kcb_product = resolved
        self.mibig_hits = mibig_hits or []
        self.kcb_top = None
        self.contig = "NODE_1"


def _ann(products=None, resolved="UNRESOLVED", antismash_classes=None):
    bgc = _FakeBGC(products=products, resolved=resolved)
    preds = [{"record_id": "NODE_1", "product_classes": antismash_classes or []}]
    return annotate_bgc(bgc, preds)


# ---- scored positives ------------------------------------------------------
@pytest.mark.parametrize("resolved", ["meilingmycin", "salinilactam", "nystatin A1"])
def test_polyene_macrolide_scores_antifungal(resolved):
    a = _ann(products=["PKS", "T1PKS"], resolved=resolved)
    assert a.chemotype == "polyene_macrolide"
    assert a.scored_axis == "af" and a.scored_weight > 0
    assert a.pharmacology == PH_ANTIFUNGAL


@pytest.mark.parametrize("resolved", ["doxorubicin", "daunorubicin", "cosmomycin B",
                                      "cinerubin B", "elloramycin", "medermycin"])
def test_anthracycline_is_own_cytotoxic_category(resolved):
    a = _ann(products=["PKS", "T2PKS"], resolved=resolved)
    assert a.chemotype == "anthracycline"
    assert a.scored_axis == "anthracycline"     # own category, not ab/af
    assert a.cytotoxic_flag is True
    assert a.pharmacology == PH_CYTOTOXIC


def test_anthracycline_from_antismash_t2pks_prediction():
    # doxorubicin cluster with UNRESOLVED name but antiSMASH predicts the class
    a = _ann(products=["PKS", "T2PKS"], resolved="UNRESOLVED",
             antismash_classes=["angucycline", "aureolic acid", "tetracycline", "anthracycline"])
    assert a.chemotype == "anthracycline"
    assert a.evidence_source == "antismash_t2pks"


def test_ionophore_scores_antibacterial_not_antifungal():
    a = _ann(products=["PKS", "T1PKS"], resolved="nanchangmycin")
    assert a.chemotype == "ionophore"
    assert a.scored_axis == "ab"            # AB, never AF
    assert a.single_reference is True       # flagged single-reference


# ---- specific resolved name beats antiSMASH multi-class set ----------------
def test_tetracycline_name_beats_antismash_anthracycline_in_list():
    # tetracycline clusters list 'anthracycline' among antiSMASH product_classes;
    # the specific resolved name must win.
    a = _ann(products=["PKS", "T2PKS"], resolved="chlortetracycline",
             antismash_classes=["anthracycline", "tetracycline", "angucycline"])
    assert a.chemotype == "tetracycline"


@pytest.mark.parametrize("resolved", ["kinamycin", "lomaiviticin A"])
def test_diazofluorene_name_beats_antismash_class(resolved):
    a = _ann(products=["PKS", "T2PKS"], resolved=resolved,
             antismash_classes=["angucycline", "anthracycline"])
    assert a.chemotype == "diazofluorene"
    assert a.cytotoxic_flag is True
    assert a.scored_axis == ""              # annotate-only, not scored


# ---- annotate-only chemotypes (recorded, not scored) -----------------------
@pytest.mark.parametrize("resolved,expected", [
    ("frenolicin B", "pyranonaphthoquinone"),
    ("enterocin", "pyranonaphthoquinone"),
    ("rabelomycin", "angucycline"),
    ("rubradirin", "ansamycin"),
    ("spinosyn D", "macrolide_other"),
])
def test_annotate_only_chemotypes(resolved, expected):
    a = _ann(products=["PKS", "T2PKS"], resolved=resolved)
    assert a.chemotype == expected
    assert a.scored_axis == ""             # recorded, no score consequence


# ---- negatives must NOT move -----------------------------------------------
@pytest.mark.parametrize("resolved", ["marineosin A", "tautomycetin",
                                      "yanuthone D", "solanapyrone D"])
def test_negatives_unclassified(resolved):
    a = _ann(products=["PKS", "T1PKS"], resolved=resolved)
    assert a.chemotype == ""
    assert a.scored_axis == ""


# ---- arylpolyene pigment trap ----------------------------------------------
def test_arylpolyene_is_not_polyene_macrolide():
    a = _ann(products=["arylpolyene"], resolved="UNRESOLVED")
    assert a.chemotype != "polyene_macrolide"
    a2 = _ann(products=["arylpolyene", "polyene"], resolved="arylpolyene pigment")
    assert a2.chemotype != "polyene_macrolide"


# ---- never reads raw kcb_top (P-7 preservation) ----------------------------
def test_annotation_ignores_raw_kcb_top():
    # a genome-self-hit naming an anthracycline in kcb_top must NOT classify the BGC
    bgc = _FakeBGC(products=["NRPS"], resolved="UNRESOLVED")
    bgc.kcb_top = "Streptomyces sp. | Type: doxorubicin anthracycline | genome self-hit"
    a = annotate_bgc(bgc, None)
    assert a.chemotype == ""    # raw kcb_top is never consulted


# ---- taxonomy integrity ----------------------------------------------------
def test_only_three_scored_chemotypes():
    scored = [c.name for c in CHEMOTYPES if c.scored is not None]
    assert set(scored) == {"polyene_macrolide", "anthracycline", "ionophore"}


# ---- broadened annotate-only families (confidence-flagged) -----------------
@pytest.mark.parametrize("resolved,expected", [
    ("balhimycin", "glycopeptide"),
    ("vancomycin", "glycopeptide"),
    ("endophenazine A", "phenazine"),
    ("caprazamycin", "nucleoside_antibiotic"),
    ("pentabromopseudilin", "halogenated_phenolic"),
    ("xiamenmycin", "prenylated_indole"),
    ("borrelidin", "macrolide_other"),
    ("alnumycin", "pyranonaphthoquinone"),
])
def test_broadened_families_are_annotate_only(resolved, expected):
    a = _ann(products=["NRPS", "PKS"], resolved=resolved)
    assert a.chemotype == expected
    assert a.scored_axis == ""          # broadened families are never scored


def test_new_families_are_low_confidence():
    # 1-reference labels carry LOW confidence so they're not read as solid as anthracycline
    for resolved in ["balhimycin", "endophenazine A", "caprazamycin",
                     "pentabromopseudilin", "xiamenmycin"]:
        a = _ann(products=["NRPS", "PKS"], resolved=resolved)
        assert a.confidence == "LOW"


def test_anthracycline_is_high_confidence():
    a = _ann(products=["PKS", "T2PKS"], resolved="doxorubicin")
    assert a.confidence == "HIGH"


# ---- non-lead exclusions (pigments, fungal toxins, primary metabolites) ----
@pytest.mark.parametrize("resolved", ["spore pigment", "patulin",
                                      "solanapyrone D", "eicosapentaenoic acid"])
def test_nonlead_exclusions_abstain(resolved):
    a = _ann(products=["PKS", "T2PKS"], resolved=resolved)
    assert a.chemotype == ""           # pigments / toxins / primary metabolites abstain


def test_antismash_class_only_downgrades_confidence():
    # an anthracycline called ONLY from the antiSMASH class list (no specific name)
    # is one confidence step below a name-confirmed HIGH call
    a = _ann(products=["PKS", "T2PKS"], resolved="UNRESOLVED",
             antismash_classes=["anthracycline", "tetracycline"])
    assert a.chemotype == "anthracycline"
    assert a.confidence == "MODERATE"   # downgraded from HIGH
