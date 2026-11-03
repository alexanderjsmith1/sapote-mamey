"""Required-input refusal checks using synthetic software fixtures only."""
import importlib.util
import json
import os
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("realistic_candidate", ROOT / "tools/realistic_bgc_count.py")
count = importlib.util.module_from_spec(spec)
spec.loader.exec_module(count)


def package(tmp_path, with_inventory=False):
    tmp_path.mkdir(exist_ok=True)
    (tmp_path / "manifest.json").write_text(json.dumps({"strain_id": "SOFTWARE-FIXTURE"}))
    if with_inventory:
        (tmp_path / "SOFTWARE-FIXTURE_2_inventory.csv").write_text("BGC_ID,Products,Length_kb,Boundary\nBGC001,T1PKS,40,Interior\n")
    return tmp_path


@pytest.mark.parametrize("reader", [count._read_regions, count.score_package])
def test_absent_inventory_is_unavailable(reader, tmp_path):
    pkg = package(tmp_path)
    with pytest.raises(FileNotFoundError, match="required inventory missing"):
        reader(str(pkg))


@pytest.mark.parametrize("existing_output", [False, True])
@pytest.mark.parametrize("multi_package", [False, True])
def test_cli_refusal_preserves_all_bytes(tmp_path, existing_output, multi_package):
    missing = package(tmp_path / "missing")
    out = tmp_path / "out"
    args = ["--package", str(missing), "--out", str(out)]
    if multi_package:
        good = package(tmp_path / "valid", True)
        args = ["--package", str(good)] + args
    if existing_output:
        out.mkdir()
        (out / "realistic_bgc_count.csv").write_bytes(b"existing CSV")
        (out / "realistic_bgc_count_summary.json").write_bytes(b"existing JSON")
    before = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    with pytest.raises(SystemExit) as error:
        count.main(args)
    assert error.value.code == 2
    after = {str(p.relative_to(tmp_path)): p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert after == before
    assert out.exists() == existing_output


def test_present_nonempty_inventory_keeps_counts(tmp_path):
    pkg = package(tmp_path, True)
    value = count.score_package(str(pkg))
    assert value["Raw_regions"] == value["Realistic_count"] == 1
    assert value["Corrected_count_bw"] == 1.0
