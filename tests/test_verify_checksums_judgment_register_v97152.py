"""Regression test — v9.7.151c audit finding.

`verify_checksums()` in mamey/validate.py hardcoded a `mutable` exemption set
of exactly three filenames (run_phase_receipts.jsonl, package_status.json,
claim_safety_status.json), omitting `*_judgment_register.json` — the single
file whose entire documented purpose (per `mamey ingest-receipts --help` and
`mode_b_receipt.py`'s own module docstring) is to be rewritten after package
seal. Every legitimate post-seal `ingest-receipts` call therefore permanently
tripped `mamey validate`'s checksum-integrity gate to FAIL, even on packages
with package_status_receipt.terminal_status correctly reporting MAMEY_COMPLETE.

Found by running `mamey validate` against a real sealed package immediately
after a real `mamey ingest-receipts` call during the v9.7.151c bundle audit
(AS-902 Mode B card migration session) — not a synthetic repro.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from mamey.validate import verify_checksums


def _write_checksummed_package(tmp_path: Path, files: dict[str, str]) -> Path:
    """Write `files` (rel_path -> content) plus a checksums_sha256.txt computed
    from their initial content, returning the package dir."""
    pkg = tmp_path / "package"
    pkg.mkdir()
    lines = []
    for rel, content in files.items():
        p = pkg / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        lines.append(f"{digest}  {rel}")
    (pkg / "checksums_sha256.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return pkg


def test_judgment_register_mutation_does_not_fail_checksum_gate(tmp_path):
    """The core regression: a post-seal judgment_register.json rewrite (the
    documented effect of `ingest-receipts`) must not trip verify_checksums."""
    pkg = _write_checksummed_package(tmp_path, {
        "AS-902_judgment_register.json": json.dumps({"bgcs": {}}),
        "AS-902_4_triage_board.csv": "BGC_ID,AB_auto\nBGC007,45\n",
    })

    # Simulate what ingest-receipts does: rewrite the register with new content.
    (pkg / "AS-902_judgment_register.json").write_text(
        json.dumps({"bgcs": {"BGC007": {"status": "COMPLETE"}}}), encoding="utf-8"
    )

    errors = verify_checksums(pkg)
    assert errors == [], f"judgment_register.json mutation should be exempt, got: {errors}"


def test_judgment_register_exemption_is_suffix_matched_per_strain(tmp_path):
    """The register is per-strain prefixed (e.g. AS-902_judgment_register.json,
    SID-001_judgment_register.json) — the exemption must match by suffix, not
    by a single hardcoded exact filename, or every strain except one hardcoded
    name would still false-positive."""
    pkg = _write_checksummed_package(tmp_path, {
        "SID-001_judgment_register.json": json.dumps({"bgcs": {}}),
    })
    (pkg / "SID-001_judgment_register.json").write_text(
        json.dumps({"bgcs": {"BGC001": {"status": "COMPLETE"}}}), encoding="utf-8"
    )
    errors = verify_checksums(pkg)
    assert errors == []


def test_non_mutable_file_mismatch_still_fails(tmp_path):
    """Guard against over-broadening the fix: a genuine corruption of a
    non-exempt, non-mutable file must still be caught."""
    pkg = _write_checksummed_package(tmp_path, {
        "AS-902_4_triage_board.csv": "BGC_ID,AB_auto\nBGC007,45\n",
    })
    # Corrupt it post-checksum, simulating real drift/corruption.
    (pkg / "AS-902_4_triage_board.csv").write_text("CORRUPTED", encoding="utf-8")

    errors = verify_checksums(pkg)
    assert len(errors) == 1
    assert "AS-902_4_triage_board.csv" in errors[0]
    assert "checksum mismatch" in errors[0]


def test_other_mutable_files_still_exempt(tmp_path):
    """Regression guard: the pre-existing exact-name exemptions
    (run_phase_receipts.jsonl, package_status.json, claim_safety_status.json)
    must continue to work after switching part of the set to suffix matching."""
    pkg = _write_checksummed_package(tmp_path, {
        "run_phase_receipts.jsonl": '{"phase": "start"}\n',
        "package_status.json": '{"status": "MAMEY_COMPLETE"}',
        "claim_safety_status.json": '{"pass": true}',
    })
    for rel in ("run_phase_receipts.jsonl", "package_status.json", "claim_safety_status.json"):
        (pkg / rel).write_text("mutated content", encoding="utf-8")

    errors = verify_checksums(pkg)
    assert errors == []
