"""Ruling 314: strong = 80% or more; below 80% is not "inactive" (inactive is under 25%). The placement-tree activity strip printed
"active (>=80%)" and "tested, inactive", so a 50-79% reading, which the thesis calls moderate, was drawn as inactive. The three files that
hold the words (placement_display.py, _placement_activity.py, phylo_display_palette.tsv) must change together: the R renderer and the
annotation gate check every category against the palette."""
import csv
import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
STRONG, BELOW = "strong (≥80%)", "tested, below 80%"
OLD = ("active (≥80%)", "tested, inactive")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_a_numeric_reading_is_strong_or_tested_below_80():
    act = _load("_placement_activity")
    assert act.state("95") == STRONG and act.state("80") == STRONG
    assert act.state("79.9") == BELOW and act.state("65") == BELOW and act.state("0") == BELOW
    assert act.state("+") == "+" and act.state("−") == "−" and act.state("n.t.") == "n.t."   # recorded states are never converted


def test_the_pooled_candida_order_ranks_the_new_labels_by_strength():
    act = _load("_placement_activity")
    assert act.POOL_ORDER.index(STRONG) < act.POOL_ORDER.index(BELOW)
    assert not set(OLD) & set(act.POOL_ORDER)


def test_the_palette_carries_the_new_words_in_both_fields_and_no_old_ones():
    rows = list(csv.reader(open(ROOT / "tools/phylo_display_palette.tsv"), delimiter="\t"))
    for field in ("activity", "activity_calm"):
        values = [r[1] for r in rows if r and r[0] == field]
        assert STRONG in values and BELOW in values
        assert not set(OLD) & set(values)


def test_no_tool_still_prints_the_pre_314_legend_words():
    for rel in ("tools/placement_display.py", "tools/_placement_activity.py", "tools/phylo_display_palette.tsv"):
        text = (ROOT / rel).read_text()
        assert not any(o in text for o in OLD) and "\\u2265 80%" not in text, rel
        assert "tested, inactive" not in text, rel


def test_the_annotation_gate_accepts_the_new_words_and_refuses_the_old():
    gate = _load("tree_annotation_gate")
    ok = [dict(tip="Q1", role="query", category=STRONG, source=BELOW)]
    gate.validate_activity(ok)
    for old in OLD:
        with pytest.raises(ValueError):
            gate.validate_activity([dict(tip="Q1", role="query", category=old, source=BELOW)])


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_a_tiny_tree_renders_with_the_new_legend_words(tmp_path):
    tree, meta, prefix = tmp_path / "t.nwk", tmp_path / "m.tsv", tmp_path / "fig"
    tips = ["SYN-1", "SYN-2", "Reference_a", "Reference_b", "Reference_outgroup"]
    tree.write_text("((" + ",".join(f"{t}:0.01" for t in tips[:-1]) + "):0.01,Reference_outgroup:0.03);")
    with meta.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["tip", "label", "role", "category", "source"], delimiter="\t")
        w.writeheader()
        for i, t in enumerate(tips):
            w.writerow(dict(tip=t, label=t, role="query" if i < 2 else "reference", category=[STRONG, BELOW][i] if i < 2 else "",
                            source=[BELOW, STRONG][i] if i < 2 else ""))
    env = dict(os.environ, SAPOTE_PYTHON=sys.executable, GG_PRINT_WIDTH="7.2", GG_STRIPS="2", GG_STRIP_KIND="activity",
               GG_BLANK_MISSING="1", GG_STRIP1_TITLE="Activity A", GG_STRIP2_TITLE="Activity B")
    proc = subprocess.run(["Rscript", str(ROOT / "tools/ggtree_rect_heatmap.R"), str(tree), str(meta), str(prefix)],
                          env=env, text=True, capture_output=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    audit = list(csv.DictReader((tmp_path / "fig.annotation_audit.tsv").open(), delimiter="\t"))
    values = {r["value"] for r in audit}
    assert STRONG in values and BELOW in values
    from pypdf import PdfReader
    text = " ".join(p.extract_text() for p in PdfReader(str(prefix.with_suffix(".pdf"))).pages)
    assert "strong" in text and "below 80%" in text and "inactive" not in text
