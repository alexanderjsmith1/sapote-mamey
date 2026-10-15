"""An empty or incomplete chitin count set is not reported as observed absence."""
import pytest
from mamey import chitin_reference_eval as mod


def test_empty_counts_are_incomplete_not_absent():
    p = mod.architecture_profile("SYN-401", {})
    assert p.architecture_state == "CHITIN_SCAN_INCOMPLETE_NOT_ABSENCE"
    assert set(p.missing_families) == set(mod.CHITIN_FAMILIES)
    assert p.to_dict()["missing_families"]


def test_partial_zero_counts_are_incomplete():
    p = mod.architecture_profile("SYN-402", {"GH18": 0, "GH19": 0})
    assert p.architecture_state == "CHITIN_SCAN_INCOMPLETE_NOT_ABSENCE"


def test_complete_zero_counts_are_absent():
    p = mod.architecture_profile("SYN-403", {f: 0 for f in mod.CHITIN_FAMILIES})
    assert p.architecture_state == "ABSENT_NO_MEASURED_CHITIN_DOMAINS"
    assert p.missing_families == ()


def test_positive_partial_counts_keep_their_state_and_record_missing():
    p = mod.architecture_profile("SYN-404", {"GH19": 3})
    assert p.architecture_state == "CHITINASE_FAMILY_CAPACITY_WITHOUT_SUPPORTING_ARMS"
    assert "GH18" in p.missing_families


@pytest.mark.parametrize("bad", [True, 2.5])
def test_bool_and_fractional_counts_are_refused(bad):
    with pytest.raises(mod.ChitinReferenceEvalError):
        mod.architecture_profile("SYN-405", {"GH18": bad})


def test_integral_float_is_accepted():
    assert mod.architecture_profile("SYN-406", {f: 0 for f in mod.CHITIN_FAMILIES} | {"GH18": 2.0}).counts["GH18"] == 2
