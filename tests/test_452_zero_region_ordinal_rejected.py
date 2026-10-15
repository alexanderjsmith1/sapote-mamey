"""A zero region ordinal names no antiSMASH region; the exact-locus owner refuses it."""
import pytest

from mamey.exact_identity import (
    ExactLocusIdentityError,
    exact_locus_display,
    exact_locus_from_native_inventory_row,
)

CONTIG = "NODE_7_length_120000_cov_42.5"


def _inventory_row(region_label, ordinal=None):
    row = {"Contig": CONTIG, "Node_ID": "NODE_7_length_120000_cov_42", "antiSMASH_Region": region_label, "BGC_ID": "BGC007"}
    if ordinal is not None:
        row["Region"] = ordinal
    return row


@pytest.mark.parametrize("region", ["region000", "region0000", "REGION000", "region١٢٣", "unknown"])
def test_zero_unknown_or_non_ascii_region_is_refused(region):
    with pytest.raises(ExactLocusIdentityError):
        exact_locus_display("SYN-1", CONTIG, region, "BGC007")


@pytest.mark.parametrize("region", ["region001", "Region007", "region1000", "region0012"])
def test_positive_regions_still_display(region):
    assert exact_locus_display("SYN-1", CONTIG, region, "BGC007") == f"SYN-1 / {CONTIG} / {region} / BGC007"


@pytest.mark.parametrize("label,ordinal", [("region000", "0"), ("region000", "000"), ("region001", "0")])
def test_native_inventory_zero_ordinal_is_refused(label, ordinal):
    with pytest.raises(ExactLocusIdentityError):
        exact_locus_from_native_inventory_row("SYN-1", _inventory_row(label, ordinal))


@pytest.mark.parametrize("label,ordinal", [("region001", "1"), ("region007", "007"), ("region1000", "1000")])
def test_native_inventory_positive_ordinal_still_binds(label, ordinal):
    identity = exact_locus_from_native_inventory_row("SYN-1", _inventory_row(label, ordinal))
    assert identity.region == label
    assert identity.exact_locus == f"SYN-1 / {CONTIG} / {label} / BGC007"


def test_native_inventory_mismatched_ordinal_still_refused():
    with pytest.raises(ExactLocusIdentityError):
        exact_locus_from_native_inventory_row("SYN-1", _inventory_row("region002", "1"))
