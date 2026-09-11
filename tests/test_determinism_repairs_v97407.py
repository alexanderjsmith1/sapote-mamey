from datetime import datetime, timezone
import json
import zipfile

from openpyxl import Workbook

from mamey.cli import _phase_receipt
from mamey.domain_level import run_domain_level
from mamey.package_map import build_package_map
from mamey.xlsx_determinism import FIXED_ZIP_DATETIME, canonicalize_xlsx


def test_xlsx_canonicalization_removes_core_and_zip_timestamps(tmp_path):
    outputs = []
    for index, year in enumerate((2020, 2026)):
        path = tmp_path / f"book{index}.xlsx"
        workbook = Workbook()
        workbook.active["A1"] = "same cell"
        workbook.properties.created = datetime(year, 1, 2, tzinfo=timezone.utc)
        workbook.properties.modified = datetime(year, 1, 3, tzinfo=timezone.utc)
        workbook.save(path)
        canonicalize_xlsx(path)
        outputs.append(path)
    assert outputs[0].read_bytes() == outputs[1].read_bytes()
    with zipfile.ZipFile(outputs[0]) as archive:
        assert all(info.date_time == FIXED_ZIP_DATETIME for info in archive.infolist())


def test_package_map_uses_portable_package_locator(tmp_path):
    (tmp_path / "manifest.json").write_text('{"strain_id":"PUBLIC-FIX"}')
    assert build_package_map(tmp_path)["package_dir"] == "."


def test_domain_level_receipt_does_not_leak_absolute_package_path(tmp_path):
    package = tmp_path / "package"
    package.mkdir()
    receipt = run_domain_level(package)
    assert receipt["package"] == "."
    persisted = json.loads((package / "domain_level" / "domain_level_receipt.json").read_text())
    assert persisted["package"] == "."


def test_domain_level_receipt_uses_portable_source_name(tmp_path):
    package = tmp_path / "package"
    package.mkdir()
    source = tmp_path / "outside" / "fixture.zip"
    receipt = run_domain_level(package, source_antismash=source)
    assert receipt["source_antismash"] == "fixture.zip"
    assert str(tmp_path) not in json.dumps(receipt)


def test_phase_receipt_redacts_absolute_locators(tmp_path):
    package = tmp_path / "run" / "package"
    package.mkdir(parents=True)
    inside = package / "rows.csv"
    outside = tmp_path / "inputs" / "fixture.zip"
    _phase_receipt(package, "probe", "END", csv=str(inside), input_zip=str(outside))
    row = json.loads((package / "run_phase_receipts.jsonl").read_text())
    assert row["csv"] == "rows.csv"
    assert row["input_zip"] == "fixture.zip"
    assert str(tmp_path) not in json.dumps(row)
