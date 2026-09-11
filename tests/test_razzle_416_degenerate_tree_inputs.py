"""RAZZLE_416 — a tree file that holds no usable tree must produce a FAIL, not a traceback.

The gate's own docstring promises "Exit 0 = PASS, 2 = FAIL", and `check()` is documented as
"importable by the render tools so they can refuse a pathological tree BEFORE drawing" -- i.e. it
must RETURN a verdict. On v9.7.415 an empty file instead raised
`IndexError: string index out of range` out of `parse()` and the CLI exited 1.

Not hypothetical: BiG-SCAPE writes a 0-byte `<FAM>.newick` per singleton GCF, and 89 such files
exist in this workspace, so gating a `GCF_trees/` directory died at the first one.

Second, unrelated hole in the same gate: a tree too small to assess could report a clean PASS.
`A_OUTGROUP:0.1;` PASSED -- its only tip is outgroup-exempt from LONG_TERMINAL, and `longest`
falls through to its 0.0 default so DOMINATING_BRANCH clears. A vacuous PASS on a HARD gate.
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import tree_sanity_check as tsc  # noqa: E402


def _w(tmp_path, text, name="t.treefile"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


# ---- no tree at all ---------------------------------------------------------------------------

@pytest.mark.parametrize("body,label", [
    ("", "empty"),
    ("   \n  ", "whitespace-only"),
    (";", "semicolon-only"),
    ("(A:0.1,B:0.2", "truncated / unbalanced"),
])
def test_input_holding_no_tree_returns_a_fail_not_an_exception(tmp_path, body, label):
    ok, msg = tsc.check(str(_w(tmp_path, body)))
    assert ok is False, f"{label} must FAIL"
    assert "[NO_TREE]" in msg
    # the finding is an ABSENCE: it must not be dressed up as a branch-length offender
    assert "0.0000" not in msg
    assert "LONG_TERMINAL" not in msg and "DOMINATING_BRANCH" not in msg


def test_missing_file_is_a_verdict_not_a_traceback(tmp_path):
    ok, msg = tsc.check(str(tmp_path / "nope.treefile"))
    assert ok is False and "[NO_TREE]" in msg


def test_cli_honours_its_documented_exit_contract(tmp_path):
    """0 = PASS, 2 = FAIL. v9.7.415 exited 1 with a parser traceback."""
    p = _w(tmp_path, "")
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "tree_sanity_check.py"), str(p)],
                       capture_output=True, text=True)
    assert r.returncode == 2, f"expected documented FAIL code 2, got {r.returncode}"
    assert "Traceback" not in r.stderr


def test_a_directory_sweep_survives_one_bad_file(tmp_path):
    """The operational point: one empty tree must not abort gating the rest of a cohort."""
    good = _w(tmp_path, "((((A:0.1,B:0.1):0.1,C:0.1):0.1,D:0.1):0.1,OUTGROUP:0.15);", "good.treefile")
    bad = _w(tmp_path, "", "bad.treefile")
    verdicts = {p.name: tsc.check(str(p))[0] for p in (good, bad)}
    assert verdicts == {"good.treefile": True, "bad.treefile": False}


# ---- too small to assess ----------------------------------------------------------------------

@pytest.mark.parametrize("body", ["A_OUTGROUP:0.1;", "(A:0.1,B_OUTGROUP:0.2);"])
def test_a_tree_too_small_to_assess_does_not_pass(tmp_path, body):
    ok, msg = tsc.check(str(_w(tmp_path, body)))
    assert ok is False, "a 1-2 tip tree must not report a clean bill of health"
    assert "[DEGENERATE_TREE]" in msg
    assert "PASS — no pathological" not in msg


def test_degenerate_report_says_no_check_ran(tmp_path):
    _, msg = tsc.check(str(_w(tmp_path, "A_OUTGROUP:0.1;")))
    assert "NOT a clean bill of health" in msg
    # nothing to prune: the pruning remedy would be wrong advice here
    assert "prune the listed tip" not in msg


def test_real_trees_are_unaffected(tmp_path):
    """Guard the guard: the normal 5-tip rooted case still PASSes unchanged."""
    ok, _ = tsc.check(str(_w(tmp_path, "((((A:0.1,B:0.1):0.1,C:0.1):0.1,D:0.1):0.1,OUTGROUP:0.15);")))
    assert ok is True


# ---- the advisory companion gate --------------------------------------------------------------

def test_signoff_check_names_an_absent_tree_instead_of_calling_it_thin():
    """v9.7.415 reported an empty file as 'thin tree (n=0)' -- which describes a SMALL TREE."""
    sys.path.insert(0, str(ROOT / "tools"))
    import signoff_check as sc
    tips, issues, notes = sc.check_tree_text("")
    assert tips == []
    assert any("NO TREE" in i for i in issues), "the absence must be stated as an issue"
    assert not any("thin tree" in n for n in notes), "an absent tree is not a thin tree"
