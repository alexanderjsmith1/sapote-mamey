"""Operator TSVs neutralise spreadsheet formulas from paths and source text."""
import csv
import json
from pathlib import Path
from types import SimpleNamespace
import zipfile

from tools import antismash_strictness_census as census
from tools import figure_render_qc as figure_qc
from tools import region_table_one_setting as region_table
from tools import sixteen_s_similarity_check as similarity

PAYLOAD = "=HYPERLINK(A1,B1)"


def _rows(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def test_strictness_census_sanitizes_result_name(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source = Path("=SUM(1+1).zip")
    with zipfile.ZipFile(source, "w") as archive:
        archive.writestr("results.json", json.dumps({"records": [{"modules": {
            "antismash.detection.hmm_detection": {"strictness": "strict"}}}]}))
    out = tmp_path / "census.tsv"
    assert census.main([str(source), "--tsv", str(out)]) == 0
    assert _rows(out)[0]["result"] == "'" + source.name


def test_figure_qc_sanitizes_drawn_text_flag(tmp_path):
    out = tmp_path / "qc"
    figure_qc.write_reports([(tmp_path / "plot.png", [("error", PAYLOAD)])], out, [tmp_path])
    assert _rows(out / "RENDER_QC.tsv")[0]["flag"] == "'" + PAYLOAD


def test_region_table_sanitizes_product(tmp_path, monkeypatch):
    monkeypatch.setattr(region_table, "find_zips", lambda inputs: [tmp_path / "synthetic.zip"])
    rows = [{"strain": "SYNTH-1", "strictness": "strict", "record": "NODE_1",
             "region_file": "NODE_1.region001.gbk", "products": PAYLOAD,
             "contig_edge": "interior", "zip_sha256": "0" * 64}]
    receipt = [{"strain": "SYNTH-1", "status": "kept", "n_dropped": 0}]
    monkeypatch.setattr(region_table, "build", lambda *args: (rows, receipt, []))
    out = tmp_path / "regions.tsv"
    assert region_table.main(["--zips", str(tmp_path), "--strictness", "strict",
                              "--out", str(out), "--no-exclusions"]) == 0
    assert _rows(out)[0]["products"] == "'" + PAYLOAD


def test_sixteen_s_similarity_sanitizes_blast_title(tmp_path, monkeypatch):
    fasta = tmp_path / "q.fa"
    fasta.write_text(">SYNTH-1\nACGT\n")
    table = tmp_path / "table.tsv"
    table.write_text("strain\tgenus_16s\tclosest_type_strain\tsimilarity_percent\n"
                     "SYNTH-1\tStreptomyces sp.\tS. griseus\t99\n")
    def fake_run(args, **kwargs):
        if "blastdbcmd" in str(args[0]) and "all" in args:
            return SimpleNamespace(stdout="ACC\tStreptomyces griseus hit\n", returncode=0)
        if "blastn" in str(args[0]) and "-subject" in args:
            return SimpleNamespace(stdout="99\t4\t200\n", returncode=0)
        if "blastn" in str(args[0]):
            return SimpleNamespace(stdout=f"99\t4\t4\t200\t{PAYLOAD}\n", returncode=0)
        return SimpleNamespace(stdout="", returncode=0)
    monkeypatch.setattr(similarity.subprocess, "run", fake_run)
    out = tmp_path / "similarity.tsv"
    assert similarity.main(["--fasta", str(fasta), "--table", str(table),
                            "--db", "synthetic-db", "--out", str(out)]) == 0
    assert _rows(out)[0]["nearest_title"] == "'" + PAYLOAD
