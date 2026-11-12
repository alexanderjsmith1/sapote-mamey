"""gap_rescue_join_runs writes its tables with the bundle's formula-safe writer."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import gap_rescue_join_runs as J  # noqa: E402


def test_formula_leading_cell_is_neutralized_and_numbers_kept(tmp_path):
    out = tmp_path / "t.tsv"
    J._write(out, ("reference_name", "core"), [{"reference_name": "=HYPERLINK(1)", "core": "-3"}])
    row = next(csv.DictReader(open(out, encoding="utf-8"), delimiter="\t"))
    assert row["reference_name"] == "'=HYPERLINK(1)"
    assert row["core"] == "-3"


def test_no_plain_csv_writer_in_the_tool():
    text = (ROOT / "tools" / "gap_rescue_join_runs.py").read_text(encoding="utf-8")
    assert "csv.DictWriter(" not in text and "csv.writer(" not in text
