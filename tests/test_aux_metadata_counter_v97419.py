"""Portable auxiliary metadata regression — the aux-metadata counter reported table rows, not tips enriched.

`--aux-table` takes any path, so passing another cohort's table is the obvious operator slip. The
counter incremented once per FILLED FIELD ON ANY STRAIN IN THE TABLE, including strains that are not
tips in the tree being built. Reproduced on the real Kribbella panel with an aux table naming only
AS-9001/AS-9002: the tool printed "filled 6 empty field(s)" while 4 of 5 query tips still rendered
bare — zero tips enriched.

The existing "no metadata at all" NOTE does not cover this: it fires only when NOTHING has metadata,
so a single tip supplied by --host-table silences it.
"""
import importlib.util
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "tools", "build_placement_ggtree_inputs.py")

GRAFT = ("((AS_1:0.01,NR_000001_1_Genus_alpha_strain_A_16S:0.01):0.02,"
         "(AS_2:0.01,NR_000002_1_Genus_beta_strain_B_16S:0.01):0.02,"
         "NR_000003_1_Other_gamma_strain_C_16S_outgroup:0.3);")


def _run(tmp_path, aux_rows, host_rows=None):
    g = tmp_path / "g.newick"; g.write_text(GRAFT, encoding="utf-8")
    aux = tmp_path / "aux.tsv"
    aux.write_text("strain\thost\tregion\taccession\n" + aux_rows, encoding="utf-8")
    cmd = [sys.executable, TOOL, "--graft", str(g), "--group", "Genus", "--neighbors", "3",
           "--aux-table", str(aux), "--out-prefix", str(tmp_path / "out")]
    if host_rows is not None:
        h = tmp_path / "host.tsv"
        h.write_text("tip_label\thost_common\tlocation\tgenbank_accession\n" + host_rows,
                     encoding="utf-8")
        cmd += ["--host-table", str(h)]
    r = subprocess.run(cmd, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout + r.stderr


def test_a_wrong_cohort_table_does_not_report_a_successful_fill(tmp_path):
    """The regression: 'filled 6 empty field(s)' while zero tips were enriched."""
    out = _run(tmp_path, "AS-9001\tsoil\tPeru\tNR_1.1\nAS-9002\tsoil\tPeru\tNR_2.1\n",
               host_rows="AS-1\tmoss\tOntario\tPX1.1\n")
    assert "filled 0 empty field(s) on tips in this tree" in out
    assert "NO tip was enriched" in out, "the operator must be told the table matched nothing here"


def test_a_matching_table_reports_the_tips_it_enriched(tmp_path):
    out = _run(tmp_path, "AS-1\tmoss\tOntario\tPX1.1\nAS-2\tbee\tQuebec\tPX2.1\n")
    assert "filled 6 empty field(s) on tips in this tree" in out
    assert "NO tip was enriched" not in out


def test_off_tree_rows_are_reported_but_not_alarming(tmp_path):
    """One shared aux table across many per-genus panels is the NORMAL way to run this, so
    off-tree rows must be stated without implying an error."""
    out = _run(tmp_path, "AS-1\tmoss\tOntario\tPX1.1\nAS-9001\tsoil\tPeru\tNR_1.1\n")
    assert "filled 3 empty field(s) on tips in this tree" in out
    assert "1 more matched strain(s) not in this tree" in out, "STRAINS off-tree, not fields"
    assert "NO tip was enriched" not in out, "some tip WAS enriched; this must not read as a failure"


def test_the_counter_is_not_silent_when_something_lands(tmp_path):
    out = _run(tmp_path, "AS-1\tmoss\tOntario\tPX1.1\n")
    assert "aux metadata:" in out
