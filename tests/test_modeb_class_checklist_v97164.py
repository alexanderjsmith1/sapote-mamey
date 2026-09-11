"""test_modeb_class_checklist_v97164.py — class-triggered content expectations.

Derived from pre-program reference cards (thioamide + lasso class content). Validates that a
deep card addressing its class-specific biology passes, and a hollow card is flagged.
"""
import mamey.modeb_class_checklist as cc


def test_products_map_to_classes():
    assert "thioamide" in cc.classes_for_products("NRPS; thioamide-NRP")
    assert "nrps" in cc.classes_for_products("NRPS; thioamide-NRP")
    assert cc.classes_for_products("lassopeptide") == ["lassopeptide"]
    assert "metallophore" in cc.classes_for_products("NRP-metallophore+NRPS")


def test_hollow_card_flags_all_class_concepts():
    thin = "This is an NRPS cluster. It makes a peptide. Interesting lead."
    gaps = cc.check_class_content(thin, "NRPS; thioamide-NRP")
    concepts = {g["concept"] for g in gaps}
    # must flag the thioamide-specific expectations
    assert any("thioamidation cassette" in c for c in concepts)
    assert any("mass shift" in c for c in concepts)
    assert all(g["severity"] == "WARN" for g in gaps)
    assert all(g["code"] == "CONTENT_GAP" for g in gaps)


def test_thioamide_card_addressing_biology_passes():
    card = (
        "Thioamide capacity via a YcaO/TfuA thioamidation cassette. The O->S substitution "
        "gives a +15.977 Da diagnostic mass shift for LC-MS. Metallophore signal: DmdR/ZuR "
        "metal-limitation regulation, diaminopropionate (Dap) via SbnA/SbnB. Module "
        "architecture: nine condensation and one adenylation domain; Stachelhaus specificity "
        "code extraction predicts substrate; thioesterase release."
    )
    gaps = cc.check_class_content(card, "NRPS; thioamide-NRP")
    assert gaps == [], f"unexpected gaps: {[g['concept'] for g in gaps]}"


def test_lasso_card_expectations():
    hollow = "A lassopeptide cluster with a small maturation cassette."
    gaps = cc.check_class_content(hollow, "lassopeptide")
    concepts = {g["concept"] for g in gaps}
    assert any("precursor" in c.lower() for c in concepts)
    assert any("protease" in c.lower() or "b protease" in c.lower() for c in concepts)

    good = (
        "Lasso precursor A peptide with leader + core split. Lasso B protease removes the "
        "leader; lasso C lactam synthetase forms the isopeptide macrolactam. An RRE "
        "recognition element mediates threading; asparagine synthase B-protein present."
    )
    assert cc.check_class_content(good, "lassopeptide") == []


def test_non_matching_class_no_gaps():
    # a product with no checklist key yields no gaps (nothing to check)
    assert cc.check_class_content("some prose", "unknown-class-xyz") == []
