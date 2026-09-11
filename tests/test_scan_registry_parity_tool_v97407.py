"""Regression coverage for the reusable B2 registry/fallback parity receipt."""
from __future__ import annotations

import importlib.util
import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "scan_registry_parity.py"
SMOKE = ROOT / "examples" / "test_data" / "smoke_antismash_small.zip"


def _tool_module():
    spec = importlib.util.spec_from_file_location("scan_registry_parity", TOOL)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_smoke_fixture_has_byte_identical_registry_and_fallback_outputs(tmp_path):
    assert SMOKE.exists(), "sealed code tier must ship the smoke antiSMASH fixture"
    output = tmp_path / "parity.json"
    assert _tool_module().main(["--input", str(SMOKE), "--output", str(output)]) == 0
    text = output.read_text(encoding="utf-8")
    assert '"status": "PASS"' in text
    assert '"registry_active": true' in text
    assert '"fallback_active": false' in text


def test_tool_runs_as_a_direct_bundle_script(tmp_path):
    output = tmp_path / "parity-subprocess.json"
    completed = subprocess.run(
        [sys.executable, str(TOOL), "--input", str(SMOKE), "--output", str(output)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "PASS" in completed.stdout
