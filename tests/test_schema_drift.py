"""Test the schema-drift gate (G1): aligned sources pass (0), drift fails closed (1)."""
import json
import os
import subprocess
import sys

TOOL = os.path.join(os.path.dirname(__file__), "..", "tools", "check_schema_drift.py")


def _mk(tmp_path, name, version, extra=None):
    d = tmp_path / name / "package"
    d.mkdir(parents=True)
    man = {"strain_id": name, "workflow_version": version, "bgc_counts": {}, "bgcs": []}
    if extra:
        man.update(extra)
    (d / "manifest.json").write_text(json.dumps(man))
    return str(d)


def _run(*pkgs, expect=None):
    cmd = [sys.executable, TOOL, "--packages", *pkgs]
    if expect:
        cmd += ["--expect", expect]
    return subprocess.run(cmd, capture_output=True, text=True)


def test_aligned_sources_pass(tmp_path):
    a = _mk(tmp_path, "A", "9.7.24")
    b = _mk(tmp_path, "B", "9.7.24")
    r = _run(a, b)
    assert r.returncode == 0
    assert "no drift" in r.stdout


def test_version_drift_fails_closed(tmp_path):
    a = _mk(tmp_path, "A", "9.7.24")
    c = _mk(tmp_path, "C", "9.7.23")
    r = _run(a, c)
    assert r.returncode == 1
    assert "VERSION DRIFT" in r.stdout


def test_key_signature_drift_fails_closed(tmp_path):
    a = _mk(tmp_path, "A", "9.7.24")
    d = _mk(tmp_path, "D", "9.7.24", extra={"legacy_field": 1})
    r = _run(a, d)
    assert r.returncode == 1
    assert "KEY-SIGNATURE DRIFT" in r.stdout
    assert "legacy_field" in r.stdout


def test_expected_version_violation(tmp_path):
    a = _mk(tmp_path, "A", "9.7.23")
    r = _run(a, expect="9.7.24")
    assert r.returncode == 1
    assert "EXPECTED 9.7.24" in r.stdout


def _mk_bgcs(tmp_path, dirname, version, bgcs, strain=None):
    d = tmp_path / dirname / "package"
    d.mkdir(parents=True)
    man = {"strain_id": strain or dirname, "workflow_version": version, "bgc_counts": {}, "bgcs": bgcs}
    (d / "manifest.json").write_text(json.dumps(man))
    return str(d)


def test_pk_collision_fails_closed(tmp_path):
    # same strain_id + same BGC id across two sources -> duplicate global key
    a = _mk_bgcs(tmp_path, "S_a", "9.7.24", [{"bgc_id": "BGC001", "kcb_top": "BGC0000001 | x"}], strain="S")
    b = _mk_bgcs(tmp_path, "S_b", "9.7.24", [{"bgc_id": "BGC001", "kcb_top": "BGC0000001 | x"}], strain="S")
    r = _run(a, b)
    assert r.returncode == 1
    assert "KEY COLLISION" in r.stdout


def test_unprovenanced_kcb_fails_closed(tmp_path):
    a = _mk_bgcs(tmp_path, "T", "9.7.24", [{"bgc_id": "BGC002", "kcb_top": "spore pigment"}])
    r = _run(a)
    assert r.returncode == 1
    assert "UN-PROVENANCED KCB" in r.stdout


def test_provenanced_kcb_passes(tmp_path):
    a = _mk_bgcs(tmp_path, "U", "9.7.24", [{"bgc_id": "BGC003", "kcb_top": "BGC0002460.3 | loonamycin"}])
    r = _run(a)
    assert r.returncode == 0
    assert "no drift" in r.stdout
