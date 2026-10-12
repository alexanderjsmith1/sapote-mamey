"""Actual harness/engine privacy integration using the shipped tiny generic fixture.

Requires the companion PRIVATE-default proposal. No private research data or
external/network examples. The engine, package reads, receipt binding and CSV
publication are real; the wrapper only captures argv and bounds immediate-child
runtime using the harness's existing monitor. It is not a process-tree limit.
"""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = ROOT / "tools/intake_harness.py"
FIXTURE = ROOT / "examples/test_data/smoke_antismash_small.zip"


def _digest_tree(path):
    return {str(p.relative_to(path)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in path.rglob("*") if p.is_file()}


def _csv(path):
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


@pytest.mark.parametrize("explicit_release,expected", [(None, "PRIVATE"), ("PUBLIC", "PUBLIC")])
def test_actual_engine_package_registry_and_resume_policy(tmp_path, monkeypatch, capsys,
                                                         explicit_release, expected):
    spec = importlib.util.spec_from_file_location("intake_private_integration", HARNESS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert FIXTURE.is_file(), "required generic fixture missing; do not substitute research data"
    source = tmp_path / "generic_reference.zip"
    shutil.copyfile(FIXTURE, source)
    out = tmp_path / "out"
    registry, metrics = out / "registry.csv", out / "metrics.csv"
    argv = ["intake_harness.py", "--inputs", str(source), "--outdir", str(out),
            "--registry", str(registry), "--metrics", str(metrics),
            "--source", "synthetic software fixture"]
    if explicit_release:
        argv.extend(["--release", explicit_release])
    monkeypatch.setattr(sys, "argv", argv)
    calls = []
    real_monitor = module.run_monitored
    def capture_real_engine(command, **kwargs):
        calls.append(list(command))
        return real_monitor(command, timeout=120, **kwargs)
    monkeypatch.setattr(module, "run_monitored", capture_real_engine)
    assert module.main() == 0, capsys.readouterr().out
    assert len(calls) == 1
    command = calls[0]
    assert command[command.index("--release") + 1] == expected
    assert Path(command[1]) == ROOT / "mamey_run.py"
    rows = _csv(registry)
    assert len(rows) == 1 and rows[0]["release"] == expected
    strain = rows[0]["strain"]
    package = out / strain / "package"
    manifest = json.loads((package / "manifest_short.json").read_text())
    intake = json.loads((package / f"{strain}_1_intake.json").read_text())
    assert manifest["release"] == intake["release"] == expected
    receipt = json.loads((out / strain / "intake_completion_receipt.json").read_text())
    assert receipt["run"]["options"]["release"] == expected
    assert receipt["output"] == module._tree_binding(str(package))
    before_package, before_registry = _digest_tree(package), registry.read_bytes()
    before_receipt = (out / strain / "intake_completion_receipt.json").read_bytes()

    def refuse(*args, **kwargs):
        raise AssertionError("resume must hold/skip before staging or launching engine")
    monkeypatch.setattr(module, "detect_and_stage", refuse)
    monkeypatch.setattr(module, "run_monitored", refuse)
    monkeypatch.setattr(sys, "argv", [*argv, "--resume"])
    assert module.main() == 0
    assert "SKIP (verified completion receipt)" in capsys.readouterr().out
    assert _digest_tree(package) == before_package
    assert registry.read_bytes() == before_registry

    changed = list(argv)
    new_policy = "PRIVATE" if expected == "PUBLIC" else "PUBLIC"
    if "--release" in changed:
        changed[changed.index("--release") + 1] = new_policy
    else:
        changed.extend(["--release", new_policy])
    monkeypatch.setattr(sys, "argv", [*changed, "--resume"])
    assert module.main() == 1
    assert "RESUME_BINDING_HOLD" in capsys.readouterr().out
    assert _digest_tree(package) == before_package
    assert registry.read_bytes() == before_registry
    assert (out / strain / "intake_completion_receipt.json").read_bytes() == before_receipt
    assert _csv(metrics)[-1]["status"] == "RUN_FAILED"
