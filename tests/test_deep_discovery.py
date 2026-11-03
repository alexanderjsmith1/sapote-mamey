"""Opaque synthetic receipt discovery only; no biological extraction."""
import os
import glob
import json
from pathlib import Path
import pytest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))  # tests/ is a package; sibling test modules import by bare name
from test_deep_mode_admission import tool, native_case

@pytest.mark.parametrize("nested,visible", [(False, False), (True, False), (True, True)])
def test_unavailable_discovery_holds_before_native_publication(native_case, monkeypatch, nested, visible):
    bank, package, evidence, objects, calls = native_case
    denied = package / "unreadable" if nested else package
    if nested: denied.mkdir()
    if visible: evidence.write_text(json.dumps({"json_mode": "bounded"}))
    hidden_receipt = denied / "HIDDEN_AntiSMASH_Evidence_Parse.json"
    hidden_receipt.write_text(json.dumps({"json_mode": "full"}))
    before = {name: (bank / name).read_bytes() for name in objects}
    inputs = {str(p): p.read_bytes() for p in package.rglob('*') if p.is_file()}
    real_scan = tool.os.scandir
    def denied_scan(path):
        if Path(path) == denied:
            raise PermissionError("synthetic directory unavailable")
        return real_scan(path)
    monkeypatch.setattr(tool.os, "scandir", denied_scan)
    # Prove baseline discovery silently omits this exact unavailable directory.
    matches = glob.glob(str(package / "**/*AntiSMASH_Evidence_Parse.json"), recursive=True)
    assert str(hidden_receipt) not in matches
    error = None
    try:
        tool.main()
    except ValueError as exc:
        error = exc
    receipt = os.environ.get("DISCOVERY_RESULTS")
    if receipt:
        with open(receipt, "a") as output:
            output.write(json.dumps({"nested": nested, "visible_receipt": visible, "error": str(error) if error else None, "canonical_unchanged": {name: (bank / name).read_bytes() == value for name, value in before.items()}, "core_calls": len(calls["core"]), "finer_calls": len(calls["finer"]), "commit_state": (bank / ".ingest_state.json").exists(), "pending": (bank / ".ingest_pending.json").exists()}) + "\n")
    assert error is not None and "DEEP_DATA_DISCOVERY_HOLD" in str(error)
    assert str(denied) in str(error)
    assert isinstance(error.__cause__, PermissionError)
    assert {name: (bank / name).read_bytes() for name in objects} == before
    assert not calls["core"] and not calls["finer"]
    assert not (bank / ".ingest_state.json").exists()
    assert not (bank / ".ingest_pending.json").exists()
    monkeypatch.setattr(tool.os, "scandir", real_scan)
    assert {str(p): p.read_bytes() for p in package.rglob('*') if p.is_file()} == inputs


def test_readable_namespace_parity(tmp_path):
    for relative in ["X_AntiSMASH_Evidence_Parse.json", "nested/Y_AntiSMASH_Evidence_Parse.json", ".hidden/Z_AntiSMASH_Evidence_Parse.json", "nested/.privateAntiSMASH_Evidence_Parse.json"]:
        p = tmp_path / relative; p.parent.mkdir(exist_ok=True); p.write_text('{}')
    # Existing glob follows directory symlinks and matches directories by name too.
    (tmp_path / "alias").symlink_to(tmp_path / "nested", target_is_directory=True)
    (tmp_path / "directoryAntiSMASH_Evidence_Parse.json").mkdir()
    assert tool._evidence_paths(str(tmp_path)) == sorted(glob.glob(str(tmp_path / "**/*AntiSMASH_Evidence_Parse.json"), recursive=True))


def test_complete_readable_absence_remains_optional(tmp_path):
    (tmp_path / "nested").mkdir()
    assert tool.admitted_evidence(str(tmp_path / "Snapshot.json")) == ('unknown', None, {})


def test_directory_symlink_cycle_is_explicit_hold(tmp_path):
    (tmp_path / "cycle").symlink_to(tmp_path, target_is_directory=True)
    with pytest.raises(ValueError, match="directory traversal cycle"):
        tool.admitted_evidence(str(tmp_path / "Snapshot.json"))
