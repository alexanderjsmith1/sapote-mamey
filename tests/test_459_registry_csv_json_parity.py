"""The CSV must remain a complete, faithful view of the JSON inventory."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
JOINED = {"wet_lab_routes", "synonyms", "required_markers", "optional_markers", "forbidden_markers"}

def test_registry_csv_matches_json():
    entries = json.loads((ROOT / "bundle_support/registry_inventory_v1.9.4.json").read_text())
    with (ROOT / "bundle_support/registry_inventory_v1.9.4.csv").open(newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fields = reader.fieldnames
    assert len({x["id"] for x in entries}) == len(entries)
    assert [x["id"] for x in rows] == [x["id"] for x in entries]
    assert set(fields) == {key for entry in entries for key in entry}
    for entry, row in zip(entries, rows):
        for key in fields:
            value = entry.get(key)
            if key == "targets" and value is not None:
                assert json.loads(row[key]) == value
            elif key in JOINED and value is not None:
                assert (row[key].split(";") if row[key] else []) == value
            else:
                assert row[key] == ("" if value is None else value), (entry["id"], key)

def invoke(registry, output):
    return subprocess.run([sys.executable, str(ROOT / "tools/export_registry_inventory_csv.py"), "--registry", str(registry), "--output", str(output)], capture_output=True, text=True)

def test_cli_preserves_quoted_unicode_and_nested_targets(tmp_path):
    entry = {"id": "GENERIC-001", "name": 'Comma, quote " and newline\nUnicode Ω', "targets": [{"value": "a,b", "score": None}], "synonyms": ["alpha", "beta"]}
    source = tmp_path / "source.json"; output = tmp_path / "out.csv"
    source.write_text(json.dumps([entry])); original = source.read_bytes()
    result = invoke(source, output)
    assert result.returncode == 0, result.stderr
    with output.open(newline="") as f: row = next(csv.DictReader(f))
    assert row["name"] == entry["name"]
    assert json.loads(row["targets"]) == entry["targets"]
    assert row["synonyms"].split(";") == entry["synonyms"]
    first = output.read_bytes(); assert invoke(source, output).returncode == 0
    assert output.read_bytes() == first and source.read_bytes() == original

@pytest.mark.parametrize("entries", [[{"id": "X"}, {"id": "X"}], [{"name": "missing ID"}], [{"id": "X", "unmapped": "lost"}], [{"id": "X", "synonyms": ["ambiguous;value"]}]])
def test_invalid_source_leaves_output_unchanged(tmp_path, entries):
    source = tmp_path / "source.json"; output = tmp_path / "out.csv"
    source.write_text(json.dumps(entries)); output.write_text("KEEP")
    result = invoke(source, output)
    assert result.returncode != 0
    assert output.read_text() == "KEEP"

def test_refuses_to_overwrite_source_json(tmp_path):
    source = tmp_path / "source.json"; source.write_text('[{"id":"X"}]'); original = source.read_bytes()
    assert invoke(source, source).returncode != 0
    assert source.read_bytes() == original
