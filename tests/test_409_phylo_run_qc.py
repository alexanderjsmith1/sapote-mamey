#!/usr/bin/env python3
"""CLAUDE_409 phylo-run QC + determinism — fail-before/pass-after coverage for Finding 3 & 7.

Verifies the two fixes wired into ``tools/run_planned_tree.py``:

  * Finding 3 — the CLI-blessed genome executor now runs a HARD tree-QC gate
    (``tree_sanity_check`` + ``phylo_postflight`` P1-P6 + ``phylo_evidence`` support) on the
    finished treefile BEFORE it may report DONE. A contaminant/dominating branch, a bootstrap
    killed mid-run (no support), etc. are caught (typed) instead of silently reported complete.
  * Finding 7 — the IQ-TREE invocation now pins ``-seed`` (default 12345) and a fixed ``-T``
    (default 1) instead of the non-reproducible no-seed / ``-T AUTO``.

Runs against a copy of the bundle ``tools/`` + ``mamey/`` tree (BUNDLE_ROOT env var, or the
default scratchpad copy). Pure/offline — never launches GToTree or IQ-TREE.
"""
import importlib.util
import os
import re
import sys

import pytest

# Default: the bundle root (parent of tests/), so this works dropped into tests/. Override with
# BUNDLE_ROOT to point at a scratchpad copy of the tools/+mamey/ tree.
BUNDLE_ROOT = os.environ.get(
    "BUNDLE_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNNER = os.path.join(BUNDLE_ROOT, "tools", "run_planned_tree.py")


def _load_runner():
    spec = importlib.util.spec_from_file_location("run_planned_tree_under_test", RUNNER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GOOD = ("(OUTGROUP_Nocardiopsis_dassonvillei_DSM43111:0.12,"
        "(Streptomyces_griseus_DSM40236:0.02,"
        "(Streptomyces_coelicolor_A32:0.02,Streptomyces_avermitilis_MA4680:0.02)98/100:0.01)"
        "95/99:0.02);")
# bootstrap killed mid-run: correct tips, ends with ';', NO support labels
NO_SUPPORT = ("(OUTGROUP_Nocardiopsis_dassonvillei_DSM43111:0.12,"
              "(Streptomyces_griseus_DSM40236:0.02,"
              "(Streptomyces_coelicolor_A32:0.02,Streptomyces_avermitilis_MA4680:0.02):0.01):0.02);")
# contaminant E. coli on a dominating long branch
ROGUE = ("(OUTGROUP_Nocardiopsis_dassonvillei_DSM43111:0.12,"
         "(Streptomyces_griseus_DSM40236:0.02,"
         "(Escherichia_coli_K12:2.5,Streptomyces_avermitilis_MA4680:0.02)80/95:0.01)95/99:0.02);")


def _write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return str(p)


def test_runner_wires_the_hard_qc_and_determinism():
    """The patched runner exposes hard_tree_qc and pins seed + fixed threads (grep-level)."""
    src = open(RUNNER, encoding="utf-8").read()
    assert "def hard_tree_qc(" in src
    assert "tree_sanity_check" in src
    assert "phylo_postflight" in src
    assert "phylo_evidence" in src
    # determinism: seed pinned, AUTO gone from the iqtree invocation
    assert "--seed" in src or "-seed" in src
    assert re.search(r'"-seed",\s*str\(a\.seed\)', src)
    assert '"-T", "AUTO"' not in src


def test_good_tree_passes(tmp_path):
    mod = _load_runner()
    ok, lines = mod.hard_tree_qc(_write(tmp_path, "good.treefile", GOOD), "Nocardiopsis")
    assert ok is True, "\n".join(lines)


def test_bootstrap_killed_midrun_is_caught(tmp_path):
    """No support labels -> postflight P3 FAIL AND phylo_evidence PHYLO_SUPPORT_MISSING."""
    mod = _load_runner()
    ok, lines = mod.hard_tree_qc(_write(tmp_path, "ns.treefile", NO_SUPPORT), "Nocardiopsis")
    blob = "\n".join(lines)
    assert ok is False
    assert "PHYLO_SUPPORT_MISSING" in blob
    assert "P3" in blob and "bootstrap did not finish" in blob


def test_contaminant_dominating_branch_is_caught(tmp_path):
    """E. coli on a branch eating the tree -> tree_sanity_check DOMINATING_BRANCH FAIL."""
    mod = _load_runner()
    ok, lines = mod.hard_tree_qc(_write(tmp_path, "rogue.treefile", ROGUE), "Nocardiopsis")
    blob = "\n".join(lines)
    assert ok is False
    assert "DOMINATING_BRANCH" in blob


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
