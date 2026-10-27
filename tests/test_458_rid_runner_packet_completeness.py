"""The RID runner records which genes a result packet holds and whether it is complete.

A packet's CSV grows as each query batch for it returns; a reader that hashed it early bound a partial
packet. `_result_generation.json` now lists genes_done and genes_expected and says complete only when
every expected gene is in, including genes with no hits.
"""
import importlib.util
import json
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools/blastp_crawl/nr_rid_runner.py"


def _load(monkeypatch, tmp_path):
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("RID_DATABASE", "nr_cluster_seq")
    monkeypatch.setenv("RID_QUERIES", "_QUERIES_T")
    monkeypatch.setenv("RID_BASE", "_LANE_T")
    spec = importlib.util.spec_from_file_location("rid_runner_458", SCRIPT)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod


def _row(mod, gene):
    return ["AS-9001", "AS-9001_gapK_p0001", gene] + [""] * (len(mod.OUT_COLS) - 3)


def test_packet_is_complete_only_when_every_gene_is_in(monkeypatch, tmp_path):
    m = _load(monkeypatch, tmp_path)
    q = m.QUERIES / "AS-9001" / "AS-9001_gapK_p0001"; q.mkdir(parents=True)
    (q / "b01.faa").write_text(">ctg1_1\nMSTN\n>ctg2_7\nMKTA\n")
    gen = m.RESDIR / "AS-9001" / "AS-9001_gapK_p0001" / "_result_generation.json"

    m.write_results("AS-9001", "AS-9001_gapK_p0001", [_row(m, "ctg1_1")], replace_genes={"ctg1_1"})
    first = json.loads(gen.read_text())
    assert first["genes_expected"] == ["ctg1_1", "ctg2_7"]
    assert first["genes_done"] == ["ctg1_1"] and first["complete"] is False

    m.write_results("AS-9001", "AS-9001_gapK_p0001", [], replace_genes={"ctg2_7"})   # finished with no hits
    second = json.loads(gen.read_text())
    assert second["genes_done"] == ["ctg1_1", "ctg2_7"] and second["complete"] is True
