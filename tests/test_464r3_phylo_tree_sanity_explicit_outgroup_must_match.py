"""tree_sanity_check: an explicit --outgroup term that matches no tip FAILs on the command line, even
when another tip carries an OUTGROUP marker; every term is reported with the tips it matched; and an
exempt outgroup branch is reported with its share of tree depth."""
import subprocess
import sys
from pathlib import Path

GATE = Path(__file__).resolve().parents[1] / "tools" / "tree_sanity_check.py"
TREE = "(((A:0.01,B:0.012):0.01,(C:0.011,D:0.013):0.01):0.02,E_OUTGROUP:0.03);"


def _run(tmp_path, tree, *extra):
    p = tmp_path / "t.nwk"
    p.write_text(tree)
    return subprocess.run([sys.executable, str(GATE), str(p), *extra], text=True, capture_output=True)


def test_unmatched_explicit_outgroup_fails_despite_marker(tmp_path):
    r = _run(tmp_path, TREE, "--outgroup", "Nonexistent_genus")
    assert r.returncode == 2, r.stdout
    assert "[OUTGROUP_UNMATCHED]" in r.stdout
    assert "'nonexistent_genus' matched 0 tip(s) -- NOT FOUND" in r.stdout


def test_matched_explicit_outgroup_passes_and_names_tip(tmp_path):
    r = _run(tmp_path, TREE, "--outgroup", "E_OUTGROUP")
    assert r.returncode == 0, r.stdout
    assert "'e_outgroup' matched 1 tip(s): E_OUTGROUP" in r.stdout


def test_marker_only_tree_still_passes(tmp_path):
    r = _run(tmp_path, TREE)
    assert r.returncode == 0, r.stdout
    assert "[outgroup-term]" not in r.stdout


def test_dominant_outgroup_branch_reports_depth_share(tmp_path):
    r = _run(tmp_path, "(((A:0.01,B:0.012):0.01,(C:0.011,D:0.013):0.01):0.0,E_OUTGROUP:0.9);")
    assert r.returncode == 0, r.stdout
    assert "[outgroup-exempt] 0.9000" in r.stdout and "100% of tree depth" in r.stdout
    assert "review this branch and the root yourself" in r.stdout


def test_library_call_default_does_not_require_match(tmp_path):
    sys.path.insert(0, str(GATE.parent))
    import tree_sanity_check as tsc
    p = tmp_path / "t.nwk"
    p.write_text(TREE)
    ok, msg = tsc.check(str(p), outgroup="Nonexistent_genus")
    assert ok is True and "NOT FOUND" in msg
    ok, msg = tsc.check(str(p), outgroup="Nonexistent_genus", require_outgroup_match=True)
    assert ok is False and "[OUTGROUP_UNMATCHED]" in msg
