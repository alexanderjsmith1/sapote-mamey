"""A ledger is a lane even when its directory lacks the historical RID spelling."""

from __future__ import annotations

import csv
import datetime as dt
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools" / "blastp_monitoring"


def _lane(tmp_path: Path, name: str, panel: str, stamp: str,
          *, strain: str = "TEST", n_seqs: int = 1) -> None:
    lane = tmp_path / "Blastp RESULTS" / name
    lane.mkdir(parents=True)
    with (lane / "_ledger.csv").open("w", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=(
            "strain", "bgc", "file", "rid", "rtoe", "submit_iso", "status", "fetch_iso", "note"))
        writer.writeheader()
        writer.writerow({"strain": strain, "bgc": "", "file": f"{strain}/{panel}",
                         "rid": "TEST", "status": "fetched", "fetch_iso": stamp,
                         "submit_iso": stamp, "note": "1 row"})
    query = tmp_path / "Blastp RESULTS" / "_QUERIES_TEST" / strain / panel
    query.parent.mkdir(parents=True, exist_ok=True)
    query.write_text("".join(f">query_{i}\nMAA\n" for i in range(n_seqs)))


def _fixture(tmp_path: Path) -> tuple[str, ...]:
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    names = ("_NR_RID_LEGACY", "_STRAINGAP_CLNR_TEST", "_REDIV_RID_NR_TEST")
    for index, name in enumerate(names):
        _lane(tmp_path, name, f"panel_{index}.faa", stamp)
    return names


def test_recent_plot_discovers_all_lanes_and_keeps_channels_distinct(tmp_path, monkeypatch):
    names = _fixture(tmp_path)
    monkeypatch.chdir(tmp_path)
    spec = importlib.util.spec_from_file_location("blastp_plot_recent_test", TOOLS / "plot_crawl_recent.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    rows = module.load_fetches()
    assert {row[3] for row in rows} == set(names)
    assert {row[3]: row[2] for row in rows}["_STRAINGAP_CLNR_TEST"] == "ClusteredNR"
    assert sum(row[1] for row in rows) == 3


def test_last_returns_includes_new_lane_names(tmp_path):
    names = _fixture(tmp_path)
    env = {**os.environ, "SAPOTE_WORKSPACE_ROOT": str(tmp_path)}
    result = subprocess.run([sys.executable, str(TOOLS / "blastp_last_returns.py"),
                             "--last", "10"], env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert all(name in result.stdout for name in names)
    assert "3 shown" in result.stdout


def test_24_96h_plot_discovers_clnr_lane(tmp_path):
    _fixture(tmp_path)
    out = tmp_path / "plots"
    out.mkdir()
    env = {**os.environ, "SAPOTE_WORKSPACE_ROOT": str(tmp_path),
           "SAPOTE_BLASTP_PLOT_DIR": str(out), "MPLBACKEND": "Agg"}
    result = subprocess.run([sys.executable, str(TOOLS / "plot_crawl_proteins_24_96h.py")],
                            env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ClusteredNR" in result.stdout
    assert sum("Trailing 24 h: 1 proteins (1 panels)" in line
               for line in result.stdout.splitlines()) == 3
    assert (out / "blastp_throughput_proteins_24_96h.svg").exists()


def test_same_basename_in_two_strains_keeps_distinct_protein_counts(tmp_path, monkeypatch):
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _lane(tmp_path, "_NR_RID_A", "panel.faa", stamp, strain="STRAIN_A", n_seqs=1)
    _lane(tmp_path, "_STRAINGAP_CLNR_B", "panel.faa", stamp, strain="STRAIN_B", n_seqs=3)
    monkeypatch.chdir(tmp_path)
    spec = importlib.util.spec_from_file_location("blastp_recent_collision_test", TOOLS / "plot_crawl_recent.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    rows = module.load_fetches()
    assert {row[3]: row[1] for row in rows} == {"_NR_RID_A": 1, "_STRAINGAP_CLNR_B": 3}
    env = {**os.environ, "SAPOTE_WORKSPACE_ROOT": str(tmp_path),
           "SAPOTE_BLASTP_PLOT_DIR": str(tmp_path), "MPLBACKEND": "Agg"}
    result = subprocess.run([sys.executable, str(TOOLS / "plot_crawl_proteins_24_96h.py")],
                            env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "nr A" in result.stdout and "1 proteins" in result.stdout
    assert "ClusteredNR STRAINGAP CLNR B" in result.stdout and "3 proteins" in result.stdout


def test_conflicting_same_relative_path_is_not_silently_admitted(tmp_path, monkeypatch):
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _lane(tmp_path, "_NR_RID_A", "panel.faa", stamp, strain="STRAIN_A", n_seqs=1)
    duplicate = tmp_path / "Blastp RESULTS" / "_QUERIES_OTHER" / "STRAIN_A" / "panel.faa"
    duplicate.parent.mkdir(parents=True)
    duplicate.write_text(">different_1\nMAA\n>different_2\nMAA\n")
    monkeypatch.chdir(tmp_path)
    spec = importlib.util.spec_from_file_location("blastp_recent_ambiguous_test", TOOLS / "plot_crawl_recent.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    assert module.load_fetches()[0][1] == 0
    assert module._UNKNOWN_PANELS["STRAIN_A/panel.faa"] == "conflicting copies across query roots"
