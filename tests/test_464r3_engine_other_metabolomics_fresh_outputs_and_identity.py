"""Metabolomics readiness: outputs are fresh, and each row carries the exact source identity.

Before: the CSV and spreadsheet replaced earlier files under fixed names (an older spreadsheet could
survive a failed spreadsheet write beside a new CSV), rows had no strain field, a missing contig or
region showed as `?`, and a region already named `region004` was printed as `regionregion004`.
"""
import csv
import importlib.util
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))


def _load():
    spec = importlib.util.spec_from_file_location("bmr_464r3", ROOT / "tools" / "build_metabolomics_readiness.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _package(tmp_path):
    pkg = tmp_path / "package"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "SYN-1", "bgcs": [
        {"bgc_id": "BGC001", "contig": "NODE_1_length_9000", "antismash_region": "region004", "products": ["NRPS"]},
        {"bgc_id": "BGC002", "products": ["terpene"]},
    ]}))
    return pkg


def _run(mod, monkeypatch, pkg, out):
    monkeypatch.setattr(sys, "argv", ["bmr", "--package-dir", str(pkg), "--out-dir", str(out)])
    mod.main()


def test_rows_carry_exact_identity_and_holds(tmp_path, monkeypatch):
    mod, pkg, out = _load(), _package(tmp_path), tmp_path / "out"
    _run(mod, monkeypatch, pkg, out)
    rows = {r["bgc_id"]: r for r in csv.DictReader((out / "SYN-1_Metabolomics_Readiness.csv").open())}
    one = rows["BGC001"]
    assert (one["strain"], one["full_contig"], one["region"], one["identity_state"]) == (
        "SYN-1", "NODE_1_length_9000", "region004", "COMPLETE")
    assert "regionregion" not in one["locator"]
    assert rows["BGC002"]["identity_state"].startswith("IDENTITY_HOLD")
    assert rows["BGC002"]["full_contig"] == "" and rows["BGC002"]["region"] == ""


def test_existing_outputs_are_refused(tmp_path, monkeypatch):
    mod, pkg, out = _load(), _package(tmp_path), tmp_path / "out"
    out.mkdir()
    stale = out / "SYN-1_Metabolomics_Readiness.xlsx"
    stale.write_bytes(b"older spreadsheet")
    with pytest.raises(SystemExit) as exc:
        _run(mod, monkeypatch, pkg, out)
    assert "OUTPUT_REFUSED" in str(exc.value.code)
    assert stale.read_bytes() == b"older spreadsheet"
    assert not (out / "SYN-1_Metabolomics_Readiness.csv").exists()
