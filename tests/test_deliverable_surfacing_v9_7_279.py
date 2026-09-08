"""v9.7.279 deliverable-surfacing gate.

The sealed per-strain Complete_Package.zip is the run deliverable, but operators
(human or LLM) kept missing it because the only pointer was one terse mid-run line
and the instruction to surface it lived in prose docs. The gate makes delivery
instruction-independent: every `mamey run` prints an explicit DELIVERABLES block as
its final stdout AND writes a machine-readable HANDBACK.json to the outdir.

This locks both behaviors on the single-strain path (the path the intake harness
drives, one `mamey run --strain X` per strain), using the public smoke fixture so the
test ships safely in every tier.
"""
from __future__ import annotations
import json
import os
import pathlib
import subprocess
import sys
import tempfile

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ZIP = ROOT / "examples" / "test_data" / "smoke_antismash_small.zip"
pytestmark = pytest.mark.skipif(not ZIP.exists(), reason="smoke fixture absent")


@pytest.fixture(scope="module")
def run_out():
    out = tempfile.mkdtemp(prefix="deliv_")
    env = dict(os.environ, PYTHONPATH=str(ROOT))
    proc = subprocess.run(
        [sys.executable, "-m", "mamey", "run", "--strain", "DELIV_TEST",
         "--input-zip", str(ZIP), "--taxonomy", "Streptomyces sp.",
         "--source", "test", "--outdir", out, "--mode", "standard",
         "--release", "PUBLIC", "--brief", "none", "--json-evidence", "off"],
        check=True, capture_output=True, timeout=300, env=env, text=True)
    return out, proc.stdout


def test_handback_json_written(run_out):
    out, _ = run_out
    hb_path = os.path.join(out, "HANDBACK.json")
    assert os.path.exists(hb_path), "HANDBACK.json not written to outdir"
    hb = json.load(open(hb_path))
    assert hb["schema"] == "mamey_handback_v1"
    assert hb["primary_deliverables"], "no primary_deliverables recorded"


def test_handback_points_at_a_real_zip(run_out):
    out, _ = run_out
    hb = json.load(open(os.path.join(out, "HANDBACK.json")))
    d = hb["primary_deliverables"][0]
    # the pointer must resolve to a real, non-trivial sealed package on disk
    assert d["zip"].endswith("_Complete_Package.zip")
    assert os.path.exists(d["zip"]), f"handback zip does not exist: {d['zip']}"
    assert d["bytes"] == os.path.getsize(d["zip"])
    assert d["bytes"] > 1024, "sealed package suspiciously small"


def test_stdout_carries_deliverables_block(run_out):
    _, stdout = run_out
    # the operator-facing block must be present and name the zip
    assert "DELIVERABLES" in stdout
    assert "_Complete_Package.zip" in stdout
    # and it must instruct against substituting a hand-rolled subset
    assert "hand-rolled" in stdout
