"""Every gold figure carries its <stem>_data.csv, including the seven D-series scatter plots and empty-state panels.

The house rule is that a figure traces to its data. Before .447 the gold scatter figures D03-D07, D10 and D11 wrote no
data CSV, and the empty-state placeholders of heatmap(), hmap() and bubble_matrix() wrote none either. With the seal
figure gate reading the figure folders (card a cut card), each would be a WARN
on every package.
"""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "examples" / "test_data" / "smoke_antismash_small.zip"


@pytest.mark.skipif(not SMOKE.exists(), reason="smoke antiSMASH ZIP not shipped")
def test_every_gold_figure_has_its_data_csv(tmp_path):
    pytest.importorskip("matplotlib")
    r = subprocess.run([sys.executable, str(ROOT / "mamey_run.py"), "run", "--strain", "P1", "--input-zip", str(SMOKE),
                        "--outdir", str(tmp_path / "out"), "--mode", "gold", "--capped-session", "--json-evidence", "off"],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=900)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    gold = next((tmp_path / "out").rglob("gold_figures"), None)
    if gold is None:
        pytest.skip("this run wrote no gold figures (figure stack absent)")
    pngs = sorted(gold.glob("*.png"))
    assert pngs
    missing = [p.name for p in pngs if not p.with_name(p.stem + "_data.csv").exists()]
    assert not missing, f"gold figures without a data CSV: {missing}"
    scatter = next(gold.glob("D03_scatter_size_vs_domains_data.csv"), None)
    if scatter is not None:
        assert scatter.read_text().splitlines()[0] == "strain,bgc_id,region_length_kb,total_domains"
