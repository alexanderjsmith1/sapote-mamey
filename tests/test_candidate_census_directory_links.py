from pathlib import Path
import importlib.util
import pytest
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("census_symlink_test", ROOT / "tools" / "candidate_census.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

@pytest.mark.parametrize("internal", [False, True])
def test_skipped_directory_link_is_incomplete(tmp_path, internal):
    root = tmp_path / "candidate"; root.mkdir()
    target = (root if internal else tmp_path) / "target"; target.mkdir()
    (target / "hidden.pyc").write_bytes(b"debris")
    (root / "linked").symlink_to(target, target_is_directory=True)
    report = m.census(str(root))
    assert report["status"] == "INCOMPLETE"
    assert not report["coverage_complete"]
    assert report["traversal_errors"][0]["error_type"] == "DirectorySymlinkSkipped"

def test_link_cycle_is_not_followed(tmp_path):
    (tmp_path / "cycle").symlink_to(tmp_path, target_is_directory=True)
    report = m.census(str(tmp_path))
    assert report["status"] == "INCOMPLETE"
    assert len(report["traversal_errors"]) == 1

def test_normal_subtree_preserves_debris_count(tmp_path):
    nested = tmp_path / "nested"; nested.mkdir()
    (nested / "hidden.pyc").write_bytes(b"debris")
    report = m.census(str(tmp_path))
    assert report["coverage_complete"]
    assert report["status"] == "DEBRIS_FOUND"
    assert report["debris"]["pyc_files"] == 1
