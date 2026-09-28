"""The RG-GMCI ranked-pairs table and workbook sheet say why each pair holds its confidence.

The engine wrote `acceptance_gate` (the gate that kept or demoted a pair), `max_endpoint_hub_degree` and
`mibig_good_geometry_references` only into `_4A_RGGMCI_full.json`. The CSV and the workbook sheet, which people and
downstream tools read, left them out, so a pair demoted by the hub or paralogy gate looked like weak evidence. The
standalone rggmci package already shows them.
"""
import csv
import json
import os
import pathlib
import subprocess
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ZIP = ROOT / "tests" / "fixtures" / "rggmci_public_VWPH00000000.1_subset.zip"
NEW = ("acceptance_gate", "max_endpoint_hub_degree", "mibig_good_geometry_references")


@pytest.fixture(scope="module")
def package(tmp_path_factory):
    out = tmp_path_factory.mktemp("gate444")
    env = dict(os.environ, PYTHONPATH=str(ROOT), PYTHONHASHSEED="0")
    subprocess.run([sys.executable, "-m", "mamey", "run", "--strain", "VWPH_SUBSET", "--input-zip", str(ZIP),
                    "--taxonomy", "Saccharopolyspora sp.", "--source", "public test fixture", "--outdir", str(out),
                    "--mode", "standard", "--release", "PUBLIC", "--brief", "none", "--json-evidence", "off"],
                   check=True, capture_output=True, timeout=600, env=env, text=True)
    return next(out.rglob("VWPH_SUBSET_4A_RGGMCI_ranked_pairs.csv")).parent


def test_csv_carries_the_gate_and_matches_the_json(package):
    rows = list(csv.DictReader(open(package / "VWPH_SUBSET_4A_RGGMCI_ranked_pairs.csv", encoding="utf-8")))
    full = json.load(open(package / "VWPH_SUBSET_4A_RGGMCI_full.json", encoding="utf-8"))["ranked_pairs"]
    assert rows and all(c in rows[0] for c in NEW)
    assert [(r["pair"], r["acceptance_gate"]) for r in rows] == [(p["pair"], p["acceptance_gate"]) for p in full]
    assert all(r["acceptance_gate"] for r in rows)


def test_workbook_sheet_carries_the_gate(package):
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.load_workbook(next(package.glob("*_5_workbook.xlsx")), read_only=True)
    header = next(wb["RGGMCI_Ranked"].iter_rows(values_only=True))
    assert all(c in header for c in NEW)
