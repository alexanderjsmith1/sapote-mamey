"""Tests for tools/tygs_figures.py (card 018c0f08_452_tygs_figures). Parsing and selection only; drawing needs R."""
import importlib.util, sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "tygs_figures.py"
spec = importlib.util.spec_from_file_location("tygs_figures", TOOL)
tf = importlib.util.module_from_spec(spec); spec.loader.exec_module(tf)

TSV = ("comp_type\tquery_genome\tsubject_genome\tdigital_ddh_d0\tconfidence_interval_d0\tdigital_ddh_d4\tconfidence_interval_d4\t"
       "digital_ddh_d6\tconfidence_interval_d6\tpercent_gc_diff\n"
       "U vs. T\t'AS-1.fna'\tStreptomyces alpha DSM 1\t90\t[88 - 92]\t30.5\t[28.1 - 33.0]\t90\t[88 - 92]\t0.2\n"
       "U vs. T\t'AS-1.fna'\tStreptomyces beta DSM 2\t90\t[88 - 92]\t72.0\t[69.0 - 74.8]\t90\t[88 - 92]\t0.1\n"
       "U vs. U\t'AS-1.fna'\t'SYNTHETIC-CASE-002.fna'\t90\t[88 - 92]\t99.0\t[98 - 99.5]\t90\t[88 - 92]\t0.0\n")


def test_tsv_parse_and_user_vs_type(tmp_path):
    p = tmp_path / "t.tsv"; p.write_text(TSV)
    rows = tf.parse_tygs_tsv(str(p))
    assert len(rows) == 3
    assert rows[0]["query"] == "AS-1" and rows[0]["d4_lo"] == 28.1 and rows[0]["d4_hi"] == 33.0
    assert [r["user_vs_type"] for r in rows] == [True, True, False]


def test_missing_values_stay_missing():
    assert tf.num("NA") is None and tf.num("") is None and tf.num("n.d.") is None and tf.num("99.3") == 99.3


def test_closest_type_pick_ignores_user_vs_user(tmp_path, monkeypatch):
    p = tmp_path / "t.tsv"; p.write_text(TSV)
    s = tmp_path / "s.tsv"; s.write_text("isolate\tgenus\tgroup\tsimilarity\nAS-1\tStreptomyces\tMoss\tNA\n")
    out = tmp_path / "out"
    calls = []
    monkeypatch.setattr(tf.subprocess, "run", lambda *a, **k: calls.append(a))
    monkeypatch.setattr(sys, "argv", ["tygs_figures.py", "--tygs", str(p), "--strain-table", str(s), "--out", str(out),
                                      "--palette", str(p)])
    tf.main()
    data = (out / "T05_T06_data.tsv").read_text().splitlines()
    assert len(data) == 2 and "Streptomyces beta DSM 2" in data[1] and "\t72.0\t" in data[1]
    assert "1 genomes" in (out / "CAPTION.md").read_text() or "of each of the 1 genomes" in (out / "CAPTION.md").read_text()


def test_refuses_existing_output(tmp_path, monkeypatch):
    p = tmp_path / "t.tsv"; p.write_text(TSV); s = tmp_path / "s.tsv"; s.write_text("isolate\tgenus\nAS-1\tStreptomyces\n")
    (tmp_path / "out").mkdir()
    monkeypatch.setattr(sys, "argv", ["tygs_figures.py", "--tygs", str(p), "--strain-table", str(s), "--out", str(tmp_path / "out")])
    try:
        tf.main(); assert False
    except SystemExit as e:
        assert "OUTPUT_EXISTS" in str(e)
