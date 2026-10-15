import pytest
from tools.check_provenance_columns import main

@pytest.mark.parametrize("other", ["missing.tsv", "unsupported.txt", "folder.csv"])
def test_required_target_cannot_disappear(tmp_path, other):
    valid = tmp_path / "valid.tsv"
    valid.write_text("strain\tcontig\tregion\tbgc_id\nSYN-A\tcontig1\t1\tBGC001\n")
    target = tmp_path / other
    if other == "unsupported.txt":
        target.write_text("data")
    elif other == "folder.csv":
        target.mkdir()
    assert main([str(valid), str(target)]) == 2
    assert main([str(valid), str(valid)]) == 0

def test_unmatched_required_glob_is_not_partial_success(tmp_path):
    valid = tmp_path / "valid.csv"
    valid.write_text("value\n1\n")
    assert main([str(valid), "--glob", str(tmp_path / "absent*.tsv")]) == 2
