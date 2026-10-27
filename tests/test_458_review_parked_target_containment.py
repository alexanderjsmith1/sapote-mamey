from pathlib import Path
import importlib.util
import pytest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("parked_review", ROOT / "tools/parked_card_audit.py")
tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)

@pytest.mark.parametrize("escape", ["parent", "absolute", "symlink", "old_header"])
def test_outside_target_is_refused_before_presence_or_dry_run(tmp_path, monkeypatch, escape):
    tree=tmp_path / "tree";tree.mkdir()
    outside=tmp_path / "outside.py";outside.write_text("new_line\n")
    old="a/inside.py";new="b/inside.py"
    (tree / "inside.py").write_text("new_line\n")
    if escape == "parent": new="b/../outside.py"
    elif escape == "absolute": new=str(outside)
    elif escape == "symlink":
        (tree / "link.py").symlink_to(outside);new="b/link.py"
    else: old="a/../outside.py"
    patch=tmp_path / "card.diff"
    patch.write_text(f"--- {old}\n+++ {new}\n@@ -1 +1 @@\n-old_line\n+new_line\n")
    monkeypatch.setattr(tool, "_dry_run", lambda *a, **k: pytest.fail("unsafe patch reached dry run"))
    with pytest.raises(ValueError, match="PATCH_TARGET_OUTSIDE_TREE"):
        tool._classify_patch(patch, tree)

@pytest.mark.parametrize("kind, expected", [("modify", "FOLDED"), ("add", "FOLDED"),
                                             ("delete", "OUT_OF_SCOPE")])
def test_in_tree_and_dev_null_headers_keep_existing_classification(tmp_path, kind, expected):
    tree=tmp_path / "tree";tree.mkdir();(tree / "inside.py").write_text("new_line\n")
    old="/dev/null" if kind == "add" else "a/inside.py"
    new="/dev/null" if kind == "delete" else "b/inside.py"
    patch=tmp_path / "card.diff"
    hunk = "@@ -1 +0,0 @@\n-new_line\n" if kind == "delete" else "@@ -1 +1 @@\n-old_line\n+new_line\n"
    patch.write_text(f"--- {old}\n+++ {new}\n" + hunk)
    assert tool._classify_patch(patch, tree) == expected

def test_cli_reports_refusal_without_clean_summary(tmp_path, monkeypatch, capsys):
    import sys
    def reject(*args, **kwargs):raise ValueError("PATCH_TARGET_OUTSIDE_TREE: synthetic")
    monkeypatch.setattr(tool, "audit", reject)
    monkeypatch.setattr(sys, "argv", ["parked_card_audit", str(tmp_path), "--sealed-tree", str(tmp_path),
                                     "--current-version", "457"])
    assert tool.main() == 2
    out=capsys.readouterr()
    assert "PATCH_TARGET_OUTSIDE_TREE" in out.err
    assert "nothing flagged" not in out.out
