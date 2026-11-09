"""plot_examples: existing PNGs are refused, and an isolate with no class rows is not drawn as zeros.

Before: the three PNGs were written into the input folder under fixed names and replaced on every
run, and the heatmap filled every absent class x isolate cell with 0, including isolates that have
no row at all in class_by_strain.csv.
"""
import csv
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "plot_examples.py"


def _write(d, name, header, rows):
    with open(d / name, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=header)
        w.writeheader()
        w.writerows(rows)


def _inputs(d):
    _write(d, "strain_summary.csv", ["strain", "assembly_tier", "n50", "fragmentation_loss"], [
        {"strain": "REF-1", "assembly_tier": "GOOD", "n50": "250000", "fragmentation_loss": "0"},
        {"strain": "REF-2", "assembly_tier": "POOR", "n50": "12000", "fragmentation_loss": "3"}])
    _write(d, "class_by_strain.csv", ["strain", "product_class", "n_bgcs"], [
        {"strain": "REF-1", "product_class": "NRPS", "n_bgcs": "4"}])
    _write(d, "class_prevalence.csv", ["product_class", "n_strains", "band"], [
        {"product_class": "NRPS", "n_strains": "1", "band": "UNIQUE"}])


def _run(*args):
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True,
                          env=dict(os.environ, MPLBACKEND="Agg"), cwd=str(ROOT))


def test_unrecorded_isolate_is_reported_and_rerun_is_refused(tmp_path):
    _inputs(tmp_path)
    first = _run(str(tmp_path))
    assert first.returncode == 0, first.stderr[-400:]
    assert "1 isolate(s) have no class_by_strain rows" in first.stdout
    png = tmp_path / "fig3_class_by_strain_heatmap.png"
    before = png.read_bytes()
    again = _run(str(tmp_path))
    assert again.returncode == 2 and "OUTPUT_REFUSED" in again.stderr
    assert png.read_bytes() == before


def test_out_dir_keeps_the_input_folder_clean(tmp_path):
    src = tmp_path / "figure_ready"
    src.mkdir()
    _inputs(src)
    out = tmp_path / "figs"
    proc = _run(str(src), "--out-dir", str(out))
    assert proc.returncode == 0, proc.stderr[-400:]
    assert sorted(p.name for p in out.iterdir()) == [
        "fig1_fragmentation_gradient.png", "fig2_class_prevalence.png", "fig3_class_by_strain_heatmap.png"]
    assert not any(p.suffix == ".png" for p in src.iterdir())
