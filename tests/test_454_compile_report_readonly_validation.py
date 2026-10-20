"""v9.7.454: compile-report reads a sealed package without changing a byte, using the REAL validator.

The older reader-route tests replace validate_package with a stub, so they cannot see the validator's default
package_status.json write. These tests keep the real validator and compare every file's bytes and mtime before
and after, on success or refusal, with and without an existing status receipt, and on a repeated run.
"""
import hashlib, json
from pathlib import Path
from types import SimpleNamespace

import pytest

from mamey import compile_report as cr


def _package(tmp_path, status_receipt):
    p = tmp_path / "SYN-1" / "package"; p.mkdir(parents=True)
    (p / "manifest.json").write_text(json.dumps({"strain_id": "SYN-1", "locus_maps": "off"}))
    (p / "SYN-1_2_inventory.csv").write_text("BGC_ID,Contig,Region,Class\nBGC001,ctg,region001,NRPS\n")
    (p / "SYN-1_4_triage_board.csv").write_text("BGC_ID,Lead_tier_auto,Class,Boundary\nBGC001,High,NRPS,Interior\n")
    if status_receipt:
        (p / "package_status.json").write_text('{"synthetic": "stale, non-canonical receipt"}\n')
    digest = lambda f: hashlib.sha256(f.read_bytes()).hexdigest()
    (p / "checksums_sha256.txt").write_text("".join(f"{digest(f)}  {f.name}\n" for f in sorted(p.iterdir())))
    return p


def _snapshot(p):
    return {f.relative_to(p).as_posix(): (hashlib.sha256(f.read_bytes()).hexdigest(), f.stat().st_mtime_ns)
            for f in sorted(p.rglob("*")) if f.is_file()}


def _compile(p):
    args = SimpleNamespace(package_dir=str(p), out=None, pdf=False, strict=False, no_figures=True,
                           toc_depth=1, blastp_waiver="synthetic reason")
    try:
        return cr.compile_report_command(args)
    except SystemExit as refusal:  # a refusal is an outcome too; the original must still be untouched
        return refusal


@pytest.mark.parametrize("status_receipt", [True, False], ids=["stale-status-receipt", "no-status-receipt"])
def test_compile_report_with_real_validator_leaves_sealed_package_untouched(tmp_path, status_receipt):
    p = _package(tmp_path, status_receipt)
    before = _snapshot(p)
    _compile(p)
    assert _snapshot(p) == before
    _compile(p)  # repeated attempt
    assert _snapshot(p) == before


def test_validator_read_only_mode_still_returns_the_result(tmp_path):
    from mamey.validate import validate_package
    p = _package(tmp_path, status_receipt=False)
    before = _snapshot(p)
    result = validate_package(p, write_status_receipt=False)
    assert isinstance(result, dict) and "package_status_receipt" in result
    assert _snapshot(p) == before
