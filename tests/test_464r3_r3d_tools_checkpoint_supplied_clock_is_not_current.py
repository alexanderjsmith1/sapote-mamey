"""A backdated --now makes the checkpoint a simulated assessment: nothing is labelled current."""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import socket
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "tools" / "checkpoint_status.py"
_spec = importlib.util.spec_from_file_location("checkpoint_status_r3d", PATH)
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)

OLD = dt.datetime(2026, 1, 1, 12, tzinfo=dt.timezone.utc)


def _manifest(tmp_path, observed):
    ledger = tmp_path / "ledger.json"
    ledger.write_text("{}")
    inbox = tmp_path / "inbox.json"
    inbox.write_text(json.dumps({"observed_at": observed.isoformat(),
                                 "source": {"path": str(ledger), "sha256": m.digest(ledger)},
                                 "open_unique_id_count": 4}))
    alloc = tmp_path / "alloc.json"
    alloc.write_text(json.dumps({"schema": "sapote.scheduler-allocation.v1", "host_id": socket.gethostname(),
                                 "observed_at": observed.isoformat(), "allocated_cores": 2}))
    manifest = {"schema": m.SCHEMA, "sources": [
        {"id": "inbox", "kind": "inbox", "path": str(inbox), "sha256": m.digest(inbox)},
        {"id": "alloc", "kind": "allocation", "path": str(alloc), "sha256": m.digest(alloc)}]}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest))
    return manifest, path


def test_backdated_clock_is_a_simulated_assessment(tmp_path):
    manifest, _ = _manifest(tmp_path, OLD)
    clock = m.clock_record(OLD, dt.datetime.now(dt.timezone.utc))
    assert clock["state"] == "SIMULATED_CLOCK"
    r = m.build(manifest, tmp_path, OLD, tmp_path, clock)
    assert r["inbox"]["state"] == "SIMULATED_CLOCK_ASSESSMENT"
    assert r["inbox"]["current_open_count"] is None
    assert r["resources"]["allocation_state"] == "SIMULATED_CLOCK_ASSESSMENT"
    assert r["resources"]["allocated_cores"] is None
    assert r["clock"]["system_clock"]
    assert "simulated, historical assessment" in m.markdown(r)


def test_system_clock_still_admits_a_current_receipt(tmp_path):
    now = dt.datetime.now(dt.timezone.utc)
    manifest, _ = _manifest(tmp_path, now)
    r = m.build(manifest, tmp_path, now, tmp_path, m.clock_record(None, now))
    assert r["inbox"]["state"] == "CURRENT_SNAPSHOT"
    assert r["resources"]["allocated_cores"] == 2


def test_cli_records_the_supplied_clock(tmp_path):
    _, path = _manifest(tmp_path, OLD)
    out = tmp_path / "out"
    proc = subprocess.run([sys.executable, str(PATH), str(path), "--out", str(out), "--now", OLD.isoformat()],
                          capture_output=True, text=True)
    assert proc.returncode in (0, 2), proc.stderr
    r = json.loads((out / "CHECKPOINT.json").read_text()) if proc.returncode == 0 else json.loads(proc.stdout)
    assert r["inbox"]["state"] == "SIMULATED_CLOCK_ASSESSMENT"
    if proc.returncode == 0:
        assert json.loads((out / "CHECKPOINT.json").read_text())["clock"]["state"] == "SIMULATED_CLOCK"
