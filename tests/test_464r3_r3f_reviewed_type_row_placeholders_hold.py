"""A placeholder in a required reviewed type field is missing evidence, not evidence.

`NA`, `-`, `none`, `not available` (the `mamey.missing_values` tokens) and a zero-width space
in any required type field hold the row with HOLD_TYPE_EVIDENCE_MISSING, so no type mark is put
on the tip. A placeholder `accession` cell holds with HOLD_TYPE_ACCESSION_MISSING, not as a
conflict. Synthetic rows only.
"""
import pytest

from tools import _placement_report_metadata as contract
from tests.test_464r3_r3d_tools_reviewed_type_row_requires_accession import LABEL, TIP, _row, _table

PLACEHOLDERS = ["NA", "n/a", "-", "none", "None", "not available", "nan", "​"]


@pytest.mark.parametrize("field", ["type_evidence", "strain_identity_basis", "taxon", "strain"])
@pytest.mark.parametrize("value", PLACEHOLDERS)
def test_placeholder_type_evidence_is_held(tmp_path, field, value):
    path = _table(tmp_path / "reviewed.tsv", _row(**{field: value}))
    with pytest.raises(ValueError, match="HOLD_TYPE_EVIDENCE_MISSING"):
        contract.reviewed_type_map([path], {TIP: LABEL})


@pytest.mark.parametrize("value", PLACEHOLDERS + ["null", "unbound"])
def test_placeholder_accession_is_missing_not_conflicting(tmp_path, value):
    path = _table(tmp_path / "reviewed.tsv", _row(accession=value))
    with pytest.raises(ValueError, match="HOLD_TYPE_ACCESSION_MISSING"):
        contract.reviewed_type_map([path], {TIP: LABEL})


def test_a_real_conflicting_accession_is_still_a_conflict(tmp_path):
    path = _table(tmp_path / "reviewed.tsv", _row(accession="NR_000009.1"))
    with pytest.raises(ValueError, match="HOLD_TYPE_SOURCE_ACCESSION_CONFLICT"):
        contract.reviewed_type_map([path], {TIP: LABEL})


def test_complete_row_is_admitted(tmp_path):
    path = _table(tmp_path / "reviewed.tsv", _row())
    assert TIP in contract.reviewed_type_map([path], {TIP: LABEL})["roles"]
