"""phylo_sequence_admission: a roster or FASTA that cannot be read is a typed ADMISSION_ERROR with
exit 2 and a receipt, not a FileNotFoundError traceback; a validation refusal stays ADMISSION_FAIL."""
import json
import subprocess
import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "phylo_sequence_admission.py"


def _run(*args):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)], text=True, capture_output=True)


def test_missing_roster_is_a_typed_error_with_receipt(tmp_path):
    fasta = tmp_path / "s.fasta"
    fasta.write_text(">q\nACGT\n")
    receipt = tmp_path / "r.json"
    r = _run("--roster", tmp_path / "nope.tsv", "--fasta", fasta, "--json", receipt)
    assert r.returncode == 2 and "Traceback" not in r.stderr
    assert "ADMISSION_ERROR: input could not be read" in r.stderr
    data = json.loads(receipt.read_text())
    assert data["status"] == "ADMISSION_ERROR" and data["rows"] is None


def test_missing_fasta_is_a_typed_error(tmp_path):
    roster = tmp_path / "r.tsv"
    roster.write_text("tip\trole\n")
    r = _run("--roster", roster, "--fasta", tmp_path / "nope.fasta")
    assert r.returncode == 2 and "ADMISSION_ERROR" in r.stderr and "Traceback" not in r.stderr
    assert json.loads(r.stdout)["status"] == "ADMISSION_ERROR"


def test_duplicate_fasta_header_is_still_a_validation_failure(tmp_path):
    roster = tmp_path / "r.tsv"
    roster.write_text("tip\trole\n")
    fasta = tmp_path / "s.fasta"
    fasta.write_text(">q\nACGT\n>q\nACGT\n")
    r = _run("--roster", roster, "--fasta", fasta)
    assert r.returncode == 2 and json.loads(r.stdout)["status"] == "ADMISSION_FAIL"
