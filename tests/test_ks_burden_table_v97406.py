from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("ks_burden_table", ROOT / "tools" / "ks_burden_table.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def _write_csv(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _package(tmp_path, strain="SYN-001"):
    package = tmp_path / strain / "package"
    package.mkdir(parents=True)
    (package / f"{strain}_1_intake.json").write_text(json.dumps({"strain_id": strain}))
    _write_csv(package / f"{strain}_2_inventory.csv", ["BGC_ID", "Boundary"], [
        {"BGC_ID": "BGC001", "Boundary": "Interior"},
        {"BGC_ID": "BGC002", "Boundary": "Edge"},
        {"BGC_ID": "BGC003", "Boundary": "Full-contig"},
    ])
    _write_csv(package / f"{strain}_3_antismash_modules.csv", ["row_id", "domain"], [
        {"row_id": "M1", "domain": "PKS_KS"},
        {"row_id": "M2", "domain": "PKS_KS"},
        {"row_id": "M3", "domain": "PKS_AT"},
    ])
    _write_csv(package / f"{strain}_4B_pks_ks_fragment_scan.csv", ["clade_id", "n_ks"], [
        {"clade_id": "C1", "n_ks": "3"},
    ])
    return package


def test_counts_exact_module_rows_plus_separate_fragment_ks_and_binds_output(tmp_path):
    package = _package(tmp_path)
    out, receipt = tmp_path / "burden.tsv", tmp_path / "receipt.json"
    result = MODULE.build([package], out, receipt)
    row = list(csv.DictReader(out.open(), delimiter="\t"))[0]
    assert row["mapped_pks_ks"] == "2"
    assert row["orphan_fragment_pks_ks"] == "3"
    assert row["total_pks_ks_burden"] == "5"
    assert row["corrected_bgc_count"] == "1.75"
    assert result["output"]["sha256"] == hashlib.sha256(out.read_bytes()).hexdigest()
    assert "not module count" in row["claim_ceiling"]


def test_duplicate_module_row_id_fails_closed(tmp_path):
    package = _package(tmp_path)
    modules = package / "SYN-001_3_antismash_modules.csv"
    _write_csv(modules, ["row_id", "domain"], [
        {"row_id": "M1", "domain": "PKS_KS"},
        {"row_id": "M1", "domain": "PKS_KS"},
    ])
    try:
        MODULE.package_row(package)
    except MODULE.KSBurdenHold as exc:
        assert exc.code == "KS_MODULE_ROW_ID_HOLD"
    else:
        raise AssertionError("duplicate KS row id was accepted")
