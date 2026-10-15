"""v9.7.452: tools/ingest_field_collection.py --layout experiment-sheets reads a lab workbook kept as
one sheet per experiment (no `Isolate Index` sheet) into the same per-strain TSV, values verbatim,
with the sheet and cell of every value, and a typed hold for a code whose rows disagree.
Synthetic workbook only: reserved-range parser-contract fixtures, placeholder places."""
from pathlib import Path
import csv
import datetime
import os
import subprocess
import sys

import pytest

openpyxl = pytest.importorskip("openpyxl")

TOOL = Path(__file__).resolve().parents[1] / "tools/ingest_field_collection.py"


def _workbook(tmp_path):
    wb = openpyxl.Workbook()
    # storage map: no header, codes in a grid -- must be excludable by pattern
    ws = wb.active
    ws.title = "Storage Map"
    ws.append([None, "Box 1", None, None, None, None, "AS-978", "AS-974"])
    ws.append([None, "Box 2", None, None, None, None, "AS-975", "AS-976"])
    # header-mapped sheet
    ws = wb.create_sheet("Experiments 1 to 9")
    ws.append(["Date", "Experiment number", "Sample Number", "Description", "Location", "Notes"])
    ws.append([None, "Experiment 1", "Colony X1", "Site A queen", "Site A", None])
    ws.append([datetime.datetime(2021, 3, 4), "Experiment 1", "#1", "Top of garden", None,
               None, "AS-978, AS-971 + AS-972"])
    ws.append([None, "Experiment 1", "#2", "Middle", None, "same tube as 977", None])
    ws.append([None, "Experiment 2", "#1", "Leaf", "Site B", None, "AS-973"])
    ws.append([None, "Experiment 2", "#2", "Leaf", "Site B", None, "AS-973"])  # sample conflict
    # headerless per-experiment sheet, title carries the experiment
    ws = wb.create_sheet("Exp 7")
    ws.append(["Exp 7"])
    ws.append([])
    ws.append([datetime.datetime(2023, 6, 1), "Region A field day"])
    ws.append(["Exp 7", "#4", "Material A", None, None, "Region A", "AS-974"])
    ws.append([None, "Exp 7", 5.0, "Material B", "AS975"])
    ws.append([None, "Exp 7", "#6", "Material C", "AS-976 (contaminated?)"])
    # the same code again in another sheet, agreeing (Exp 7 vs Experiment 7, blank fills blank)
    ws = wb.create_sheet("Exp 8")
    ws.append([None, "Experiment 7", "#4", None, None, None, "AS-974"])
    p = tmp_path / "lab.xlsx"
    wb.save(p)
    return p


def _run(tmp_path, *args):
    return subprocess.run([sys.executable, str(TOOL), *args], cwd=tmp_path,
                          env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"),
                          capture_output=True, text=True, timeout=60)


def _rows(path):
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


@pytest.fixture()
def result(tmp_path):
    xlsx = _workbook(tmp_path)
    out = tmp_path / "coll.tsv"
    holds = tmp_path / "holds.tsv"
    r = _run(tmp_path, "--layout", "experiment-sheets", "--input", str(xlsx), "--out", str(out),
             "--holds", str(holds), "--exclude-sheet", "^Storage Map$")
    assert r.returncode == 0, r.stderr
    return r, {x["as_id"]: x for x in _rows(out)}, {x["as_id"]: x for x in _rows(holds)}


def test_schema_keeps_existing_columns_first(result):
    _, rows, _ = result
    first = next(iter(rows.values()))
    assert list(first)[:8] == ["as_id", "category_raw", "simple_group_raw", "location_raw",
                               "date", "experiment", "sample", "description_raw"]
    assert {"context_raw", "as_cell_raw", "source_sheet", "source_refs",
            "n_source_rows"} <= set(first)


def test_header_sheet_multi_code_cell_and_context(result):
    _, rows, _ = result
    for aid in ("AS-978", "AS-971", "AS-972"):
        row = rows[aid]
        assert row["experiment"] == "Experiment 1"
        assert row["sample"] == "#1"
        assert row["date"] == "2021-03-04"
        assert row["description_raw"] == "Top of garden"
        assert row["as_cell_raw"] == "AS-978, AS-971 + AS-972"
        # the colony line above is carried verbatim as context, not parsed into a place
        assert row["context_raw"] == "Colony X1 | Site A queen | Site A"
        assert row["location_raw"] == ""
        assert row["category_raw"] == ""


def test_lowercase_prose_is_not_a_strain(result):
    _, rows, holds = result
    assert "AS-977" not in rows and "AS-977" not in holds


def test_headerless_sheet_verbatim_and_provenance(result):
    _, rows, _ = result
    r910 = rows["AS-974"]
    assert r910["experiment"] == "Exp 7"
    assert r910["sample"] == "#4"
    # no column is named Location here, so the place stays inside the verbatim description
    assert r910["description_raw"] == "Material A | Region A"
    assert r910["location_raw"] == ""
    assert r910["context_raw"] == "Region A field day"
    assert r910["date"] == "2023-06-01"
    # merged with the agreeing row on sheet "Exp 8"
    assert r910["n_source_rows"] == "2"
    assert r910["source_sheet"] == "Exp 7 | Exp 8"
    assert "sample=Exp 7!B4" in r910["source_refs"]
    assert "as_id=Exp 8!G1" in r910["source_refs"]
    # a bare number right after the experiment cell is the sample; 'AS975' canonicalizes
    assert rows["AS-975"]["sample"] == "5"
    assert rows["AS-976"]["description_raw"] == "Material C"
    assert rows["AS-976"]["as_cell_raw"] == "AS-976 (contaminated?)"


def test_conflict_is_a_typed_hold_not_a_pick(result):
    r, rows, holds = result
    assert "AS-973" not in rows
    h = holds["AS-973"]
    assert h["hold_code"] == "FIELD_COLLECTION_IDENTITY_CONFLICT"
    assert h["conflict_fields"] == "sample"
    assert "sample=#1" in h["source_values"] and "sample=#2" in h["source_values"]
    assert "1 identity conflicts held" in r.stdout


def test_exclude_sheet_matters(tmp_path):
    xlsx = _workbook(tmp_path)
    out = tmp_path / "all.tsv"
    r = _run(tmp_path, "--layout", "experiment-sheets", "--input", str(xlsx), "--out", str(out))
    assert r.returncode == 0, r.stderr
    holds = {x["as_id"] for x in _rows(tmp_path / "all.holds.tsv")}
    # storage-map rows disagree with the experiment rows, so those codes are held, never merged
    assert {"AS-978", "AS-974", "AS-975", "AS-976"} <= holds
    assert "4 sheets read" in r.stdout


def test_isolate_index_is_still_the_default(tmp_path):
    xlsx = _workbook(tmp_path)
    r = _run(tmp_path, "--input", str(xlsx), "--out", str(tmp_path / "o.tsv"))
    assert r.returncode == 2
    assert "FIELD_COLLECTION_SCHEMA" in r.stderr
