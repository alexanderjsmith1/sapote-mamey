"""The shared missing-value rule: placeholders stay missing, and two missing values never match."""
import math

import pytest

from mamey.missing_values import display, is_missing, optional_float, optional_int, optional_text, same_identity


@pytest.mark.parametrize("value", [None, "", "  ", "NA", "n/a", "N/A", "nan", "NaN", "None", "null", "-", "--",
                                   "unbound", math.nan])
def test_placeholders_are_missing(value):
    assert is_missing(value)
    assert optional_float(value) is None
    assert optional_text(value) is None
    assert display(value) == ""


@pytest.mark.parametrize("value", [0, 0.0, "0", "0.0", False, "BGC001", "x"])
def test_real_values_are_not_missing(value):
    assert not is_missing(value)


def test_zero_stays_a_measured_zero():
    assert optional_float("0") == 0.0
    assert display("0", fmt=".1f") == "0.0"
    assert display("", fmt=".1f", missing="n.t.") == "n.t."


def test_numbers_parse_strictly():
    assert optional_float("85.5%") == 85.5
    assert optional_float("inf") is None
    assert optional_float("12abc") is None
    assert optional_int("12") == 12
    assert optional_int("12.5") is None
    assert optional_int("") is None


def test_missing_never_matches_missing():
    assert not same_identity("", "")
    assert not same_identity("NA", "NA")
    assert not same_identity(None, "BGC0000001")
    assert same_identity(" BGC0000001 ", "BGC0000001")
