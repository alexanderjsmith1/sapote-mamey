"""DREL-044: the status receipt temp file is created exclusively."""
import json

from mamey.recovery_status import write_package_status_receipt


def _package(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "SYN-1"}))
    (pkg / "SYN-1_2_inventory.csv").write_text("BGC_ID,Contig,Region\n")
    return pkg


def test_status_writer_leaves_occupied_old_temp_alone(tmp_path):
    pkg = _package(tmp_path)
    occupied = pkg / "package_status.json.tmp"
    occupied.write_text("someone else's bytes")
    write_package_status_receipt(pkg, validator_status="PASS")
    assert occupied.read_text() == "someone else's bytes"
    assert json.loads((pkg / "package_status.json").read_text())


def test_status_writer_does_not_follow_planted_temp_symlink(tmp_path):
    pkg = _package(tmp_path)
    outside = tmp_path / "outside.txt"
    outside.write_text("untouched")
    (pkg / "package_status.json.tmp").symlink_to(outside)
    write_package_status_receipt(pkg, validator_status="PASS")
    assert outside.read_text() == "untouched"


def test_status_writer_keeps_readable_mode_and_no_stray_temp(tmp_path):
    pkg = _package(tmp_path)
    path = write_package_status_receipt(pkg, validator_status="PASS")
    assert path.stat().st_mode & 0o777 == 0o644
    assert not [p for p in pkg.iterdir() if p.name.endswith(".tmp")]
