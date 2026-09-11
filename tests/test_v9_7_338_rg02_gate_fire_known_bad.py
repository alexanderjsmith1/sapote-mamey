"""v9.7.338 RG-02 — assert the three validate_package FAIL branches actually FIRE.

The full-round audit (SAPOTE_MAMEY_FULL_ROUND_AUDIT.md, RG-02) flagged three overall-status
FAIL branches in ``validate.validate_package`` that no test ever drove to failure:

  * ``rggmci_gate`` != PASS  -> status FAIL   (validate.py, "elif result.get('rggmci_gate')...")
  * ``file_presence`` == FAIL -> status FAIL   (a REQUIRED suffix missing)
  * ``reporting_v2_gate`` == FAIL -> status FAIL   (a v2-reporting manifest with a broken output)

A FAIL branch that is only ever exercised on GOOD inputs (where it does not fire) is
indistinguishable from a branch that CANNOT fire — the project's own .335 lesson
("verify the gate BITES on a known-bad input, not just that it passes on a known-good one",
see tests/test_v9_7_335_tier1_gates_known_bad_input.py). A regression that silently disabled
any of these three would pass CI today. These tests feed each branch its known-bad artifact
and assert the branch fires AND drives the overall verdict to FAIL, each paired with a control
so a future refactor cannot make the test pass by breaking the gate the other way.

RG-02 is a TEST-ONLY gap: no engine code changes here.

Notes on scope vs. the .338 GATE-11 tests (tests/test_v9_7_338_verdict_gates.py):
  * GATE-11 exercises the *NULL_NO_RGGMCI_PAIRS + parse-error* branch. Case (a) here drives the
    *unexpected/non-PASS status* branch (the ``else`` arm), which GATE-11 does not cover.
"""

from __future__ import annotations

import json
from pathlib import Path

from mamey.validate import validate_package


_LOCKED = ["BGC001", "BGC002"]



