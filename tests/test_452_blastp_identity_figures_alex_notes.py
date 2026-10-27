"""Card 452_blastp_identity_figures_alex_notes.

Owner review of the by-genome and by-class BLASTp identity figures:
- panel B prints no genes-with-a-hit fraction above its bars by default, and `--bar-counts` opts back in;
- `--omit-class` leaves a class off the by-class figure while its rows stay in the numbers table;
- every drawn text run is at least 8 pt (docs/FIGURE_STYLE.md publication gate).
Uses the synthetic world of test_451_blastp_identity_figures.
"""
import csv
import json
import math
import re

import pytest

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location("_t451_bif", Path(__file__).with_name("test_451_blastp_identity_figures.py"))
_t451 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_t451)
_run, world = _t451._run, _t451.world  # world is the 451 card's pytest fixture, reused here

pypdf = pytest.importorskip("pypdf")


def _text_runs(pdf):
    runs = []
    for page in pypdf.PdfReader(str(pdf)).pages:
        def visit(text, cm, tm, font_dict, font_size):
            if text and text.strip():
                a, b, c, d = (cm[0] * tm[0] + cm[2] * tm[1], cm[1] * tm[0] + cm[3] * tm[1],
                              cm[0] * tm[2] + cm[2] * tm[3], cm[1] * tm[2] + cm[3] * tm[3])
                runs.append((font_size * math.sqrt(abs(a * d - b * c)), text.strip()))
        page.extract_text(visitor_text=visit)
    return runs


def _fraction_labels(pdf):
    return [t for _, t in _text_runs(pdf) if re.fullmatch(r"\d+/\d+", t)]


def test_panel_b_has_no_bar_fractions_by_default(world):
    out = world["tmp"] / "default"
    assert _run(world, out, "--figure", "by-genome") == 0
    assert _fraction_labels(out / "BLASTP_IDENTITY_BY_GENOME.pdf") == []
    rows = [r for r in csv.reader(open(out / "BLASTP_IDENTITY_BY_GENOME_numbers.tsv"), delimiter="\t") if len(r) > 4 and r[1] == "S1"]
    assert rows and rows[0][3:5] == ["2", "3"]          # the counts still go to the numbers table
    assert json.loads((out / "RUN_INFO.json").read_text())["bar_counts"] is False


def test_bar_counts_option_restores_the_fractions(world):
    out = world["tmp"] / "counts"
    assert _run(world, out, "--figure", "by-genome", "--bar-counts") == 0
    assert "2/3" in _fraction_labels(out / "BLASTP_IDENTITY_BY_GENOME.pdf")


def test_omit_class_drops_the_panel_but_keeps_its_numbers(world):
    out = world["tmp"] / "omit"
    assert _run(world, out, "--figure", "by-class", "--omit-class", "Terpene") == 0
    text = " ".join(t for _, t in _text_runs(out / "BLASTP_IDENTITY_BY_CLASS.pdf"))
    assert "Terpene core genes" not in text and "PKS core genes" in text
    classes = {r[0] for r in csv.reader(open(out / "BLASTP_IDENTITY_BY_CLASS_numbers.tsv"), delimiter="\t")}
    assert "Terpene" in classes
    assert json.loads((out / "RUN_INFO.json").read_text())["omitted_classes"] == ["Terpene"]


@pytest.mark.parametrize("figure,stem", [("by-genome", "BLASTP_IDENTITY_BY_GENOME"), ("by-class", "BLASTP_IDENTITY_BY_CLASS")])
def test_all_drawn_text_is_at_least_8_pt(world, figure, stem):
    out = world["tmp"] / f"pt_{figure}"
    assert _run(world, out, "--figure", figure, "--bar-counts") == 0
    runs = _text_runs(out / f"{stem}.pdf")
    assert runs
    small = sorted({(round(s, 2), t) for s, t in runs if s < 7.95})
    assert not small, small[:10]


@pytest.mark.parametrize("width", [7.2, 9.5])
def test_class_figure_fits_its_declared_print_width(world, width):
    out = world["tmp"] / f"w{width}"
    assert _run(world, out, "--figure", "by-class", "--print-width", str(width)) == 0
    w = float(pypdf.PdfReader(str(out / "BLASTP_IDENTITY_BY_CLASS.pdf")).pages[0].mediabox.width) / 72
    assert w <= width + 0.01
    assert json.loads((out / "RUN_INFO.json").read_text())["print_width_in"] == width
