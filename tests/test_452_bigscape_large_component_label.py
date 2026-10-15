"""A large BiG-SCAPE component is labelled by its size; no assembly cause is drawn."""
import inspect
from mamey import bigscape_figures as bf


def test_large_component_is_labelled_by_size_only():
    cat, colour, label = bf._family_category(150, 0, "#123456")
    assert cat == "large-component"
    assert "150 records" in label
    assert "artifact" not in label.lower() and "fragment" not in label.lower()


def test_threshold_and_other_categories_are_unchanged():
    assert bf._family_category(120, 0, "#123456")[0] == "cohort-shared"
    assert bf._family_category(121, 3, "#123456")[0] == "large-component"
    assert bf._family_category(10, 2, "#123456") == ("mibig-anchored", "#123456", "MIBiG-anchored family")


def test_legend_says_the_cause_is_not_tested():
    assert "cause not tested" in bf.LARGE_COMPONENT_LEGEND
    assert "assembly artifact" not in inspect.getsource(bf)
