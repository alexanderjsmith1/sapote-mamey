"""Admission-only fixtures: every extractor is stubbed; native transaction is real."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("deep_admission_native", ROOT / "tools/build_deep_data.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
original_find_snaps = tool.find_snaps

CASES = [
    ("absent", None, True, "unknown"),
    ("missing", {}, False, None),
    ("unknown", {"json_mode": "unknown"}, False, None),
    ("uppercase", {"json_mode": "UNKNOWN"}, False, None),
    ("typo", {"json_mode": "typo"}, False, None),
    ("null", {"json_mode": None}, False, None),
    ("off", {"json_mode": "off"}, True, "off"),
    ("bounded", {"json_mode": "bounded"}, True, "bounded"),
    ("full", {"json_mode": "full"}, True, "full"),
    ("effective_bounded", {"json_mode_effective": "bounded"}, True, "bounded"),
    ("effective_full", {"json_mode_effective": "full"}, True, "full"),
    ("effective_off", {"json_mode_effective": "off"}, True, "off"),
    ("conflict1", {"json_mode": "off", "json_mode_effective": "bounded"}, False, None),
    ("conflict2", {"json_mode": "bounded", "json_mode_effective": "off"}, False, None),
    ("downgrade", {"json_mode_requested": "bounded", "json_mode_effective": "off"}, True, "off"),
    ("malformed", "{bad", False, None),
    ("nonobject", [], False, None),
    ("duplicate", {"json_mode": "bounded"}, False, None),
    ("matching", {"json_mode": "full", "json_mode_effective": "full"}, True, "full"),
]

@pytest.fixture
def native_case(tmp_path, monkeypatch):
    from mamey import gold_bgc_identity
    bank = tmp_path / "bank"; bank.mkdir()
    objects = {
        "bgc_data.json": {"strains": {"SOFTWARE": {}, "OTHER": {}}, "bgcs": []},
        "deep_data.json": {"bgc_profile": [], "domain_hits": [], "active_sites": [{"sid": "SOFTWARE", "retain": True}, {"sid": "OTHER", "retain": True}], "class_pred": []},
        "gene_data.json": {"scan_agg": {}, "tfbs": {}, "domain_arch": [], "substrates": [{"sid": "SOFTWARE", "retain": True}, {"sid": "OTHER", "retain": True}], "ripp": []},
    }
    for name, value in objects.items(): (bank / name).write_text(json.dumps(value))
    package = tmp_path / "package"; package.mkdir()
    snapshot = package / "SOFTWARE_Project_Memory_Snapshot.json"
    snapshot.write_text(json.dumps({"source_scans": {}}))
    evidence = package / "SOFTWARE_AntiSMASH_Evidence_Parse.json"
    calls = {"core": [], "finer": []}
    monkeypatch.setattr(tool, "find_snaps", lambda: {"SOFTWARE": str(snapshot)})
    monkeypatch.setattr(tool, "extract", lambda *a, **kw: calls["core"].append(a) or ([{"sid": "SOFTWARE", "new": True}], [], []))
    monkeypatch.setattr(tool, "extract_finer", lambda *a: calls["finer"].append(a) or ([], [], [], []))
    monkeypatch.setattr(gold_bgc_identity, "load_gold_identity_context", lambda *a: {"receipt": {"stub": True}})
    monkeypatch.setattr(sys, "argv", [str(tool.__file__), str(bank)])
    return bank, package, evidence, objects, calls

@pytest.mark.parametrize("label,payload,accepted,mode", CASES, ids=[c[0] for c in CASES])
def test_native_mode_admission(native_case, label, payload, accepted, mode):
    from mamey import bank_transaction
    bank, package, evidence, objects, calls = native_case
    if label != "absent":
        evidence.write_text(payload if isinstance(payload, str) else json.dumps(payload))
    if label == "duplicate":
        (package / "SECOND_AntiSMASH_Evidence_Parse.json").write_text(json.dumps(payload))
    before = {name: (bank / name).read_bytes() for name in objects}
    inputs = {p.name: p.read_bytes() for p in package.iterdir()}
    if not accepted:
        with pytest.raises(ValueError): tool.main()
        assert {name: (bank / name).read_bytes() for name in objects} == before
        assert not calls["core"] and not calls["finer"]
        assert not (bank / ".ingest_state.json").exists()
    else:
        assert tool.main() == 0
        bank_transaction.coherent(bank)
        assert len(calls["core"]) == 1
        assert len(calls["finer"]) == (mode != "off")
        for name, section in [("deep_data.json", "active_sites"), ("gene_data.json", "substrates")]:
            rows = json.loads((bank / name).read_text())[section]
            assert [r for r in rows if r["sid"] == "OTHER"] == [{"sid": "OTHER", "retain": True}]
            assert bool([r for r in rows if r["sid"] == "SOFTWARE"]) == (mode in {"unknown", "off"})
    assert not (bank / ".ingest_pending.json").exists()
    assert {p.name: p.read_bytes() for p in package.iterdir()} == inputs

@pytest.mark.parametrize("first_failure", [True, False], ids=["first-read-failure", "forbid-reread"])
def test_single_admitted_read_native_preservation(native_case, monkeypatch, first_failure):
    bank, package, evidence, objects, calls = native_case
    evidence.write_text(json.dumps({"json_mode": "bounded", "opaque": "original"}))
    before = {name: (bank / name).read_bytes() for name in objects}
    evidence_before = evidence.read_bytes()
    real_read = tool._read_json
    reads = []
    admitted = []
    def controlled(path, **kwargs):
        if Path(path) == evidence:
            reads.append(str(path))
            if first_failure:
                raise PermissionError("synthetic first-read failure")
            if len(reads) > 1:
                pytest.fail("selected evidence reread after admission")
            value = real_read(path, **kwargs)
            admitted.append(value)
            return value
        return real_read(path, **kwargs)
    monkeypatch.setattr(tool, "_read_json", controlled)
    if first_failure:
        with pytest.raises(ValueError, match="DEEP_DATA_EVIDENCE_READ_HOLD") as caught:
            tool.main()
        assert isinstance(caught.value.__cause__, PermissionError)
        assert str(evidence) in str(caught.value)
        assert {name: (bank / name).read_bytes() for name in objects} == before
        assert not calls["core"] and not calls["finer"]
        assert not (bank / ".ingest_state.json").exists()
    else:
        assert tool.main() == 0
        assert len(calls["finer"]) == 1
        assert calls["finer"][0][2] is admitted[0]
    assert len(reads) == 1
    assert evidence.read_bytes() == evidence_before
    assert not (bank / ".ingest_pending.json").exists()


@pytest.mark.parametrize("kind", ["invalid_json", "invalid_utf8", "missing", "permission"])
def test_selected_snapshot_error_preserves_native_bank(native_case, monkeypatch, kind):
    bank, package, evidence, objects, calls = native_case
    snapshot = package / "SOFTWARE_Project_Memory_Snapshot.json"
    if kind == "invalid_json": snapshot.write_text("{broken")
    elif kind == "invalid_utf8": snapshot.write_bytes(b"{\xff}")
    elif kind == "missing": snapshot.unlink()
    before = {name: (bank / name).read_bytes() for name in objects}
    read = tool._read_json
    def controlled(path, **kwargs):
        if kind == "permission" and Path(path) == snapshot: raise PermissionError("synthetic denied")
        return read(path, **kwargs)
    monkeypatch.setattr(tool, "_read_json", controlled)
    with pytest.raises(ValueError, match="DEEP_DATA_SNAPSHOT_READ_HOLD") as caught:
        tool.main()
    assert caught.value.__cause__ is not None
    assert str(snapshot) in str(caught.value)
    assert {name: (bank / name).read_bytes() for name in objects} == before
    assert not calls["core"] and not calls["finer"]
    assert not (bank / ".ingest_pending.json").exists()
    assert not (bank / ".ingest_state.json").exists()


@pytest.mark.parametrize("kind", ["duplicate", "unreadable"])
def test_snapshot_discovery_hold_native_bank(native_case, monkeypatch, kind):
    bank, package, evidence, objects, calls = native_case
    monkeypatch.setattr(tool, "find_snaps", original_find_snaps)
    monkeypatch.setenv("MAMEY_PACKAGES", str(package))
    blocked=package/"subfolder";blocked.mkdir()
    if kind == "duplicate":
        (package/"SOFTWARE_Project_Memory_Snapshot.json").rename(package/"SID1_Project_Memory_Snapshot.json")
        (blocked/"SID1_Project_Memory_Snapshot.json").write_text("{}")
    else:
        real=tool.os.scandir
        def denied(path):
            if Path(path) == blocked: raise PermissionError("synthetic denied")
            return real(path)
        monkeypatch.setattr(tool.os,"scandir",denied)
    before={name:(bank/name).read_bytes() for name in objects}
    with pytest.raises(ValueError,match="DEEP_DATA_SNAPSHOT_"):
        tool.main()
    assert {name:(bank/name).read_bytes() for name in objects} == before
    assert not calls["core"] and not calls["finer"]
    assert not (bank/".ingest_pending.json").exists()
    assert not (bank/".ingest_state.json").exists()


def test_external_receipt_symlink_holds_native_bank(native_case, tmp_path, monkeypatch):
    bank, package, evidence, objects, calls = native_case
    outside=tmp_path/"outside";outside.mkdir();(outside/"SID1_AntiSMASH_Evidence_Parse.json").write_text('{"json_mode":"full"}')
    (package/"external").symlink_to(outside,target_is_directory=True)
    before={name:(bank/name).read_bytes() for name in objects}
    with pytest.raises(ValueError,match="DEEP_DATA_DISCOVERY_HOLD"):
        tool.main()
    assert {name:(bank/name).read_bytes() for name in objects}==before
    assert not calls["core"] and not calls["finer"]
    assert not (bank/".ingest_pending.json").exists()
    assert not (bank/".ingest_state.json").exists()


@pytest.mark.parametrize("snapshot_value", [None, [], {}, {"source_scans": None}, {"source_scans": []}])
def test_selected_snapshot_invalid_shape_holds_native_bank(native_case, snapshot_value):
    bank, package, evidence, objects, calls = native_case
    snapshot=package/"SOFTWARE_Project_Memory_Snapshot.json"
    snapshot.write_text(json.dumps(snapshot_value))
    before={name:(bank/name).read_bytes() for name in objects}
    with pytest.raises(ValueError,match="DEEP_DATA_SNAPSHOT_SCHEMA_HOLD"):
        tool.main()
    assert {name:(bank/name).read_bytes() for name in objects}==before
    assert not calls["core"] and not calls["finer"]
    assert not (bank/".ingest_pending.json").exists()
    assert not (bank/".ingest_state.json").exists()
