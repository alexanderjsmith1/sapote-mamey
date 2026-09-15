"""BLACK_CHERRY_4_427: tools/ingest_field_collection.py normalizes the field-collection workbook's
Isolate Index sheet into a per-strain collection-metadata TSV. Real CLI subprocess; builds a tiny
xlsx fixture with openpyxl (skips cleanly if openpyxl is absent)."""
from pathlib import Path
import csv
import os
import subprocess
import sys

import pytest

openpyxl = pytest.importorskip("openpyxl")

TOOL = Path(__file__).resolve().parents[1] / "tools/ingest_field_collection.py"

HEADER = ("AS code", "Experiment", "Sample", "Description", "Simple Group",
          "Category", "Location", "Date")


def _make_xlsx(tmp_path, rows, sheet="Isolate Index"):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = sheet
    ws.append(list(HEADER))
    for r in rows:
        ws.append(list(r))
    p = tmp_path / "field.xlsx"
    wb.save(p)
    return p


def _run(tmp_path, *args):
    return subprocess.run([sys.executable, str(TOOL), *args], cwd=tmp_path,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
                          capture_output=True, text=True, timeout=60)


def _rows(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def test_basic_normalize_and_verbatim_category(tmp_path):
    # Synthetic identifiers only (the "verified synthetic" block of tools/test_synthetic_ids.txt)
    # with placeholder locality: GOV-001's rationale rests on no host, collection or geolocation
    # detail being paired with a real strain identifier in the shipped tree.
    xlsx = _make_xlsx(tmp_path, [
        ("AS-900", "Exp 1", "#9", "Bombus", "Bee", "Bombus", "Region A", "2022"),
        ("AS 901", "Exp 2", "#1", "Ant", "Ant", "Other/unclear", "Region A (field site)", "2022"),
    ])
    out = tmp_path / "coll.tsv"
    r = _run(tmp_path, "--input", str(xlsx), "--out", str(out))
    assert r.returncode == 0, r.stderr
    rows = {x["as_id"]: x for x in _rows(str(out))}
    assert rows["AS-900"]["category_raw"] == "Bombus"
    assert rows["AS-900"]["location_raw"] == "Region A"
    # 'AS 901' canonicalizes to AS-901; the awkward raw category is preserved verbatim, not bucketed
    assert rows["AS-901"]["category_raw"] == "Other/unclear"
    assert rows["AS-901"]["location_raw"] == "Region A (field site)"


def test_non_strain_rows_skipped(tmp_path):
    xlsx = _make_xlsx(tmp_path, [
        ("AS-1", "E1", "#1", "d", "Bee", "Bombus", "NJ", "2022"),
        ("BLANK", "", "", "", "", "", "", ""),
        ("Media control", "", "", "", "", "", "", ""),
    ])
    out = tmp_path / "coll.tsv"
    r = _run(tmp_path, "--input", str(xlsx), "--out", str(out))
    assert r.returncode == 0, r.stderr
    ids = {x["as_id"] for x in _rows(str(out))}
    assert ids == {"AS-1"}
    assert "2 non-strain rows skipped" in r.stdout


def test_duplicate_fills_blanks_no_conflict(tmp_path):
    xlsx = _make_xlsx(tmp_path, [
        ("AS-5", "E1", "#1", "d", "Bee", "Bombus", "", "2022"),
        ("AS-5", "E1", "#1", "d", "Bee", "", "New Jersey", "2022"),  # fills location, no conflict
    ])
    out = tmp_path / "coll.tsv"
    r = _run(tmp_path, "--input", str(xlsx), "--out", str(out))
    assert r.returncode == 0, r.stderr
    rows = {x["as_id"]: x for x in _rows(str(out))}
    assert rows["AS-5"]["category_raw"] == "Bombus"
    assert rows["AS-5"]["location_raw"] == "New Jersey"


def test_identity_conflict_refuses(tmp_path):
    xlsx = _make_xlsx(tmp_path, [
        ("AS-5", "E1", "#1", "d", "Bee", "Bombus", "NJ", "2022"),
        ("AS-5", "E1", "#1", "d", "Bee", "Wasp", "NJ", "2022"),  # category conflict
    ])
    out = tmp_path / "coll.tsv"
    r = _run(tmp_path, "--input", str(xlsx), "--out", str(out))
    assert r.returncode == 2, r.stderr
    assert "FIELD_COLLECTION_IDENTITY_CONFLICT" in r.stderr
    assert "Traceback" not in r.stderr


def test_missing_column_schema_refusal(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Isolate Index"
    ws.append(["AS code", "Category"])  # missing most required columns
    ws.append(["AS-1", "Bombus"])
    p = tmp_path / "bad.xlsx"
    wb.save(p)
    r = _run(tmp_path, "--input", str(p), "--out", str(tmp_path / "o.tsv"))
    assert r.returncode == 2
    assert "FIELD_COLLECTION_SCHEMA" in r.stderr


def test_missing_sheet_refusal(tmp_path):
    xlsx = _make_xlsx(tmp_path, [("AS-1", "E", "#1", "d", "Bee", "Bombus", "NJ", "2022")])
    r = _run(tmp_path, "--input", str(xlsx), "--out", str(tmp_path / "o.tsv"),
             "--sheet", "Nonexistent")
    assert r.returncode == 2
    assert "FIELD_COLLECTION_SCHEMA" in r.stderr
