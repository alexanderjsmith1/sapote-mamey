"""explain must report the package's final status, not the pre-seal one in manifest_short.json.

manifest_short.json is checksummed and is written before the final re-validation, so a package
that failed that check still says MAMEY_COMPLETE there. package_status.json carries the final status.
"""
import json
from types import SimpleNamespace

from mamey.package_inspector import _final_package_status, _read_json_or_warn, explain_command


def _pkg(tmp_path, short_status, terminal=None):
    pkg = tmp_path / "S1" / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest_short.json").write_text(json.dumps({"strain_id": "S1", "status": short_status}))
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "S1"}))
    if terminal:
        (pkg / "package_status.json").write_text(json.dumps({"terminal_status": terminal}))
    return pkg


def test_final_status_wins_and_the_early_one_is_named(tmp_path):
    pkg = _pkg(tmp_path, "MAMEY_COMPLETE", terminal="VALIDATION_FAIL")
    assert _final_package_status(pkg, {}, {"status": "MAMEY_COMPLETE"}) == ("VALIDATION_FAIL", "MAMEY_COMPLETE")


def test_manifest_terminal_status_is_the_second_source(tmp_path):
    pkg = _pkg(tmp_path, "MAMEY_COMPLETE")
    assert _final_package_status(pkg, {"terminal_status": "VALIDATION_FAIL"}, {"status": "MAMEY_COMPLETE"})[0] == "VALIDATION_FAIL"


def test_agreeing_sources_show_one_status(tmp_path):
    pkg = _pkg(tmp_path, "MAMEY_COMPLETE", terminal="MAMEY_COMPLETE")
    assert _final_package_status(pkg, {}, {"status": "MAMEY_COMPLETE"}) == ("MAMEY_COMPLETE", "")


def test_older_package_without_final_status_keeps_its_reading(tmp_path):
    pkg = _pkg(tmp_path, "PASS")
    assert _final_package_status(pkg, {}, {"status": "PASS"}) == ("PASS", "")


def test_unreadable_file_warns_and_reads_as_empty(tmp_path, capsys):
    bad = tmp_path / "package_status.json"
    bad.write_text("{oops", encoding="utf-8")
    assert _read_json_or_warn(bad) == {}
    assert "could not read package_status.json" in capsys.readouterr().err
    assert _read_json_or_warn(tmp_path / "absent.json") == {}


def test_explain_prints_the_final_status(tmp_path, capsys):
    pkg = _pkg(tmp_path, "MAMEY_COMPLETE", terminal="VALIDATION_FAIL")
    explain_command(SimpleNamespace(package_dir=str(pkg)))
    out = capsys.readouterr().out
    assert "Status        : VALIDATION_FAIL" in out
    assert "Pre-seal status: MAMEY_COMPLETE" in out
    assert "Status        : MAMEY_COMPLETE" not in out
