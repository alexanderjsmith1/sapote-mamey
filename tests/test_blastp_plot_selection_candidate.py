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
    # All 22 lanes fetched in the same hour: one full-hour bar, stacked 22 segments high.
    bars = sorted(state["axes"][1][0].patches, key=lambda bar: bar.get_y())
    assert len(bars) == 22
    assert len({round(bar.get_x(), 9) for bar in bars}) == 1
    assert all(abs(bar.get_width() - 0.9 / 24) < 1e-9 for bar in bars)
    running = 0
    for bar in bars:
        assert abs(bar.get_y() - running) < 1e-9
        running += bar.get_height()
    assert running == 21  # panel0.faa was removed above, so that lane counts 0
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


def test_strain_lanes_get_short_one_line_labels(tmp_path, monkeypatch):
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _lane(tmp_path, "_STRAINGAP_SINGLE_CLNR_GAP_AS932", "panel0.faa", stamp)
    _lane(tmp_path, "_NR_RID_AS-40", "panel1.faa", stamp)
    state = run_plot(tmp_path, monkeypatch)
    fig = state["fig"]
    texts = [t.get_text() for t in fig.legends[0].get_texts()]
    assert any(t.startswith("AS-932 — ") for t in texts)
    assert any(t.startswith("AS-40 nr — ") for t in texts)
    assert all("\n" not in t for t in texts)
    plt.close(fig)


def test_same_strain_in_two_lanes_keeps_both_distinct(tmp_path, monkeypatch):
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _lane(tmp_path, "_STRAINGAP_SINGLE_CLNR_AS190", "panel0.faa", stamp)
    _lane(tmp_path, "_STRAINGAP_SINGLE_CLNR_GAP_AS190", "panel1.faa", stamp)
    state = run_plot(tmp_path, monkeypatch)
    names = list(state["data"])
    assert len(names) == 2 and len(set(names)) == 2
    assert all(name.startswith("AS-190 [") for name in names)
    plt.close(state["fig"])


def test_selection_receipt_records_stacked_bars(tmp_path, monkeypatch):
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _lane(tmp_path, "_STRAINGAP_SINGLE_CLNR_GAP_AS1", "panel0.faa", stamp)
    state = run_plot(tmp_path, monkeypatch)
    receipt = json.loads((tmp_path / "blastp_throughput_proteins_24_96h.selection.json").read_text())
    assert receipt["hourly_bar_layout"] == "stacked"
    plt.close(state["fig"])


def test_default_plot_folder_inside_the_bundle_is_refused(tmp_path, monkeypatch):
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _lane(tmp_path, "_STRAINGAP_SINGLE_CLNR_GAP_AS1", "panel0.faa", stamp)
    bundle = SCRIPT.parents[2]
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.delenv("SAPOTE_BLASTP_PLOT_DIR", raising=False)
    monkeypatch.chdir(bundle)
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    from mamey.path_safety import OutputInsideBundle
    with pytest.raises(OutputInsideBundle):
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert not (bundle / "blastp_throughput_proteins_24_96h.png").exists()
    plt.close("all")
