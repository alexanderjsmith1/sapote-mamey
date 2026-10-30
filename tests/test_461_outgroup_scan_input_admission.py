"""Malformed tree input must not support a STABLE verdict; no tree inference."""
import importlib.util
from pathlib import Path
import pytest

_SPEC = importlib.util.spec_from_file_location("scan461", Path(__file__).resolve().parents[1] / "tools/mlsa_outgroup_scan.py")
scan = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(scan)
# Reuse topology-only mechanical fixture shape from test_458_outgroup_scan_insufficient_input.
TREE = "((A,B),(C,D),X_OUTGROUP);"


@pytest.mark.parametrize("suffix", ["((A,C),(B,D));", ")", ";"])
def test_trailing_newick_content_is_refused(suffix):
    with pytest.raises(ValueError, match="trailing Newick"):
        scan._parse(TREE + suffix)


def test_cli_does_not_report_stable_for_two_concatenated_trees(tmp_path, capsys):
    a = tmp_path / "first.treefile"; b = tmp_path / "second.treefile"
    a.write_text(TREE); b.write_text(TREE + "((A,C),(B,D));")
    assert scan.main(["--trees", str(a), str(b)]) == 1
    captured = capsys.readouterr()
    assert "STABLE" not in captured.out
    assert "TREE_INPUT_ERROR" in captured.err


def test_missing_tree_reports_a_typed_refusal(tmp_path, capsys):
    assert scan.main(["--trees", str(tmp_path / "absent.treefile")]) == 1
    assert "TREE_INPUT_ERROR" in capsys.readouterr().err
