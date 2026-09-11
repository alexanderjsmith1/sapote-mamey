"""Regression test — v97396: comparator_evidence.py's coverage_state() treats a NaN sentinel as
a valid, in-range coverage percentage.

The module's own docstring: "The adapter is deliberately sequence-first and fail-closed." Its
`coverage_state()` already carries one documented fix for exactly this failure shape (see the
comment on `read_comparator_source()`: a malformed row "slipped past this guard, despite the
module's fail-closed design intent"). This is a second instance of the same shape: `float("nan")`
succeeds (Python accepts the string "nan"), but every comparison against NaN is False under IEEE
754 semantics, so BOTH the `value > 100` and `value < 0` guards silently fail to catch it — a
non-numeric sentinel is classified as "WITHIN_EXPECTED_RANGE_SOURCE_REPORTED", the same bucket as
a genuinely valid percentage. `inf`/`-inf` are correctly caught by the existing guards (this is
NOT a general non-finite-value gap, specifically a NaN one).
"""
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from mamey.comparator_evidence import coverage_state


def test_nan_is_held_not_reported_as_within_range_v97396():
    usable, state = coverage_state("nan")
    assert usable == "", "a NaN sentinel must not be reported as a usable coverage value"
    assert state != "WITHIN_EXPECTED_RANGE_SOURCE_REPORTED"


def test_nan_case_variants_are_also_held_v97396():
    for raw in ("nan", "NaN", "NAN", "-nan"):
        usable, state = coverage_state(raw)
        assert usable == "", f"{raw!r} must be held, not reported as in-range"
        assert state != "WITHIN_EXPECTED_RANGE_SOURCE_REPORTED"


def test_infinity_still_correctly_held_no_regression_v97396():
    usable, state = coverage_state("inf")
    assert usable == ""
    assert state == "SOURCE_GT100_HOLD_DENOMINATOR_OR_HSP_AGGREGATE_UNRESOLVED"
    usable, state = coverage_state("-inf")
    assert usable == ""
    assert state == "COVERAGE_NEGATIVE_INVALID"


def test_genuine_in_range_value_still_passes_no_regression_v97396():
    usable, state = coverage_state("95.5")
    assert usable == "95.5"
    assert state == "WITHIN_EXPECTED_RANGE_SOURCE_REPORTED"
