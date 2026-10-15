import pytest
from mamey.bgc_blastp_panel import assign_rounds, _write_scope

@pytest.mark.parametrize("isolate", [True, False])
def test_oversized_intact_sequence_is_held_before_fasta_write(tmp_path, isolate):
    row = {"sequence": "M" * 11, "protein_length_aa": 11, "bgc_id": "BGC001"}
    with pytest.raises(ValueError, match="held"):
        _write_scope(tmp_path, "SYN-A", "selected", [row], 5, 10, 5, True, isolate, [])
    assert list(tmp_path.iterdir()) == []

@pytest.mark.parametrize("records,residues", [(0, 10), (5, 0), (-1, 10), (5, -1)])
def test_nonpositive_caps_are_refused(records, residues):
    with pytest.raises(ValueError):
        assign_rounds([], "SYN-A", proteins_per_file=records, max_residues=residues)

def test_valid_group_is_packed_without_truncating_proteins():
    rows = [{"sequence": "M" * 6, "protein_length_aa": 6, "bgc_id": "BGC001"} for _ in range(3)]
    rounds = assign_rounds(rows, "SYN-A", max_residues=12)
    assert [len(r) for r in rounds] == [2, 1]
    assert [row for chunk in rounds for row in chunk] == rows
