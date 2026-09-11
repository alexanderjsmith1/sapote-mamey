"""Tree-portable regression for signoff/tree_sanity outgroup PARITY (VGP .399 phylo patch 3).

`tools/signoff_check.py` gained `_is_outgroup_tip` + `--outgroup` so the advisory sign-off gate
and the HARD `tree_sanity_check` gate can never disagree about which tip is the outgroup: a
correct-but-untagged sister taxon named via `--outgroup` must not be reported as
"no _OUTGROUP-tagged tip found". Replaces the packet-relative harness; self-contained.
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys

_TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools")
_SPEC = importlib.util.spec_from_file_location("tools_signoff_check", os.path.join(_TOOLS, "signoff_check.py"))
signoff = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(signoff)

UNTAGGED_OUTGROUP_TREE = "((Alpha_a_S1:0.01,Alpha_b_S2:0.012):0.01,(Beta_c_S3:0.011,Beta_d_S4:0.01):0.01,Rhodo_ref_X9:0.25);"


def test_is_outgroup_tip_mirrors_tree_sanity_semantics():
    assert signoff._is_outgroup_tip("Ref_x_OUTGROUP")
    assert signoff._is_outgroup_tip("ref_x_outgroup"), "OUTGROUP match must be case-insensitive"
    assert signoff._is_outgroup_tip("Rhodo_ref_X9", outgroup="rhodo"), "--outgroup token must match case-insensitively"
    assert not signoff._is_outgroup_tip("Alpha_a_S1")
    assert not signoff._is_outgroup_tip("Alpha_a_S1", outgroup="rhodo")


def _run_cli(treefile, *extra):
    return subprocess.run(
        [sys.executable, os.path.join(_TOOLS, "signoff_check.py"), str(treefile), *extra],
        capture_output=True, text=True, timeout=120,
    )


def test_untagged_outgroup_named_via_flag_is_not_reported_missing(tmp_path):
    tf = tmp_path / "untagged.treefile"
    tf.write_text(UNTAGGED_OUTGROUP_TREE)
    without = _run_cli(tf)
    with_flag = _run_cli(tf, "--outgroup", "Rhodo")
    assert "no _OUTGROUP-tagged tip found" in without.stdout, \
        "control: without the flag the untagged outgroup must still be reported missing"
    assert "no _OUTGROUP-tagged tip found" not in with_flag.stdout, \
        "--outgroup must satisfy the outgroup-present check (parity with tree_sanity_check)"
