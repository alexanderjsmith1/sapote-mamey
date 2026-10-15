"""Card 018c0f08_452_sixteen_s_identity_all_records_unambiguous.

Two defects made 16S similarity to the nearest type strain read low:
- the nearest-record search capped BLAST at 10 subjects (comparator_select at max(top*6, 30)). BLAST keeps the first N
  subjects in its own order, not the N most identical, so the nearest type strain in a large genus could be missed;
- BLAST pident counts every IUPAC ambiguity code as a mismatch, so partial Sanger reads with ambiguous calls lost points.
The tools now search every record (-max_target_seqs = the database's sequence count) and report identity over the
columns where both sequences carry A, C, G, T or a gap. Hermetic: fake BLAST programs.
"""
import csv
import importlib.util
import stat
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
GUIDE = ROOT / "docs" / "LOCAL_16S_DATABASE.md"

CLEAN = "ACGT" * 25                      # 100 columns
AMBIG = "ACNT" + "ACGT" * 23 + "ACGN"    # the same read with 2 ambiguous calls
ONE_OFF = "ACGA" + "ACGT" * 24           # one real mismatch against CLEAN


def _load(name, alias):
    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))
    spec = importlib.util.spec_from_file_location(alias, TOOLS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[alias] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def p16():
    return _load("_phylo16s", "_phylo16s_t452amb")


def _exe(path: Path, body: str):
    path.write_text("#!/bin/sh\n" + body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _fake_bin(d: Path, log: Path, qcols: bool = True):
    """blastdbcmd reports 1,234 records; blastn logs its arguments and returns two subjects:
    A (raw 98.00, the query's 2 ambiguous calls are its only differences) and B (raw 99.00, one real mismatch)."""
    d.mkdir()
    _exe(d / "blastdbcmd",
         'case "$*" in\n'
         '  *-info*) printf "Database: fake type strains\\n\\t1,234 sequences; 1400 total bases\\n";;\n'
         '  *"-entry all"*) printf "NR_1.1\\tGenusa speciesa strain A1 16S\\nNR_2.1\\tGenusa speciesb strain B1 16S\\n";;\n'
         '  *) out=""; prev=""; for a in "$@"; do [ "$prev" = "-out" ] && out="$a"; prev="$a"; done;\n'
         '     printf ">NR_1.1\\nACGT\\n" > "$out";;\n'
         "esac\n")
    tail = f"\\t{AMBIG}\\t{CLEAN}" if qcols else ""
    tail_b = f"\\t{CLEAN}\\t{ONE_OFF}" if qcols else ""
    _exe(d / "blastn",
         f'echo "$*" >> "{log}"\n'
         'case "$*" in\n'
         f'  *-subject*) printf "98.00\\t100\\t180{tail}\\n";;\n'
         '  *-perc_identity*) [ -n "$FAKE_EMPTY_WITH_FLOOR" ] && exit 0;\n'
         f'     printf "98.00\\t100\\t100\\t180\\tGenusa speciesa strain A1 16S{tail}\\n'
         f'99.00\\t100\\t100\\t190\\tGenusa speciesb strain B1 16S{tail_b}\\n";;\n'
         f'  *) printf "98.00\\t100\\t100\\t180\\tGenusa speciesa strain A1 16S{tail}\\n'
         f'99.00\\t100\\t100\\t190\\tGenusa speciesb strain B1 16S{tail_b}\\n";;\n'
         "esac\n")


# ---------------------------------------------------------------- the shared helpers
def test_unambiguous_identity_drops_iupac_columns_in_either_sequence(p16):
    assert p16.unambiguous_identity(AMBIG, CLEAN) == (100.0, 2)
    assert p16.unambiguous_identity(CLEAN, AMBIG) == (100.0, 2)
    assert p16.unambiguous_identity(CLEAN, ONE_OFF) == (99.0, 0)
    assert p16.unambiguous_identity("RYKM", "ACGT") == (None, 4)


def test_gaps_still_count_as_differences(p16):
    ident, dropped = p16.unambiguous_identity("ACG-T", "ACGAT")
    assert dropped == 0 and ident == pytest.approx(80.0)


def test_record_count_comes_from_blastdbcmd_info(p16, tmp_path):
    _fake_bin(tmp_path / "bin", tmp_path / "log")
    assert p16.blastdb_sequence_count("db", str(tmp_path / "bin" / "blastdbcmd")) == 1234
    assert p16.blastdb_sequence_count("db", str(tmp_path / "missing_blastdbcmd")) is None


# ---------------------------------------------------------------- the similarity check
def _run_check(tmp_path, monkeypatch, qcols=True, empty_with_floor=False):
    log = tmp_path / "blastn_args.log"
    _fake_bin(tmp_path / "bin", log, qcols)
    if empty_with_floor:
        monkeypatch.setenv("FAKE_EMPTY_WITH_FLOOR", "1")
    (tmp_path / "q.fa").write_text(f">STR-1 isolate\n{AMBIG}\n")
    (tmp_path / "t.tsv").write_text("strain\tgenus_16s\tclosest_type_strain\tsimilarity_percent\n"
                                    "STR-1\tGenusa sp.\tG. speciesa\t99.9\n")
    mod = _load("sixteen_s_similarity_check", "sixteen_s_t452amb")
    out = tmp_path / "check.tsv"
    assert mod.main(["--fasta", str(tmp_path / "q.fa"), "--table", str(tmp_path / "t.tsv"), "--db", "fakedb",
                     "--blast-bin", str(tmp_path / "bin"), "--out", str(out)]) == 0
    return list(csv.DictReader(open(out), delimiter="\t"))[0], log.read_text(), out


def test_nearest_search_covers_every_record(tmp_path, monkeypatch):
    row, log, out = _run_check(tmp_path, monkeypatch)
    nearest_calls = [ln for ln in log.splitlines() if "-subject" not in ln]
    assert nearest_calls and all("-max_target_seqs 1234" in ln for ln in nearest_calls)
    assert "-max_target_seqs 10 " not in log
    import json
    assert json.loads(Path(str(out) + ".receipt.json").read_text())["max_target_seqs"] == 1234


def test_raw_and_unambiguous_readings_are_both_reported(tmp_path, monkeypatch):
    row, _, _ = _run_check(tmp_path, monkeypatch)
    assert row["query_ambiguous_bp"] == "2"
    assert (row["nearest_identity"], row["nearest_title"]) == ("99.00", "Genusa speciesb strain B1 16S")
    assert (row["nearest_identity_unambiguous"], row["nearest_title_unambiguous"]) == ("100.00", "Genusa speciesa strain A1 16S")
    assert row["identity_to_deposited_species"] == "98.00"
    assert row["identity_to_deposited_species_unambiguous"] == "100.00"


def test_rows_without_sequences_fall_back_to_pident(tmp_path, monkeypatch):
    row, _, _ = _run_check(tmp_path, monkeypatch, qcols=False)
    assert row["nearest_identity_unambiguous"] == row["nearest_identity"] == "99.00"


def test_search_reruns_without_the_floor_when_nothing_passes(tmp_path, monkeypatch):
    row, log, _ = _run_check(tmp_path, monkeypatch, empty_with_floor=True)
    nearest_calls = [ln for ln in log.splitlines() if "-subject" not in ln]
    assert len(nearest_calls) == 2 and "-perc_identity" in nearest_calls[0] and "-perc_identity" not in nearest_calls[1]
    assert row["nearest_identity"] == "99.00"


# ---------------------------------------------------------------- comparator_select
def test_comparator_select_searches_every_record_and_ranks_by_unambiguous_identity(tmp_path):
    log = tmp_path / "blastn_args.log"
    _fake_bin(tmp_path / "bin", log)
    # comparator_select's outfmt puts qseqid sacc first and qstart qend evalue before bitscore
    _exe(tmp_path / "bin" / "blastn",
         f'echo "$*" >> "{log}"\n'
         f'printf "Q1\\tNR_2.1\\t99.00\\t100\\t100\\t1\\t100\\t0\\t190\\tGenusa speciesb strain B1 16S\\t{CLEAN}\\t{ONE_OFF}\\n'
         f'Q1\\tNR_1.1\\t98.00\\t100\\t100\\t1\\t100\\t0\\t180\\tGenusa speciesa strain A1 16S\\t{AMBIG}\\t{CLEAN}\\n"\n')
    (tmp_path / "q.fa").write_text(f">Q1\n{AMBIG}\n")
    cs = _load("comparator_select", "comparator_select_t452amb")
    rows = cs.run_blastn(tmp_path / "q.fa", Path("fakedb"), tmp_path / "bin" / "blastn", top=1)
    assert "-max_target_seqs 1234" in log.read_text()
    picks = cs.per_query(rows, [], n_named=2)[0]["picks"]
    assert [p["sp"] for p in picks] == ["speciesa", "speciesb"]
    assert picks[0]["pident"] == 100.0 and picks[0]["pident_raw"] == 98.0


# ---------------------------------------------------------------- the guide
def test_guide_states_the_identity_rule_and_the_methods_line():
    text = GUIDE.read_text()
    assert "## How identity is measured" in text
    assert "sixteen_s_similarity_check.py" in text and "comparator_select.py" in text
    assert "nearest_identity_unambiguous" in text and "query_ambiguous_bp" in text
    assert "computed over unambiguous positions, across every record in the database" in text
