"""Tests for tools/assembly_stats_table.py (card 452_assembly_stats_table)."""
import importlib.util, io, sys, zipfile
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "assembly_stats_table.py"
spec = importlib.util.spec_from_file_location("ast_tool", TOOL); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def _zip(tmp, contigs):
    p = tmp / "g.zip"
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("input/g.fasta", "".join(f">c{i}\n{s}\n" for i, s in enumerate(contigs)))
    return p


def test_n50_l50_and_1kb_count(tmp_path):
    z = _zip(tmp_path, ["G" * 5000, "A" * 3000, "C" * 1500, "T" * 500])
    r = m.stats(*m.zip_lengths(z))
    assert r["contigs"] == "4" and r["contigs_1kb"] == "3"
    assert r["n50_kb"] == "5.0" and r["l50"] == "1" and r["largest_kb"] == "5"
    assert r["size_mb"] == "0.01" and r["gc_pct"] == "65.0"
    assert r["sequence_source"].startswith("input FASTA")


def test_full_run_blank_completeness_and_refusal(tmp_path, monkeypatch):
    z = _zip(tmp_path, ["GC" * 2000, "AT" * 600])
    s = tmp_path / "s.tsv"; s.write_text(f"strain\tgenus\tgroup\tzip\nAS-1\tStreptomyces\tmoss\t{z}\n")
    monkeypatch.setattr(sys, "argv", ["x", "--strains", str(s), "--out", str(tmp_path / "o")])
    m.main()
    rows = (tmp_path / "o" / "ASSEMBLY_STATS.tsv").read_text().splitlines()
    assert rows[1].split("\t")[10] == ""            # no completeness given -> blank, never 0
    assert (tmp_path / "o" / "ASSEMBLY_STATS_TABLE.pdf").stat().st_size > 0
    monkeypatch.setattr(sys, "argv", ["x", "--strains", str(s), "--out", str(tmp_path / "o")])
    try:
        m.main(); assert False
    except SystemExit as e:
        assert "OUTPUT_EXISTS" in str(e)
