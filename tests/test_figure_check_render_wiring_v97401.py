"""Regression test — v97401: render_clean_tree.py refuses a figure_check-FAILing tree.

Follow-on to AMBER_400 (tools/figure_check.py, OPERATOR_ONLY in gate_registry): this wires the gate
into the render entry point, mirroring how the .399 render hard-gate wired tree_sanity_check —
upgrading figure_check to WIRED. Receipt: on 2026-09-01 a figure with a known defect (AS-660 missing
its host marker) was rendered and sent; with this wiring that render REFUSES (exit 2, no PNG).

Runs the real script as a subprocess (matplotlib/Bio available in the test env). Place in tests/.
"""
import pathlib
import subprocess
import sys

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"


def _run(tree, out, env=None):
    import os
    e = dict(os.environ); e.update(env or {})
    return subprocess.run([sys.executable, str(TOOLS / "render_clean_tree.py"),
                           str(tree), str(out), "t", "Rhodococcus_OUTGROUP"],
                          capture_output=True, text=True, env=e)


def test_failing_figure_is_refused_no_png_v97401(tmp_path):
    tree = tmp_path / "bad.treefile"
    tree.write_text("(Streptomyces_sp_AS:0.01,Nocardia_iowensis:0.01,Rhodococcus_OUTGROUP:0.02);\n")
    out = tmp_path / "out.png"
    r = _run(tree, out)
    assert r.returncode == 2, r.stderr
    assert "figure_check FAILED" in r.stderr and "BARE 'AS'" in r.stdout
    assert not out.exists(), "a FAILing figure must never produce a PNG"


def test_clean_figure_still_renders_v97401(tmp_path):
    tree = tmp_path / "good.treefile"
    tree.write_text("(Nocardia_AS-188_bumblebee:0.01,Nocardia_iowensis:0.01,Rhodococcus_OUTGROUP:0.02);\n")
    out = tmp_path / "out.png"
    r = _run(tree, out)
    assert r.returncode == 0, r.stderr
    assert out.exists()


def test_documented_skip_hatch_v97401(tmp_path):
    tree = tmp_path / "bad.treefile"
    tree.write_text("(Streptomyces_sp_AS:0.01,Nocardia_iowensis:0.01,Rhodococcus_OUTGROUP:0.02);\n")
    out = tmp_path / "out.png"
    r = _run(tree, out, env={"FIGCHECK_SKIP": "1"})
    assert r.returncode == 0 and out.exists()
