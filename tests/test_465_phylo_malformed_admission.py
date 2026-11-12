"""Malformed admission inputs must yield typed refusal receipts."""
import csv
import json
import subprocess
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/phylo_sequence_admission.py"

@pytest.mark.parametrize("case", ["empty_header", "short_row"])
def test_malformed_input_is_receipted_refusal(tmp_path, case):
    sys.path.insert(0, str(ROOT / "tools"))
    from phylo_sequence_admission import REQUIRED
    roster, fasta, receipt = (tmp_path / x for x in ("roster.tsv", "input.fa", "receipt.json"))
    with roster.open("w", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(sorted(REQUIRED))
        writer.writerow(["Q1"] if case == "short_row" else ["x"] * len(REQUIRED))
    fasta.write_text(">\nACGT\n" if case == "empty_header" else ">Q1\nACGT\n")
    run = subprocess.run([sys.executable, str(TOOL), "--roster", str(roster), "--fasta", str(fasta), "--json", str(receipt)], capture_output=True, text=True)
    assert run.returncode == 2
    assert "ADMISSION_FAIL:" in run.stderr and "Traceback" not in run.stderr
    result = json.loads(receipt.read_text())
    assert result["status"] == "ADMISSION_FAIL"
    assert ("FASTA_IDENTITY" if case == "empty_header" else "ROSTER_ROW_INCOMPLETE") in result["reason"]
    assert json.loads(run.stdout) == result
