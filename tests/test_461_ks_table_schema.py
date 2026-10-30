"""Schema-only software controls; no sequence, domain scan or cohort analysis."""
import csv
import importlib.util
import json
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "tools/ks_burden_table.py"
SPEC = importlib.util.spec_from_file_location("ks_schema_regression_461", SOURCE)
ks = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ks)


def package_fixture(tmp_path):
    package = tmp_path / "package"
    package.mkdir()
    (package / "engineering_fixture_1_intake.json").write_text(json.dumps({"strain_id": "engineering_fixture"}))
    files = {
        "inventory": package / "engineering_fixture_2_inventory.csv",
        "modules": package / "engineering_fixture_3_antismash_modules.csv",
        "fragments": package / "engineering_fixture_4B_pks_ks_fragment_scan.csv",
    }
    files["inventory"].write_text("BGC_ID,Boundary,Node/Contig,Region\nBGC001,Interior,software_contig,region001\n")
    files["modules"].write_text("row_id,domain\nsoftware_row,PKS_AT\n")
    files["fragments"].write_text("clade_id,n_ks\n")
    return package, files


@pytest.mark.parametrize("kind", ["inventory", "modules", "fragments"])
@pytest.mark.parametrize("contents", ["", "unrelated\n"])
def test_missing_schema_is_held_before_outputs(tmp_path, kind, contents):
    package, files = package_fixture(tmp_path)
    files[kind].write_text(contents)
    output, receipt = tmp_path / "counts.tsv", tmp_path / "receipt.json"
    with pytest.raises(ks.KSBurdenHold) as raised:
        ks.build([package], output, receipt)
    assert raised.value.code == "KS_SOURCE_SCHEMA_HOLD"
    assert not output.exists() and not receipt.exists()


@pytest.mark.parametrize("contents", [
    "row_id,domain,domain\nsoftware_row,PKS_KS,PKS_AT\n",
    "row_id,domain\nsoftware_row,PKS_AT,unexpected_cell\n",
])
def test_ambiguous_or_nonrectangular_module_table_is_held(tmp_path, contents):
    package, files = package_fixture(tmp_path)
    files["modules"].write_text(contents)
    with pytest.raises(ks.KSBurdenHold) as raised:
        ks.package_row(package)
    assert raised.value.code == "KS_SOURCE_SCHEMA_HOLD"


def test_valid_empty_measurement_remains_zero(tmp_path):
    package, files = package_fixture(tmp_path)
    files["modules"].write_text("row_id,domain\n")
    result = ks.build([package], tmp_path / "counts.tsv", tmp_path / "receipt.json")
    assert result["status"] == "PASS"
    with (tmp_path / "counts.tsv").open() as handle:
        row = next(csv.DictReader(handle, delimiter="\t"))
    assert row["total_pks_ks_burden"] == "0"
