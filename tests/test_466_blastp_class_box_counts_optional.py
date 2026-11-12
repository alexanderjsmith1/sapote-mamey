"""blastp_identity_figures by-class: `--no-box-counts` leaves out the genes-with-a-hit count above each box and the
title's note about it; the counts stay in the numbers table, and RUN_INFO records the choice. Uses the synthetic world
of test_451_blastp_identity_figures."""
import csv
import importlib.util
import json
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("_t451_boxc", Path(__file__).with_name("test_451_blastp_identity_figures.py"))
_t451 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_t451)
_run, world = _t451._run, _t451.world  # world is the 451 card's pytest fixture, reused here

pypdf = pytest.importorskip("pypdf")


def _text(pdf):
    return [t.strip() for p in pypdf.PdfReader(str(pdf)).pages for t in p.extract_text().split("\n") if t.strip()]


def test_box_counts_are_drawn_by_default(world):
    out = world["tmp"] / "boxc_default"
    assert _run(world, out, "--figure", "by-class") == 0
    assert "numbers above" in " ".join(_text(out / "BLASTP_IDENTITY_BY_CLASS.pdf"))
    assert json.loads((out / "RUN_INFO.json").read_text())["box_counts"] is True


def _box_count_calls(monkeypatch):
    """Record every Axes.text call drawn at the box-count height (y = 101.5)."""
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.axes import Axes
    calls, real = [], Axes.text

    def spy(self, x, y, s, *args, **kwargs):
        if y == 101.5:
            calls.append(s)
        return real(self, x, y, s, *args, **kwargs)
    monkeypatch.setattr(Axes, "text", spy)
    return calls


def test_no_box_counts_drops_the_counts_and_the_note_but_keeps_the_table(world, monkeypatch):
    on, off = world["tmp"] / "boxc_on", world["tmp"] / "boxc_off"
    calls = _box_count_calls(monkeypatch)
    assert _run(world, on, "--figure", "by-class") == 0
    drawn_on = len(calls)
    assert _run(world, off, "--figure", "by-class", "--no-box-counts") == 0
    assert drawn_on > 0 and len(calls) == drawn_on      # counts drawn without the flag, none added with it
    t_off = _text(off / "BLASTP_IDENTITY_BY_CLASS.pdf")
    assert "numbers above" not in " ".join(t_off)
    assert json.loads((off / "RUN_INFO.json").read_text())["box_counts"] is False
    assert (on / "BLASTP_IDENTITY_BY_CLASS_numbers.tsv").read_text() == (off / "BLASTP_IDENTITY_BY_CLASS_numbers.tsv").read_text()
