"""Publication failures must never look successful or silently destroy prior outputs."""

import hashlib
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PRODUCER = ROOT / "tools" / "build_placement_ggtree_inputs.py"
SUFFIXES = ("_pruned.nwk", "_ggtree_annotation.tsv", "_metadata_receipt.json")


def _mod():
    spec = importlib.util.spec_from_file_location("_placement_publish", PRODUCER)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _setup(tmp_path, existing):
    tree = tmp_path / "tree.nwk"
    tree.write_text(
        "(SID_1:0.1,Streptomyces_coelicolor_NC_003888.3:0.1);\n",
        encoding="utf-8",
    )
    prefix = tmp_path / "result"
    finals = [Path(str(prefix) + suffix) for suffix in SUFFIXES]
    before = {}
    if existing:
        for index, path in enumerate(finals):
            path.write_bytes(f"sentinel-{index}".encode("ascii"))
            before[path] = path.read_bytes()
    return tree, prefix, finals, before


def _snapshot(paths):
    out = {}
    for path in paths:
        if path.exists():
            data = path.read_bytes()
            out[path.name] = {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
        else:
            out[path.name] = {"absent": True}
    return out


@pytest.mark.parametrize("publication_position", [1, 2, 3])
@pytest.mark.parametrize("existing", [False, True])
def test_replace_failure_rolls_back_every_final(
    tmp_path, monkeypatch, capsys, publication_position, existing
):
    module = _mod()
    tree, prefix, finals, before = _setup(tmp_path, existing)
    real_replace = os.replace
    count = 0

    def fail_publication(src, dst):
        nonlocal count
        if Path(dst) in finals and str(src).endswith(".tmp"):
            count += 1
            if count == publication_position:
                raise OSError(f"injected publication failure {publication_position}")
        return real_replace(src, dst)

    monkeypatch.setattr(module.os, "replace", fail_publication)
    monkeypatch.setattr(sys, "argv", [
        str(PRODUCER), "--graft", str(tree), "--out-prefix", str(prefix), "--keep-all-refs",
    ])
    caught = None
    try:
        module._run_or_refuse()
    except BaseException as exc:
        caught = exc

    residue = list(tmp_path.glob("result_*"))
    observed = {
        "exception": type(caught).__name__ if caught else None,
        "status": getattr(caught, "code", None),
        "finals": _snapshot(finals),
        "residue": sorted(path.name for path in residue),
    }
    assert isinstance(caught, SystemExit) and caught.code == 2, json.dumps(observed, sort_keys=True)
    assert "OUTPUT_PUBLICATION_FAILED_ROLLED_BACK" in capsys.readouterr().err
    if existing:
        assert {path: path.read_bytes() for path in finals} == before
    else:
        assert not any(path.exists() for path in finals)
    assert not list(tmp_path.glob("result_*.tmp"))
    assert not list(tmp_path.glob("result_*.prepublish.bak"))
    assert not (tmp_path / "result_publication_recovery.json").exists()


def test_rollback_failure_preserves_backup_and_recovery_receipt(tmp_path, monkeypatch, capsys):
    module = _mod()
    tree, prefix, finals, before = _setup(tmp_path, True)
    real_replace = os.replace
    publications = 0

    def fail_publish_and_one_restore(src, dst):
        nonlocal publications
        src_path, dst_path = Path(src), Path(dst)
        if dst_path in finals and str(src).endswith(".tmp"):
            publications += 1
            if publications == 2:
                raise OSError("injected publication failure")
        if src_path.name.endswith(".prepublish.bak") and dst_path == finals[0]:
            raise OSError("injected rollback failure")
        return real_replace(src, dst)

    monkeypatch.setattr(module.os, "replace", fail_publish_and_one_restore)
    monkeypatch.setattr(sys, "argv", [
        str(PRODUCER), "--graft", str(tree), "--out-prefix", str(prefix), "--keep-all-refs",
    ])
    with pytest.raises(SystemExit) as caught:
        module._run_or_refuse()

    assert caught.value.code == 2
    assert "OUTPUT_PUBLICATION_RECOVERY_REQUIRED" in capsys.readouterr().err
    backup = Path(str(finals[0]) + ".prepublish.bak")
    assert backup.read_bytes() == before[finals[0]]
    recovery = tmp_path / "result_publication_recovery.json"
    recovery_text = recovery.read_text(encoding="utf-8")
    payload = json.loads(recovery_text)
    assert payload["status"] == "RECOVERY_REQUIRED"
    assert payload["outputs"][0]["original_sha256"] == hashlib.sha256(before[finals[0]]).hexdigest()
    assert payload["outputs"][0]["backup"] == backup.name
    assert payload["rollback_errors"]
    assert str(tmp_path) not in recovery_text
    assert finals[1].read_bytes() == before[finals[1]]
    assert finals[2].read_bytes() == before[finals[2]]


def test_success_removes_backups_and_recovery_receipt(tmp_path, monkeypatch):
    module = _mod()
    tree, prefix, finals, _before = _setup(tmp_path, True)
    monkeypatch.setattr(sys, "argv", [
        str(PRODUCER), "--graft", str(tree), "--out-prefix", str(prefix), "--keep-all-refs",
    ])

    assert module._run_or_refuse() is None
    assert all(path.exists() for path in finals)
    assert not list(tmp_path.glob("result_*.tmp"))
    assert not list(tmp_path.glob("result_*.prepublish.bak"))
    assert not (tmp_path / "result_publication_recovery.json").exists()


def test_backup_prepare_failure_keeps_finals_and_cleans_partial_backups(
    tmp_path, monkeypatch, capsys
):
    module = _mod()
    tree, prefix, finals, before = _setup(tmp_path, True)
    real_backup = module._backup_output
    calls = 0

    def fail_second_backup(path, backup):
        nonlocal calls
        calls += 1
        if calls == 2:
            Path(backup).write_bytes(b"partial-backup")
            raise OSError("injected backup failure")
        return real_backup(path, backup)

    monkeypatch.setattr(module, "_backup_output", fail_second_backup)
    monkeypatch.setattr(sys, "argv", [
        str(PRODUCER), "--graft", str(tree), "--out-prefix", str(prefix), "--keep-all-refs",
    ])
    with pytest.raises(SystemExit) as caught:
        module._run_or_refuse()

    assert caught.value.code == 2
    assert "OUTPUT_PUBLICATION_PREPARE_FAILED" in capsys.readouterr().err
    assert {path: path.read_bytes() for path in finals} == before
    assert not list(tmp_path.glob("result_*.prepublish.bak"))
    assert not (tmp_path / "result_publication_recovery.json").exists()


def test_pending_recovery_refuses_before_staging_or_modifying_finals(
    tmp_path, monkeypatch, capsys
):
    module = _mod()
    tree, prefix, finals, before = _setup(tmp_path, True)
    recovery = tmp_path / "result_publication_recovery.json"
    recovery.write_text('{"status":"RECOVERY_REQUIRED"}\n', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [
        str(PRODUCER), "--graft", str(tree), "--out-prefix", str(prefix), "--keep-all-refs",
    ])
    with pytest.raises(SystemExit) as caught:
        module._run_or_refuse()

    assert caught.value.code == 2
    assert "OUTPUT_PUBLICATION_RECOVERY_PENDING" in capsys.readouterr().err
    assert {path: path.read_bytes() for path in finals} == before
    assert not list(tmp_path.glob("result_*.tmp"))
    assert json.loads(recovery.read_text(encoding="utf-8"))["status"] == "RECOVERY_REQUIRED"
