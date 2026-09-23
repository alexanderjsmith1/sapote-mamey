import datetime as dt
import json
from pathlib import Path
import runpy
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pytest
import importlib.util
_spec = importlib.util.spec_from_file_location("lane_fixture", Path(__file__).with_name("test_blastp_monitoring_lane_discovery_433.py"))
_fixture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fixture)
_lane = _fixture._lane

SCRIPT = Path(__file__).resolve().parents[1] / "tools/blastp_monitoring/plot_crawl_proteins_24_96h.py"


def run_plot(tmp_path, monkeypatch, *args):
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("SAPOTE_BLASTP_PLOT_DIR", str(tmp_path))
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), *args])
    monkeypatch.setattr(matplotlib.figure.Figure, "savefig", lambda *a, **k: None)
    state = runpy.run_path(str(SCRIPT), run_name="__main__")
    return state


def test_default_preserves_quiet_lane_and_records_exclusions(tmp_path, monkeypatch):
    old = (dt.datetime.now()-dt.timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
    for name in ("_NR_RID_QUIET", "_ARCHIVE_SUPERSEDED_OLD", "_SINGLE_CLNR_COMPLETE"):
        _lane(tmp_path,name,name+".faa",old)
    state=run_plot(tmp_path,monkeypatch)
    assert len(state["data"]) == 1 and "nr QUIET" in state["data"]
    receipt=json.loads((tmp_path/"blastp_throughput_proteins_24_96h.selection.json").read_text())
    assert sum(row["included"] for row in receipt["lanes"]) == 1
    plt.close(state["fig"])


def test_all_and_recency_are_separate_explicit_choices(tmp_path,monkeypatch):
    old=(dt.datetime.now()-dt.timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
    _lane(tmp_path,"_SINGLE_CLNR_COMPLETE","one.faa",old)
    state=run_plot(tmp_path,monkeypatch,"--all")
    assert len(state["data"]) == 1
    plt.close(state["fig"])
    state=run_plot(tmp_path,monkeypatch,"--all","--active-hours","24")
    assert not state["data"]
    plt.close(state["fig"])


def test_pending_single_set_is_not_hidden_as_complete(tmp_path,monkeypatch):
    stamp=dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _lane(tmp_path,"_SINGLE_CLNR_PENDING","one.faa",stamp)
    ledger=tmp_path/"Blastp RESULTS/_SINGLE_CLNR_PENDING/_ledger.csv"
    ledger.write_text(ledger.read_text().replace("fetched","waiting"))
    state=run_plot(tmp_path,monkeypatch)
    assert len(state["data"]) == 1
    plt.close(state["fig"])


def test_dense_legend_is_outside_data_and_unknown_counts_are_labeled(tmp_path,monkeypatch):
    stamp=dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for i in range(22):
        _lane(tmp_path,f"_NR_RID_GENERIC_LONG_LANE_LABEL_{i:02}",f"panel{i}.faa",stamp)
    (tmp_path/"Blastp RESULTS/_QUERIES_TEST/TEST/panel0.faa").unlink()
    state=run_plot(tmp_path,monkeypatch)
    fig=state["fig"];fig.canvas.draw();renderer=fig.canvas.get_renderer()
    assert len(fig.legends)==1
    assert "≥0" in fig.legends[0].get_texts()[0].get_text()
    assert len(state["axes"][0][0].lines[1].get_xdata()) == 3
    assert list(state["axes"][0][0].lines[1].get_ydata()) == [0, 1, 1]
    box=fig.legends[0].get_window_extent(renderer)
    assert all(not box.overlaps(ax.get_window_extent(renderer)) for ax in fig.axes)
    assert fig.bbox.contains(box.x0,box.y0) and fig.bbox.contains(box.x1,box.y1)
    assert any("LOWER BOUNDS" in t.get_text() for t in fig.texts)
    colors = [color for _comps, color in state["data"].values()]
    assert len(colors) == len(set(colors)) == 22
    bars = sorted(state["axes"][1][0].patches, key=lambda bar: bar.get_x())
    assert len(bars) == 22
    assert all(
        left.get_x() + left.get_width() <= right.get_x() + 1e-12
        for left, right in zip(bars, bars[1:])
    )
    plt.close(fig)


def test_prettified_label_collision_preserves_both_lanes(tmp_path,monkeypatch):
    stamp=dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for i,name in enumerate(("_NR_RID_A","NR_RID_A")):
        _lane(tmp_path,name,f"panel{i}.faa",stamp)
    state=run_plot(tmp_path,monkeypatch)
    assert len(state["data"]) == 2
    plt.close(state["fig"])


def test_timezone_label_comes_from_runtime_locale(tmp_path, monkeypatch):
    stamp=dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _lane(tmp_path,"_NR_RID_TIMEZONE","panel.faa",stamp)
    state=run_plot(tmp_path,monkeypatch)
    label=state["TIMEZONE_LABEL"]
    assert label and label in state["axes"][0][0].get_title()
    assert label in state["axes"][1][0].get_xlabel()
    source=SCRIPT.read_text(encoding="utf-8")
    assert "%H:%M} PDT" not in source
    assert '"time (PDT)"' not in source
    plt.close(state["fig"])
