"""Tree-portable regression for the render HARD gate (VGP .399 phylo patch 2).

`tools/render_clean_tree.py` must refuse (exit 2, "REFUSED", no output file) a tree that FAILS
`tree_sanity_check.check()` BEFORE drawing anything, while a healthy registry-rooted tree (whose
only dominating branch is the tagged outgroup — exempt by the .398 outgroup-aware checker) still
renders. Replaces the packet-relative before/after harness with self-contained fixtures; runs the
REAL tool via subprocess. Genome dir is not needed by render_clean_tree (it takes a treefile).
"""
from __future__ import annotations

import os
import subprocess
import sys

TOOL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    "tools", "render_clean_tree.py")

BAD_INGROUP_DOMINATOR = "((Alpha_a_S1:0.01,Alpha_b_S2:0.012):0.01,(Beta_c_S3:0.011,Bad_query_S4:0.90):0.01,Ref_x_OUTGROUP:0.05);"
GOOD_OUTGROUP_DOMINATES = "((Alpha_a_S1:0.01,Alpha_b_S2:0.012):0.01,(Beta_c_S3:0.011,Beta_d_S4:0.01):0.01,Ref_x_OUTGROUP:0.30);"


def _run(treefile, out_png, outgroups=""):
    return subprocess.run(
        [sys.executable, TOOL, str(treefile), str(out_png), "portable-gate test", outgroups],
        capture_output=True, text=True, timeout=180,
    )


def test_failing_tree_is_refused_before_any_figure(tmp_path):
    tf = tmp_path / "bad.treefile"
    tf.write_text(BAD_INGROUP_DOMINATOR)
    out = tmp_path / "bad.png"
    r = _run(tf, out)
    assert r.returncode == 2, f"gate must refuse with exit 2 (got {r.returncode}; out={r.stdout[-200:]})"
    assert "REFUSED" in (r.stdout + r.stderr), (r.stdout[-200:], r.stderr[-200:])
    assert not out.exists(), "a FAILing tree must never reach a figure"


def test_outgroup_dominated_tree_still_renders(tmp_path):
    tf = tmp_path / "good.treefile"
    tf.write_text(GOOD_OUTGROUP_DOMINATES)
    out = tmp_path / "good.png"
    r = _run(tf, out, outgroups="Ref_x_OUTGROUP")
    assert r.returncode == 0, f"registry-rooted tree must pass the gate (out={r.stdout[-300:]} err={r.stderr[-200:]})"
    assert out.exists() and out.stat().st_size > 0, "the PASSing tree must actually render"
