"""An existing decision-tree delivery must not be overwritten implicitly."""
import pytest
from tests.test_activity_decision_tree_portable import setup
from mamey.activity_decision_tree import build_activity_decision_trees, ActivityDecisionTreeError

@pytest.mark.parametrize("shape", ["populated_directory", "empty_directory", "file", "directory_symlink", "dangling_symlink"])
def test_existing_output_is_refused_without_changes(tmp_path, shape):
    leads, root = setup(tmp_path)
    out = tmp_path / "out"
    protected = tmp_path / "protected"
    if shape in {"populated_directory", "empty_directory"}:
        out.mkdir()
        if shape == "populated_directory":
            (out / "ACTIVITY_DECISION_TREES.md").write_text("preserve original")
    elif shape == "file":
        out.write_text("preserve original")
    else:
        if shape == "directory_symlink":
            protected.mkdir()
            (protected / "ACTIVITY_DECISION_TREES.md").write_text("preserve original")
        out.symlink_to(protected, target_is_directory=True)
    before = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file() and not p.is_symlink()}
    with pytest.raises(ActivityDecisionTreeError, match="output.*exists"):
        build_activity_decision_trees(leads, root, out)
    after = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file() and not p.is_symlink()}
    assert before == after
