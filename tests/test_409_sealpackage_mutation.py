"""tests/test_409_sealpackage_mutation.py — CLAUDE_409_sealpackage_mutation lane.

Fail-before / pass-after coverage for the seal-package mutation bug recorded in
development/DELIVERABLE_SWEEP_cohort.md ("seal-package mutates the sealed package
despite --out"): `mamey seal-package <pkg> --out <elsewhere>` rewrote
`<pkg>/package_status.json` in place, because its package_validate QC gate called
`validate.validate_package(pkg)`, whose final step unconditionally writes the
package_status.json receipt back into the package.

The fix adds a read-only opt-out to validate_package (write_status_receipt=False,
default True) and has seal_package's gate use it. package_status.json is a
MUTABLE_RECEIPT (checksum-exempt), so the mutation did not break checksums_sha256.txt,
but it still mutated a sealed package during a --out-redirected advisory read.

These tests pin the exact fixed code path; no full sealed package is required.
"""
import inspect
from pathlib import Path

import mamey  # noqa: F401
from mamey import validate as validate_mod
from mamey import seal_package as seal_mod


# --------------------------------------------------------------------------- #
# 1. validate_package exposes the read-only opt-out
# --------------------------------------------------------------------------- #
def test_validate_package_accepts_write_status_receipt_flag():
    """PASS-AFTER: validate_package has a write_status_receipt parameter (default True).
    FAIL-BEFORE: the parameter does not exist."""
    sig = inspect.signature(validate_mod.validate_package)
    assert "write_status_receipt" in sig.parameters
    assert sig.parameters["write_status_receipt"].default is True


# --------------------------------------------------------------------------- #
# 2. read-only validate does NOT write package_status.json into the package
# --------------------------------------------------------------------------- #
def test_validate_read_only_does_not_write_status_receipt(tmp_path):
    """PASS-AFTER: with write_status_receipt=False the on-disk receipt is never
    created (the recomputed receipt is still returned in-memory).
    FAIL-BEFORE: validate_package had no such flag -> TypeError."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    result = validate_mod.validate_package(pkg, write_status_receipt=False)
    assert not (pkg / "package_status.json").exists()
    assert "package_status_receipt" in result  # still computed, just not persisted


def test_validate_default_still_writes_status_receipt(tmp_path):
    """Regression guard: the DEFAULT (write_status_receipt=True) — the documented
    behaviour of `mamey validate` and of the seal pipeline — still persists the receipt."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    validate_mod.validate_package(pkg)
    assert (pkg / "package_status.json").exists()


def test_read_only_validate_leaves_existing_receipt_byte_and_mtime_identical(tmp_path):
    """The precise DELIVERABLE_SWEEP symptom: a read-only pass must not touch an
    already-sealed package_status.json — not one byte, not the mtime.
    FAIL-BEFORE: the unconditional rewrite advanced the mtime (and would change the
    bytes whenever the recomputed status differed)."""
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    sealed = pkg / "package_status.json"
    sealed.write_text('{"package_status": "MAMEY_COMPLETE", "sealed": true}\n', encoding="utf-8")
    import os
    old = (1_700_000_000, 1_700_000_000)  # fixed atime/mtime in the past
    os.utime(sealed, old)
    before_bytes = sealed.read_bytes()
    before_mtime = sealed.stat().st_mtime

    validate_mod.validate_package(pkg, write_status_receipt=False)

    assert sealed.read_bytes() == before_bytes
    assert sealed.stat().st_mtime == before_mtime


# --------------------------------------------------------------------------- #
# 3. seal-package's QC gate calls the validator read-only
# --------------------------------------------------------------------------- #
def test_seal_package_validate_gate_is_read_only(tmp_path, monkeypatch):
    """PASS-AFTER: _gate_package_validate passes write_status_receipt=False so the
    seal-package advisory pass cannot mutate the package it inspects.
    FAIL-BEFORE: the gate called validate_package without the flag (default write)."""
    seen = {}

    def _spy(package_dir, **kwargs):
        seen.update(kwargs)
        return {"status": "PASS"}

    # seal_package imports validate_package from mamey.validate at call time, so patch there.
    monkeypatch.setattr(validate_mod, "validate_package", _spy)
    gate = seal_mod._gate_package_validate(Path(tmp_path))
    assert seen.get("write_status_receipt") is False
    assert gate.status == "PASS"
