"""`claim-safety --report` never writes onto its input and never appends without being asked.

The report writer opened the path in append mode with no check, so `--report <the card>` added
CSV rows to the card, and reusing a report mixed findings from different runs.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = "# Card\n\nThis BGC produces examplomycin.\n"


def _run(*args):
    return subprocess.run([sys.executable, "mamey_run.py", "claim-safety", *args], cwd=ROOT,
                          capture_output=True, text=True, timeout=120)


def test_the_input_card_is_never_the_report(tmp_path):
    card = tmp_path / "card.md"
    card.write_text(CARD, encoding="utf-8")
    res = _run(str(card), "--report", str(card))
    assert res.returncode == 2
    assert "REFUSED" in res.stderr and "input card" in res.stderr
    assert card.read_text(encoding="utf-8") == CARD


def test_an_existing_report_is_refused_unless_appending(tmp_path):
    card = tmp_path / "card.md"
    card.write_text(CARD, encoding="utf-8")
    report = tmp_path / "report.csv"
    assert _run(str(card), "--report", str(report)).returncode in (0, 1)
    first = report.read_text(encoding="utf-8")
    res = _run(str(card), "--report", str(report))
    assert res.returncode == 2 and "--append-report" in res.stderr
    assert report.read_text(encoding="utf-8") == first
    assert _run(str(card), "--report", str(report), "--append-report").returncode in (0, 1)
    assert len(report.read_text(encoding="utf-8")) > len(first)
