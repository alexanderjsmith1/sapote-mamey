"""v9.7.398 — `mamey doctor`'s write-permission probe used `mkdir(parents=True)` to create
`runs/_doctor_probe/` but only `rmdir()`'d the leaf, leaving an empty `runs/` directory behind
permanently at the bundle root after every doctor invocation.

That litter trips `tools/public_release_audit.py`'s `runs*` glob check (`PUBLIC RELEASE AUDIT:
FAIL`), which is a required step (no `continue-on-error`) in `.github/workflows/ci.yml`'s
release-gates job — reproduced live against the sealed `.397` candidate before this fix: running
`mamey doctor` once, then `public_release_audit.py .`, returned exit 1 with `✗ untracked run dir
at root: runs`. After the fix, the same sequence returns exit 0 / PASS.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import pytest

from mamey.cli import doctor_command

_BUNDLE_ROOT = Path(__file__).resolve().parent.parent
_RUNS = _BUNDLE_ROOT / "runs"


@pytest.fixture
def clean_runs_dir():
    """Save/restore whatever runs/ state exists around this real-repo-relative test."""
    preexisted = _RUNS.exists()
    saved = None
    if preexisted:
        saved = _BUNDLE_ROOT / "runs.bc2_test_saved"
        shutil.move(str(_RUNS), str(saved))
    yield
    if _RUNS.exists():
        shutil.rmtree(_RUNS, ignore_errors=True)
    if saved is not None:
        shutil.move(str(saved), str(_RUNS))


def test_doctor_leaves_no_runs_dir_when_none_pre_existed(clean_runs_dir):
    assert not _RUNS.exists()
    doctor_command(argparse.Namespace())
    assert not _RUNS.exists(), (
        "mamey doctor left an empty runs/ directory behind — this is exactly what trips "
        "tools/public_release_audit.py's 'untracked run dir at root' check"
    )


def test_doctor_preserves_a_pre_existing_populated_runs_dir(clean_runs_dir):
    marker = _RUNS / "AS-999" / "package" / "marker.txt"
    marker.parent.mkdir(parents=True)
    marker.write_text("real output — must survive", encoding="utf-8")
    doctor_command(argparse.Namespace())
    assert marker.exists() and marker.read_text() == "real output — must survive", (
        "a pre-existing runs/ directory with real content must never be removed by the probe"
    )


def test_public_release_audit_passes_after_doctor_when_it_previously_failed(clean_runs_dir):
    """End-to-end: the exact CI sequence (doctor, then the release gate) that FAILED on pristine
    now passes, without invoking the audit module's own import machinery from inside a pytest
    process (it shells out cleanly via its own __main__ guard in normal use; here we call the
    scan function directly for a fast, hermetic check)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "public_release_audit_bc2_check", _BUNDLE_ROOT / "tools" / "public_release_audit.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert not _RUNS.exists()
    doctor_command(argparse.Namespace())
    hits = mod.audit(_BUNDLE_ROOT)
    assert not any("untracked run dir" in h for h in hits), hits
