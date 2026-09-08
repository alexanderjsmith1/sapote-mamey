from __future__ import annotations

import csv
import json
from pathlib import Path

from openpyxl import Workbook

from mamey.manifest_schema import check_package_contract


ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schemas" / "manifest_contract.json"


def _example(schema: dict):
    expected = schema.get("type", "object")
    if isinstance(expected, list):
        expected = next(item for item in expected if item != "null")
    if expected == "object":
        return {key: _example(schema.get("properties", {}).get(key, {}))
                for key in schema.get("required", [])}
    if expected == "array":
        return []
    if expected == "string":
        return "synthetic"
    if expected == "integer":
        return 0
    if expected == "number":
        return 0.0
    if expected == "boolean":
        return False
    return {}


def _package(tmp_path: Path) -> Path:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    for filename, definition in (
        ("manifest.json", "manifest"),
        ("gate_validation.json", "gate_validation"),
        ("project_registry_status.json", "project_registry_status"),
    ):
        value = _example(schema["$defs"][definition])
        (tmp_path / filename).write_text(json.dumps(value), encoding="utf-8")
    for rule in schema["x-package-contract"]["artifacts"]:
        path = tmp_path / f"SYNTHETIC-001{rule['suffix']}"
        if rule["kind"] == "json":
            path.write_text(json.dumps({key: {} for key in rule["required_keys"]}), encoding="utf-8")
        elif rule["kind"] == "csv":
            with path.open("w", newline="", encoding="utf-8") as handle:
                csv.writer(handle).writerow(rule["required_columns"])
        else:
            workbook = Workbook()
            workbook.remove(workbook.active)
            for sheet in rule["required_sheets"]:
                workbook.create_sheet(sheet)
            workbook.save(path)
    return tmp_path


def test_checker_passes_complete_synthetic_contract(tmp_path):
    result = check_package_contract(_package(tmp_path))
    assert result["status"] == "PASS"
    assert result["error_count"] == 0


def test_checker_reports_exact_nested_key_path(tmp_path):
    package = _package(tmp_path)
    path = package / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    del manifest["bgc_counts"]["assembly_tier"]
    path.write_text(json.dumps(manifest), encoding="utf-8")

    result = check_package_contract(package)
    assert result["status"] == "FAIL"
    assert {error["path"] for error in result["errors"]} == {
        "manifest.json.bgc_counts.assembly_tier"
    }


def test_checker_reports_exact_csv_column_path(tmp_path):
    package = _package(tmp_path)
    path = package / "SYNTHETIC-001_2_inventory.csv"
    with path.open(newline="", encoding="utf-8") as handle:
        header = next(csv.reader(handle))
    header.remove("Resistance_tier")
    with path.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerow(header)

    result = check_package_contract(package)
    assert result["status"] == "FAIL"
    assert {error["path"] for error in result["errors"]} == {
        "*_2_inventory.csv.columns.Resistance_tier"
    }
