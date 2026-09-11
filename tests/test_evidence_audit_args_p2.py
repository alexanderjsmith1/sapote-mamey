"""v9.7.87 P2-args: evidence_conservation_audit accepts --raw/--package and positional forms."""
from __future__ import annotations
import json, subprocess, sys, pathlib

TOOL = pathlib.Path(__file__).resolve().parents[1] / "tools" / "evidence_conservation_audit.py"


def _mk(tmp_path):
    raw = tmp_path / "raw.json"; pkg = tmp_path / "pkg.json"
    raw.write_text(json.dumps({"a": 1})); pkg.write_text(json.dumps({"b": 2}))
    return str(raw), str(pkg)


def test_named_flags_accepted(tmp_path):
    raw, pkg = _mk(tmp_path)
    r = subprocess.run([sys.executable, str(TOOL), "--raw", raw, "--package", pkg],
                       capture_output=True, text=True)
    assert "EVIDENCE CONSERVATION AUDIT" in r.stdout


def test_positional_backward_compat(tmp_path):
    raw, pkg = _mk(tmp_path)
    r = subprocess.run([sys.executable, str(TOOL), raw, pkg], capture_output=True, text=True)
    assert "EVIDENCE CONSERVATION AUDIT" in r.stdout


def test_missing_arg_clean_error(tmp_path):
    raw, pkg = _mk(tmp_path)
    r = subprocess.run([sys.executable, str(TOOL), "--package", pkg], capture_output=True, text=True)
    assert r.returncode != 0
    assert "provide both" in (r.stderr + r.stdout)
