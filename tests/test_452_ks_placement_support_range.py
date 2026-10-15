"""Only finite UFBoot values in 0..100 count as support; unreadable support is held (P300-092)."""
import pytest

from mamey import ks_phylogeny as kp


@pytest.mark.parametrize("label,expected", [
    ("100", 100.0), ("95.3/100", 100.0), ("80/0.9/95", 95.0), ("0", 0.0),
    ("inf", None), ("nan", None), ("150", None), ("-1", None), ("95/inf", None),
    ("abc/95", None), ("", None), ("95/", None),
])
def test_ufboot_admits_only_finite_values_in_range(label, expected):
    assert kp._ufboot(label) == expected


@pytest.mark.parametrize("support", ["inf", "150", "1e9"])
def test_out_of_range_support_does_not_place(support):
    tree = f"((q1:0.1,MIBiG__R_KS01:0.1){support}:0.2,x:0.1,y:0.1);"
    row = kp.place_on_reference_modules(tree)[0]
    assert row["verdict"] == kp.SUPPORT_UNVERIFIED and row["module"] == ""


def test_missing_support_is_held_not_unplaced():
    row = kp.place_on_reference_modules("((q1:0.1,MIBiG__R_KS01:0.1):0.2,x:0.1,y:0.1);")[0]
    assert row["verdict"] == kp.SUPPORT_UNVERIFIED


def test_known_values_keep_their_verdicts():
    weak = kp.place_on_reference_modules("((q1:0.1,MIBiG__R_KS01:0.1)30:0.2,x:0.1,y:0.1);")[0]
    assert weak["verdict"] == kp.UNPLACED
    placed = kp.place_on_reference_modules("((q1:0.1,MIBiG__R_KS01:0.1)80:0.2,x:0.1,y:0.1);")[0]
    assert (placed["verdict"], placed["module"], placed["support_ufboot"]) == (kp.PLACED, 1, 80.0)


def test_unreadable_branch_larger_than_the_supported_split_does_not_hold():
    tree = "(((q1:0.1,MIBiG__R_KS01:0.1)99:0.1,MIBiG__R_KS02:0.1):0.1,x:0.1,y:0.1);"
    row = kp.place_on_reference_modules(tree)[0]
    assert (row["verdict"], row["module"]) == (kp.PLACED, 1)
