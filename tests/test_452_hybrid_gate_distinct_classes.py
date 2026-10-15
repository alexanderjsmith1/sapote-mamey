"""The chemical_hybrid coherence gate counts distinct classes, not matched keywords (P300-126)."""
import pytest

from mamey.parsers import architecture_grade

_COMPACT = 8000      # Interior, core present, below the 10 kb "A" length


def _grade(products, hybrid=True, edge="Interior"):
    return architecture_grade(edge, products, _COMPACT, has_chemical_hybrid=hybrid)


@pytest.mark.parametrize("products", [
    ["lanthipeptide-class-i", "RiPP-like"],          # two RiPP types: one class
    ["azole-containing-RiPP", "RiPP-like"],           # "azole" and "ripp" in one product label
    ["lassopeptide", "RiPP-like"],
    ["NRPS", "NRP-metallophore"],                     # one NRPS class
    ["NRPS", "thioamide-NRP"],
    ["T1PKS", "transAT-PKS"],
])
def test_same_class_hybrid_is_not_promoted(products):
    grade, rationale = _grade(products)
    assert grade == "B"
    assert "chemical_hybrid" not in rationale


@pytest.mark.parametrize("products", [
    ["NRPS", "T1PKS"],
    ["lanthipeptide-class-i", "terpene"],
    ["T1PKS", "oligosaccharide"],
    ["NI-siderophore", "NRPS"],
    ["phosphonate", "NI-siderophore"],                # two distinct antiSMASH "other" types
])
def test_true_two_class_hybrid_is_still_promoted(products):
    grade, rationale = _grade(products)
    assert grade == "A"
    assert "chemical_hybrid" in rationale


def test_non_core_product_does_not_count_as_a_second_class():
    assert _grade(["NRPS", "ectoine"])[0] == "B"


def test_truncation_grades_and_rationale_note_follow_the_same_count():
    grade, rationale = _grade(["lanthipeptide-class-i", "RiPP-like"], edge="Edge")
    assert grade == "C" and "chemical_hybrid" not in rationale
    grade, rationale = _grade(["lanthipeptide-class-i", "terpene"], edge="Edge")
    assert grade == "C" and "chemical_hybrid" in rationale


def test_without_hybrid_flag_nothing_changes():
    assert _grade(["NRPS", "T1PKS"], hybrid=False)[0] == "B"
    assert _grade(["lanthipeptide-class-i", "RiPP-like"], hybrid=False)[0] == "B"
