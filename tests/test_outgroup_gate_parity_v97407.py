"""v9.7.407 — the two outgroup-aware gates must AGREE, including on a MULTI-TAXON outgroup.

REGRESSION ORIGIN (real, sealed defect): v9.7.406 made `tools/tree_sanity_check.py --outgroup`
repeatable/comma-separated so a two-taxon outgroup CLADE could be designated and its stem exempted.
`tools/signoff_check.py` mirrors that gate's outgroup semantics by design ("so the two never
disagree about which tip is the outgroup") but was left single-valued, and its hand-rolled arg loop
let a second --outgroup OVERWRITE the first. Result, on one tree with identical flags:
    tree_sanity_check --outgroup OG_one --outgroup OG_two  -> PASS
    signoff_check     --outgroup OG_one --outgroup OG_two  -> flagged OG_two as not-an-outgroup
The shipped .406 carried the behaviour change with NO test (the author's tests did not make the
cut), so nothing failed. These tests pin BOTH halves and the parity between them.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys

_TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")

# tight ingroup, two-taxon outgroup clade on a long stem — the real failure shape
TREE = ("(QUERY:0.31,((A_genus:0.11,B_genus:0.12)100/100:0.04,C_genus:0.23)100/100:0.04,"
        "(OG_one:0.19,OG_two:0.17)100/100:0.46);")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_TOOLS, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tree(tmp_path):
    p = tmp_path / "t.treefile"
    p.write_text(TREE)
    return p


# ---------- parity of the shared predicate ----------

def test_both_gates_accept_repeated_outgroup_terms():
    sc, ts = _load("signoff_check"), _load("tree_sanity_check")
    for mod in (sc, ts):
        assert mod._is_outgroup_tip("OG_one", outgroup=["OG_one", "OG_two"])
        assert mod._is_outgroup_tip("OG_two", outgroup=["OG_one", "OG_two"])
        assert not mod._is_outgroup_tip("A_genus", outgroup=["OG_one", "OG_two"])


def test_both_gates_accept_comma_separated():
    sc, ts = _load("signoff_check"), _load("tree_sanity_check")
    for mod in (sc, ts):
        assert mod._is_outgroup_tip("OG_two", outgroup="OG_one,OG_two")


def test_single_outgroup_still_works_in_both():
    """Backward compatibility: a plain string must behave exactly as before."""
    sc, ts = _load("signoff_check"), _load("tree_sanity_check")
    for mod in (sc, ts):
        assert mod._is_outgroup_tip("Rhodo_ref_X9", outgroup="rhodo")
        assert not mod._is_outgroup_tip("Alpha_a_S1", outgroup="rhodo")
        assert mod._is_outgroup_tip("Ref_x_OUTGROUP")


# ---------- CLI-level parity (the shape that actually broke) ----------

def test_cli_second_outgroup_flag_does_not_overwrite_first(tmp_path):
    """signoff_check's arg loop must ACCUMULATE --outgroup, not overwrite."""
    r = subprocess.run([sys.executable, os.path.join(_TOOLS, "signoff_check.py"),
                        str(_tree(tmp_path)), "--outgroup", "OG_one", "--outgroup", "OG_two"],
                       capture_output=True, text=True, timeout=120)
    assert "not a true outgroup" not in r.stdout, (
        "a designated outgroup tip must not be reported as not-an-outgroup:\n" + r.stdout)


def test_hard_gate_passes_multi_outgroup(tmp_path):
    """tree_sanity_check exempts the outgroup CLADE STEM once every outgroup tip is designated."""
    r = subprocess.run([sys.executable, os.path.join(_TOOLS, "tree_sanity_check.py"),
                        "--outgroup", "OG_one", "--outgroup", "OG_two", str(_tree(tmp_path))],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, f"multi-outgroup should PASS:\n{r.stdout}"


def test_single_designated_tip_of_a_two_tip_outgroup_still_fails(tmp_path):
    """Pins the bug itself: naming ONE tip leaves the clade mixed, so the stem is judged."""
    r = subprocess.run([sys.executable, os.path.join(_TOOLS, "tree_sanity_check.py"),
                        "--outgroup", "OG_one", str(_tree(tmp_path))],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 2 and "DOMINATING_BRANCH" in r.stdout


def test_ingroup_pathology_still_fails_with_full_designation(tmp_path):
    """OVER-EXEMPTION GUARD: a bad INGROUP branch must still FAIL even with every outgroup named."""
    p = tmp_path / "b.treefile"
    p.write_text("(QUERY:3.10,((A_genus:0.11,B_genus:0.12)100/100:0.04,C_genus:0.23)100/100:0.04,"
                 "(OG_one:0.19,OG_two:0.17)100/100:0.46);")
    r = subprocess.run([sys.executable, os.path.join(_TOOLS, "tree_sanity_check.py"),
                        "--outgroup", "OG_one", "--outgroup", "OG_two", str(p)],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 2, "a pathological ingroup branch must still FAIL"


# ---------- second-order false positive found in Amber's own sign-off pass ----------
# (the shared _is_outgroup_tip predicate now legitimately matches >1 tip for a real
# multi-taxon outgroup clade, which trips the UNRELATED "N tips tagged _OUTGROUP
# (expected 1)" leftover-staging check — that check predates .406 and was never meant
# to fire on an operator-designated multi-taxon outgroup.)

def test_multi_outgroup_designation_does_not_trip_leftover_staging_check(tmp_path):
    """A correct two-taxon --outgroup designation must not report 'tips tagged _OUTGROUP
    (expected 1)' — that finding exists for an accidental leftover, not a real clade."""
    r = subprocess.run([sys.executable, os.path.join(_TOOLS, "signoff_check.py"),
                        str(_tree(tmp_path)), "--outgroup", "OG_one", "--outgroup", "OG_two"],
                       capture_output=True, text=True, timeout=120)
    assert "expected 1" not in r.stdout, (
        "a legitimate multi-taxon outgroup must not trip the leftover-staging check:\n" + r.stdout)


def test_two_auto_named_outgroup_tips_with_no_flag_still_caught(tmp_path):
    """PRESERVES the original 2026-07-29 catch: two tips auto-named '..._OUTGROUP' with NO
    --outgroup flag at all is still a real leftover-staging defect and must still be flagged."""
    p = tmp_path / "c.treefile"
    p.write_text("(Streptomyces_griseus_A:0.02,(Streptosporangium_roseum_OUTGROUP:0.1,"
                 "Nocardiopsis_dassonvillei_OUTGROUP:0.12):0.3);")
    r = subprocess.run([sys.executable, os.path.join(_TOOLS, "signoff_check.py"), str(p)],
                       capture_output=True, text=True, timeout=120)
    assert "tagged _OUTGROUP (expected 1) by name" in r.stdout, (
        "two auto-named OUTGROUP tips with no explicit designation must still be caught:\n"
        + r.stdout)
