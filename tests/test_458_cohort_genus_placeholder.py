"""The engine's placeholder taxonomy `not verified` gives no genus in cohort assembly, not the genus "not"."""
from mamey.cohort_assemble import _genus_of


def test_placeholders_give_no_genus():
    for tax in ("not verified", "Not Verified", "unknown", "", None, "  "):
        assert _genus_of(tax) == ""


def test_real_taxonomy_gives_its_genus():
    assert _genus_of("Streptomyces sp.") == "Streptomyces"
    assert _genus_of("Notocardia example") == "Notocardia"
