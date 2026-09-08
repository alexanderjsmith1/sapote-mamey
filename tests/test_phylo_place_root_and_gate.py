"""Engine tests for tools/phylo_place.py rooting + graft render gate (VGP-400).

IN-TREE: exercises the INSTALLED tools/phylo_place.py source. `phylo_place` imports the bundle
`mamey` package at module load and shells out to placement binaries, so these tests assert the two
CONTRACTS that matter without invoking the toolchain:

  1. `_graft_sane()` is a thin delegate to the in-tree outgroup-aware tree_sanity_check, and
     `_render_tree()` refuses (raises) on a FAIL before drawing.
  2. `cmd_build_ref` FAILS CLOSED when `--add-outgroup` is requested but the backbone cannot be
     rooted (Codex C399-15): unresolved/ambiguous/exceptional outgroup => typed refusal, and NO
     refpkg is stamped. Silently continuing would hand EPA-ng an unrooted reference while the
     provenance claims a registry-rooted backbone.

Class-level taxonomy context; judgment deferred.
"""
import importlib.util
import re
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).resolve().parents[1] / "tools"
_SRC = (_TOOLS / "phylo_place.py").read_text(encoding="utf-8")


def _load_tsc():
    spec = importlib.util.spec_from_file_location("_tsc_pp", _TOOLS / "tree_sanity_check.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("_tsc_pp", mod)
    spec.loader.exec_module(mod)
    return mod


def test_graft_gate_is_wired_and_refuses_before_render():
    assert "def _graft_sane(" in _SRC
    assert "_graft_sane(graft_newick" in _SRC, "the gate must be CALLED inside _render_tree"
    assert re.search(r"raise RuntimeError\([^)]*tree_sanity_check FAILED", _SRC), \
        "a FAILing graft must raise before Phylo.draw"
    draw = _SRC.index("Phylo.draw(t")
    assert _SRC.index("_graft_sane(graft_newick") < draw, "the gate must precede the draw call"


def test_gate_decision_matches_the_installed_checker(tmp_path):
    tsc = _load_tsc()
    bad = tmp_path / "bad.newick"
    bad.write_text("((AS-1:0.01,AS-2:0.01):0.01,(Ref_a:0.01,Ref_b:0.01):0.01,AS-3:0.40);")
    ok, msg = tsc.check(str(bad))
    # v9.7.413 addendum: `bad` carries no outgroup tag, so NO_OUTGROUP fires alone, not alongside a
    # DOMINATING_BRANCH finding on the same untrusted branch (see the suppression fix in
    # tools/tree_sanity_check.py::check()).
    assert not ok and "NO_OUTGROUP" in msg and "DOMINATING_BRANCH" not in msg
    good = tmp_path / "ok.newick"
    good.write_text("((AS-1:0.01,AS-2:0.01):0.01,(Ref_a:0.01,Ref_b:0.01):0.01,Outer_x:0.31);")
    ok2, msg2 = tsc.check(str(good), outgroup="Outer")
    assert ok2 and "outgroup-exempt" in msg2


@pytest.mark.parametrize("code", ["BACKBONE_OUTGROUP_UNRESOLVED",
                                  "BACKBONE_ROOTING_FAILED",
                                  "BACKBONE_ROOTING_UNAVAILABLE"])
def test_requested_rooting_fails_closed_with_typed_codes(code):
    assert code in _SRC, f"missing typed refusal {code}"
    # each refusal must exit, not merely print a NOTE and continue
    idx = _SRC.index(code)
    window = _SRC[max(0, idx - 200):idx]
    assert "sys.exit(" in window, f"{code} must sys.exit (fail closed), not print-and-continue"


def test_no_silent_unrooted_continuation_remains():
    """The pre-review behaviour ('backbone left UNROOTED ... root manually') must be gone."""
    assert "backbone left UNROOTED" not in _SRC
    assert "backbone rooting skipped" not in _SRC


def test_refusal_precedes_the_refpkg_stamp():
    """No refpkg may be stamped after a rooting refusal — the refusal must sit before _stamp()."""
    first_refusal = min(_SRC.index(c) for c in
                        ("BACKBONE_OUTGROUP_UNRESOLVED", "BACKBONE_ROOTING_FAILED",
                         "BACKBONE_ROOTING_UNAVAILABLE"))
    stamp = _SRC.index('_stamp(outdir, a.group, "refpkg"')
    assert first_refusal < stamp, "rooting refusals must precede the refpkg provenance stamp"
