"""phylo_sequence_admission's CLI reports a refusal as ADMISSION_FAIL (exit 2) and never replaces a receipt.

A refusal raised ValueError out of main() as a traceback, and --json overwrote any existing file.
"""
import csv
import importlib.util
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("_admission_fixture_458c", ROOT / "tests" / "test_phylo_sequence_admission_v97429.py")
_fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fx)
_tool = importlib.util.spec_from_file_location("phylo_sequence_admission_458c", ROOT / "tools" / "phylo_sequence_admission.py")
adm = importlib.util.module_from_spec(_tool)
_tool.loader.exec_module(adm)


def _inputs(tmp_path, seq):
    row = _fx.row("R1", seq)
    roster = tmp_path / "roster.tsv"
    with open(roster, "w", newline="") as h:
        w = csv.DictWriter(h, fieldnames=list(row), delimiter="\t")
        w.writeheader()
        w.writerow(row)
    fasta = tmp_path / "seqs.fasta"
    fasta.write_text(f">R1\n{seq}\n")
    return roster, fasta


def test_refusal_is_typed_and_receipted(tmp_path, capsys):
    roster, fasta = _inputs(tmp_path, "A" * 173)        # too short for 16S
    out = tmp_path / "receipt.json"
    assert adm.main(["--roster", str(roster), "--fasta", str(fasta), "--json", str(out)]) == 2
    assert "ADMISSION_FAIL: SEQUENCE_LENGTH" in capsys.readouterr().err
    assert json.loads(out.read_text())["status"] == "ADMISSION_FAIL"


def test_existing_receipt_is_not_replaced(tmp_path, capsys):
    roster, fasta = _inputs(tmp_path, "A" * 1400)
    out = tmp_path / "receipt.json"
    out.write_text("earlier receipt")
    assert adm.main(["--roster", str(roster), "--fasta", str(fasta), "--json", str(out)]) == 2
    assert out.read_text() == "earlier receipt"
    assert "already exists" in capsys.readouterr().err


def test_pass_is_unchanged(tmp_path):
    roster, fasta = _inputs(tmp_path, "A" * 1400)
    out = tmp_path / "receipt.json"
    assert adm.main(["--roster", str(roster), "--fasta", str(fasta), "--json", str(out)]) == 0
    assert json.loads(out.read_text())["status"] == "ADMISSION_PASS"