def _seal04_write_manifest(pkg) -> None:
    """Write a genuine checksums_sha256.txt covering every file currently in `pkg`.

    Fixtures here previously wrote an empty manifest as filler. Since SEAL-04 that is an
    integrity error in its own right, so the filler is replaced by a real (and trivially
    correct) manifest, keeping these controls focused on the gates they actually test.
    """
    import hashlib as _hashlib
    from pathlib import Path as _Path
    pkg = _Path(pkg)
    lines = []
    for p in sorted(pkg.rglob("*")):
        if not p.is_file() or p.name == "checksums_sha256.txt":
            continue
        rel = p.relative_to(pkg).as_posix()
        lines.append(f"{_hashlib.sha256(p.read_bytes()).hexdigest()}  {rel}")
    (pkg / "checksums_sha256.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

def _make_min_package(
    tmp_path: Path,
    *,
    rggmci: dict | None = None,
    reporting_features: dict | None = None,
    reporting_v2_stubs: bool = False,
    drop_suffix: str | None = None,
) -> Path:
    """Build the smallest package validate_package() accepts (mode=gold), so that a single
    injected defect is the only thing that can drive a FAIL.

    Knobs:
      rggmci             : override the RG-GMCI payload written to *_4A_RGGMCI_full.json.
      reporting_features : if given, written into manifest['reporting_features'] (drives the
                           reporting-v2 gate on/off).
      reporting_v2_stubs : also drop empty/broken stubs for every REPORTING_V2 suffix, so the
                           reporting-v2 gate runs on present-but-BROKEN outputs (not missing).
      drop_suffix        : a REQUIRED_SUFFIXES basename fragment NOT to write (file_presence FAIL).
    """
    pkg = tmp_path / "AS-TEST"
    pkg.mkdir()

    manifest = {
        "strain_id": "AS-TEST",
        "mode": "gold",
        "bgcs": [{"bgc_id": b} for b in _LOCKED],
    }
    if reporting_features is not None:
        manifest["reporting_features"] = reporting_features
    (pkg / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    (pkg / "AS-TEST_2_inventory.csv").write_text(
        "bgc_id,Depth_floor\n"
        "BGC001,full_mode_b\n"
        "BGC002,abbreviated_ledger\n",
        encoding="utf-8",
    )
    if rggmci is None:
        rggmci = {"status": "NULL_NO_RGGMCI_PAIRS", "pairs_total": 0,
                  "reference_record_count": 0, "reference_parse_error_count": 0}
    (pkg / "AS-TEST_4A_RGGMCI_full.json").write_text(json.dumps(rggmci), encoding="utf-8")

    # Every REQUIRED_SUFFIXES entry the min package must carry (except the two written above and
    # checksums, plus enrichment). Keyed by the suffix fragment so drop_suffix can omit exactly one.
    json_stubs = {
        "1_intake.json": "{}",
        "3_scan_states.json": "{}",
        "commit_receipt.json": "{}",
        "Project_Memory_Snapshot.json": "{}",
        "manifest_short.json": "{}",
    }
    csv_stubs = {
        "4A_RGGMCI_ranked_pairs.csv": "col\n",
        "4A_RGGMCI_evidence.csv": "col\n",
        "4_triage_board.csv": "col\n",
        "7_cell_provenance.csv": "col\n",
    }
    for suffix, content in json_stubs.items():
        if suffix == drop_suffix:
            continue
        (pkg / f"AS-TEST_{suffix}").write_text(content, encoding="utf-8")
    for suffix, content in csv_stubs.items():
        if suffix == drop_suffix:
            continue
        (pkg / f"AS-TEST_{suffix}").write_text(content, encoding="utf-8")

    if "5_workbook.xlsx" != drop_suffix:
        (pkg / "AS-TEST_5_workbook.xlsx").write_bytes(b"stub")
    if "issue_log.md" != drop_suffix:
        (pkg / "issue_log.md").write_text("# issues\n", encoding="utf-8")
    (pkg / "OPEN_ME_FIRST.html").write_text("<html></html>", encoding="utf-8")

    if reporting_v2_stubs:
        # Present-but-broken reporting-v2 outputs: files exist (so `missing` == []), but their
        # content is empty/invalid, so the reporting-v2 validator collects parse/schema errors
        # and returns status FAIL through the errors path, not the missing path.
        for suffix in (
            "3_mibig_per_gene.json", "3_mibig_per_gene.csv",
            "3_mibig_convergence.json", "3_mibig_convergence.csv",
            "3_mibig_profile.csv", "3_antismash_structured.json",
            "3_antismash_modules.csv", "3_antismash_ripp_motifs.csv",
            "3_antismash_motifs.csv", "3_antismash_rrefinder.csv",
            "3_length_weighted_capacity.csv", "3_length_weighted_summary.json",
        ):
            (pkg / f"AS-TEST_{suffix}").write_text("", encoding="utf-8")

    # SEAL-04 (v9.7.396): an EMPTY manifest is now itself an integrity error (a zero-scan
    # PASS previously let a tampered package validate clean), so this fixture — which is
    # about other gates, not checksums — writes a real manifest over its own files.
    _seal04_write_manifest(pkg)
    return pkg


# --------------------------------------------------------------------------------------
# Control: the untouched min package is not FAILed by the fixture itself, so any FAIL below
# is attributable to the single injected defect.
# --------------------------------------------------------------------------------------

def test_control_clean_min_package_is_not_failed(tmp_path):
    pkg = _make_min_package(tmp_path)
    result = validate_package(pkg, enrichment_check=True)
    assert result["file_presence"] == "PASS", result.get("missing_required_suffixes")
    assert result["rggmci_gate"] == "PASS", result.get("rggmci_note")
    assert result["reporting_v2_gate"] == "LEGACY_NOT_APPLICABLE", result
    assert result["status"] != "FAIL", result


# --------------------------------------------------------------------------------------
# (a) rggmci_gate FAIL -> status FAIL, via a NON-PASS / unexpected RG-GMCI status with
#     reference_parse_error_count > 0 (the `else` arm, not the GATE-11 NULL+parse arm).
# --------------------------------------------------------------------------------------

def test_non_pass_rggmci_status_with_parse_errors_fails_validate(tmp_path):
    """KNOWN-BAD: an RG-GMCI status that is neither PASS nor NULL_NO_RGGMCI_PAIRS (here with
    reference_parse_error_count>0) must make the rggmci gate FAIL and drive status to FAIL."""
    pkg = _make_min_package(tmp_path, rggmci={
        "status": "REFERENCE_MAP_INCOMPLETE",   # unexpected / non-PASS
        "pairs_total": 0,
        "reference_record_count": 4,
        "reference_map_status": "PARTIAL",
        "reference_parse_error_count": 3,
    })
    result = validate_package(pkg, enrichment_check=True)
    assert result["rggmci_gate"] == "FAIL", result.get("rggmci_note")
    assert result["status"] == "FAIL", (
        "an unexpected non-PASS RG-GMCI status must fail the package; the rggmci_gate->FAIL "
        f"overall-status branch was previously never asserted to fire. got: {result.get('status')!r}"
    )


# --------------------------------------------------------------------------------------
# (b) file_presence FAIL -> status FAIL, via a deleted REQUIRED suffix.
# --------------------------------------------------------------------------------------

def test_missing_required_suffix_fails_validate(tmp_path):
    """KNOWN-BAD: drop a REQUIRED output (4_triage_board.csv) -> file_presence FAIL -> status FAIL."""
    pkg = _make_min_package(tmp_path, drop_suffix="4_triage_board.csv")
    result = validate_package(pkg, enrichment_check=True)
    assert result["file_presence"] == "FAIL", result
    assert any("4_triage_board.csv" == s or s.endswith("4_triage_board.csv")
               for s in result["missing_required_suffixes"]), result["missing_required_suffixes"]
    assert result["status"] == "FAIL", (
        "a missing REQUIRED suffix must drive the overall status to FAIL; the file_presence->FAIL "
        f"branch was previously never asserted to fire. got: {result.get('status')!r}"
    )


# --------------------------------------------------------------------------------------
# (c) reporting_v2_gate FAIL -> status FAIL, via a v2-reporting manifest whose reporting
#     outputs are PRESENT but BROKEN (so the FAIL is the reporting-v2 gate, not file_presence).
# --------------------------------------------------------------------------------------

def test_reporting_v2_broken_outputs_fail_validate(tmp_path):
    """KNOWN-BAD: manifest declares reporting_features schema_version=sapote_reporting_features_v2,
    the reporting-v2 outputs all EXIST (so `missing` is empty and file_presence stays PASS) but are
    broken/empty -> reporting_v2_gate FAIL -> status FAIL. This isolates the reporting_v2->FAIL
    overall-status branch from the file_presence path."""
    pkg = _make_min_package(
        tmp_path,
        reporting_features={"schema_version": "sapote_reporting_features_v2"},
        reporting_v2_stubs=True,
    )
    result = validate_package(pkg, enrichment_check=True)
    assert result["reporting_v2_gate"] == "FAIL", result.get("reporting_v2")
    # The FAIL must come from the reporting-v2 gate, not from a missing required file.
    assert result["file_presence"] == "PASS", result.get("missing_required_suffixes")
    assert result["status"] == "FAIL", (
        "a v2-reporting manifest with broken reporting outputs must fail the package; the "
        f"reporting_v2_gate->FAIL branch was previously never asserted to fire. got: {result.get('status')!r}"
    )


def test_control_no_reporting_v2_schema_does_not_trigger_the_gate(tmp_path):
    """Control: without the v2 schema declaration the reporting-v2 gate is not applicable, so it
    cannot be what fails the package (proves the FAIL above is the schema-triggered gate)."""
    pkg = _make_min_package(tmp_path, reporting_v2_stubs=True)  # broken stubs but NO v2 schema
    result = validate_package(pkg, enrichment_check=True)
    assert result["reporting_v2_gate"] == "LEGACY_NOT_APPLICABLE", result
    assert result["status"] != "FAIL", result
