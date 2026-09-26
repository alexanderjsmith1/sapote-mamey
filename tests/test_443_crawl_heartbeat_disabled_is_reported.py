"""v9.7.443: a GAP lane whose crawl_manifest.py is absent must say its heartbeat is off.

run_lane.sh names every lane `..._GAP_AS<N>`, so nr_rid_runner.py always tries to load
crawl_manifest.py from its own folder. That file is not shipped beside the runner, and the old
`except Exception: pass` turned the heartbeat off for every bundle run with no word to anyone.
"""
import os
import subprocess
import sys
from pathlib import Path

RUNNER = Path(__file__).resolve().parents[1] / "tools" / "blastp_crawl" / "nr_rid_runner.py"


def _import_runner(rid_base: str) -> subprocess.CompletedProcess:
    code = ("import importlib.util as u, sys; "
            f"s = u.spec_from_file_location('nr_rid_runner_probe', r'{RUNNER}'); "
            "m = u.module_from_spec(s); s.loader.exec_module(m)")
    env = dict(os.environ, RID_BASE=rid_base, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=60)


def test_gap_lane_without_manifest_reports_disabled_heartbeat():
    if (RUNNER.parent / "crawl_manifest.py").exists():
        import pytest
        pytest.skip("crawl_manifest.py is shipped; the absent-file branch cannot be exercised")
    r = _import_runner("_STRAINGAP_SINGLE_CLNR_GAP_AS7")
    assert r.returncode == 0, r.stderr
    assert "heartbeat disabled for lane AS7" in r.stderr
    assert "crawl_manifest.py not found" in r.stderr


def test_non_gap_lane_stays_quiet():
    r = _import_runner("_NR_RID")
    assert r.returncode == 0, r.stderr
    assert "heartbeat" not in r.stderr
