"""tools/bgc_figures.py: genes without a recorded identity are not 0 %, every gene is in the CSV,
existing outputs are refused, and distance 0 is not called identical."""
import csv
import importlib.util
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "bgc_figures.py"
spec = importlib.util.spec_from_file_location("bgc_figures_464r3", TOOL)
bf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bf)


def test_unmeasured_genes_keep_their_state_and_get_no_bar(tmp_path):
    pytest.importorskip("matplotlib")
    blastp = {"g1": {"defn": "synthase", "domains": "", "pid": 80.0, "evalue": "1e-50"},
              "g2": {"defn": "hypothetical protein", "domains": "", "pid": None, "evalue": ""}}
    png, data = tmp_path / "f3.png", tmp_path / "f3.csv"
    assert bf.fig_blastp(blastp, ["g1", "g2", "g3"], "t", str(png), str(data))
    rows = {r["locus_tag"]: r for r in csv.DictReader(data.open())}
    assert set(rows) == {"g1", "g2", "g3"}
    assert rows["g1"]["identity_state"] == "MEASURED"
    assert rows["g2"]["identity_state"] == "NO_IDENTITY_RECORDED" and rows["g2"]["pct_identity"] == ""
    assert rows["g3"]["identity_state"] == "NOT_IN_BLASTP_TABLE"


def test_blank_identity_in_panel_is_not_zero(tmp_path):
    panel = tmp_path / "panel.csv"
    panel.write_text("locus_tag,pct_identity,blastp_top_def\ng1,,x\n")
    assert bf.load_blastp(str(panel))["g1"]["pid"] is None


def test_existing_output_is_refused_before_any_write(tmp_path, capsys):
    gbk = tmp_path / "region.gbk"
    gbk.write_text("LOCUS       r 10 bp DNA\nORIGIN\n        1 acgtacgtac\n//\n")
    out = tmp_path / "figs"; out.mkdir()
    existing = out / "EX_BGC001_fig1_locus.png"
    existing.write_bytes(b"keep me")
    rc = bf.main(["--gbk", str(gbk), "--bgc", "BGC001", "--strain", "EX", "--outdir", str(out)])
    assert rc == 2
    assert existing.read_bytes() == b"keep me"
    assert not (out / "EX_BGC001_fig1_locus_data.csv").exists()
    assert "refused" in capsys.readouterr().err


def test_distance_axis_does_not_say_identical():
    assert "0 identical" not in TOOL.read_text()
