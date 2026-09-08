"""v9.7.338 — verdict-changing gate fixes: prove each gate FIRES on the known-bad input.

Same discipline as the v9.7.335 known-bad-input suite: every fix here is a check that used to
report success without having checked. A good-input-only suite cannot see such a bug, so each
test feeds the exact artifact that used to slip through and asserts the gate now refuses it,
paired with a good-input control so a future refactor cannot make the test pass by breaking the
gate in the other direction.

Gates locked here:
  GATE-11 validate.validate_package        — RG-GMCI "no pairs" PASSed even when the clusterblast
                                             reference geometry FAILED TO PARSE.
  WB-02   workbook_schema_check.validate    — a master with A2<->B1 orphans / row-count mismatch
                                             (consistency_errors) returned status PASS.

(GATE-12 — gold-completeness stub-card floor — is locked in
 tests/test_v9_7_335_tier1_gates_known_bad_input.py alongside the .335 gold-completeness fix.)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mamey.validate import validate_package


# ======================================================================================
# GATE-11 — RG-GMCI gate must fail when the "no pairs" verdict rests on unparseable refs.
# ======================================================================================

_LOCKED = ["BGC001", "BGC002"]


def _make_min_package(tmp_path: Path, *, rggmci: dict) -> Path:
    """Smallest package validate_package() accepts (mode=gold), with a caller-supplied
    RG-GMCI payload so we can drive the rggmci gate directly."""
    pkg = tmp_path / "AS-TEST"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(
        json.dumps({"strain_id": "AS-TEST", "mode": "gold",
                    "bgcs": [{"bgc_id": b} for b in _LOCKED]}),
        encoding="utf-8")
    (pkg / "AS-TEST_2_inventory.csv").write_text(
        "bgc_id,Depth_floor\nBGC001,full_mode_b\nBGC002,abbreviated_ledger\n",
        encoding="utf-8")
    (pkg / "AS-TEST_4A_RGGMCI_full.json").write_text(json.dumps(rggmci), encoding="utf-8")
    for stub in ("AS-TEST_1_intake.json", "AS-TEST_3_scan_states.json",
                 "commit_receipt.json", "Project_Memory_Snapshot.json",
                 "manifest_short.json"):
        (pkg / stub).write_text("{}", encoding="utf-8")
    for stub in ("AS-TEST_4A_RGGMCI_ranked_pairs.csv", "AS-TEST_4A_RGGMCI_evidence.csv",
                 "AS-TEST_4_triage_board.csv", "AS-TEST_7_cell_provenance.csv"):
        (pkg / stub).write_text("col\n", encoding="utf-8")
    (pkg / "AS-TEST_5_workbook.xlsx").write_bytes(b"stub")
    (pkg / "issue_log.md").write_text("# issues\n", encoding="utf-8")
    (pkg / "OPEN_ME_FIRST.html").write_text("<html></html>", encoding="utf-8")
    (pkg / "checksums_sha256.txt").write_text("", encoding="utf-8")
    return pkg


def test_no_pairs_with_parse_errors_fails_the_gate(tmp_path):
    """KNOWN-BAD: status=NULL_NO_RGGMCI_PAIRS while clusterblast reference file(s) were present
    but FAILED TO PARSE (reference_parse_error_count>0). The gate previously read the top-level
    status string alone and PASSed — greenlighting a no-pairs verdict built on unparseable
    input. GATE-11 fails it closed."""
    pkg = _make_min_package(tmp_path, rggmci={
        "status": "NULL_NO_RGGMCI_PAIRS",
        "pairs_total": 0,
        "reference_record_count": 0,
        "reference_map_status": "NULL_NO_CLUSTERBLAST_REFERENCES_PARSED",
        "reference_parse_error_count": 2,
    })
    result = validate_package(pkg, enrichment_check=True)
    assert result["rggmci_gate"] == "FAIL", result.get("rggmci_note")
    assert result["status"] == "FAIL", result


def test_no_pairs_with_partial_parse_errors_fails_the_gate(tmp_path):
    """KNOWN-BAD: some references parsed (reference_map_status alias PASS/PARSED) but others
    threw (reference_parse_error_count>0). Any parse error makes the empty set unreliable."""
    pkg = _make_min_package(tmp_path, rggmci={
        "status": "NULL_NO_RGGMCI_PAIRS",
        "pairs_total": 0,
        "reference_record_count": 3,
        "reference_map_status": "PASS",
        "reference_parse_error_count": 1,
    })
    result = validate_package(pkg, enrichment_check=True)
    assert result["rggmci_gate"] == "FAIL", result.get("rggmci_note")
    assert result["status"] == "FAIL", result


def test_control_reference_free_package_still_passes(tmp_path):
    """Control (the real smoke-fixture case): a package produced WITHOUT any knownclusterblast
    output has reference_map_status=NULL_NO_CLUSTERBLAST_REFERENCES_PARSED but
    reference_parse_error_count=0 — no files were present to parse, so the empty set is genuine.

    This is why GATE-11 keys on parse_error_count, not on reference_map_status: firing on the
    NULL status alone (the source addendum's OR-form) failed every reference-free antiSMASH
    package. That empty set must still PASS."""
    pkg = _make_min_package(tmp_path, rggmci={
        "status": "NULL_NO_RGGMCI_PAIRS",
        "pairs_total": 0,
        "reference_record_count": 0,
        "reference_map_status": "NULL_NO_CLUSTERBLAST_REFERENCES_PARSED",
        "reference_parse_error_count": 0,
    })
    result = validate_package(pkg, enrichment_check=True)
    assert result["rggmci_gate"] == "PASS", result.get("rggmci_note")


def test_control_genuine_empty_set_with_parsed_refs_still_passes(tmp_path):
    """Control: references parsed cleanly (zero parse errors) but produced no linked pairs —
    a genuine empty set that must still PASS."""
    pkg = _make_min_package(tmp_path, rggmci={
        "status": "NULL_NO_RGGMCI_PAIRS",
        "pairs_total": 0,
        "reference_record_count": 5,
        "reference_map_status": "PASS",
        "reference_parse_error_count": 0,
    })
    result = validate_package(pkg, enrichment_check=True)
    assert result["rggmci_gate"] == "PASS", result.get("rggmci_note")


def test_control_absent_reference_fields_still_pass_legacy_payloads(tmp_path):
    """Control: older RG-GMCI payloads have no reference_map_status / parse-error-count
    fields at all. Their absence must be treated as a genuine empty set (back-compat),
    not as a parse failure."""
    pkg = _make_min_package(tmp_path, rggmci={
        "status": "NULL_NO_RGGMCI_PAIRS", "pairs_total": 0, "reference_record_count": 0,
    })
    result = validate_package(pkg, enrichment_check=True)
    assert result["rggmci_gate"] == "PASS", result.get("rggmci_note")


# ======================================================================================
# WB-02 — master workbook validate() must FAIL on consistency_errors (A2<->B1 orphans /
# per-strain row-count mismatch), not only on column/sheet errors.
# ======================================================================================

openpyxl = pytest.importorskip("openpyxl")
from mamey.workbook_schema_check import validate, REQUIRED_SHEETS  # noqa: E402


def _header_for(spec) -> list[str]:
    """Correct header row for a required sheet, so the column check produces no errors."""
    if "columns" in spec:
        return list(spec["columns"])
    if "prefix" in spec:
        return list(spec["prefix"])
    return ["col1"]  # min_cols=1 fixed sheets (e.g. A1_Dashboard)


def _build_master(path, *, a2_strains, b1_strains) -> str:
    """Build a structurally complete master (every canonical sheet, correct headers).
    A2_Strain_Registry is the only per-strain sheet carrying data (so no row-count-mismatch
    noise); B1_BGC_Master carries one row per b1 strain. Only the A2<->B1 strain sets vary."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for sheet, spec in REQUIRED_SHEETS.items():
        ws = wb.create_sheet(sheet)
        ws.append(_header_for(spec))
        if sheet == "A2_Strain_Registry":
            for s in a2_strains:
                ws.append([s] + [""] * (len(_header_for(spec)) - 1))
        elif sheet == "B1_BGC_Master":
            for s in b1_strains:
                ws.append([s] + [""] * (len(_header_for(spec)) - 1))
    wb.save(path)
    return path


def test_a2_b1_orphan_makes_validate_fail(tmp_path):
    """KNOWN-BAD: a strain present in A2_Strain_Registry but dropped from B1_BGC_Master
    appends to consistency_errors. It previously left status=PASS (exit 0); WB-02 fails it."""
    p = _build_master(str(tmp_path / "orphan.xlsx"),
                      a2_strains=["AS-001", "AS-002"], b1_strains=["AS-001"])
    r = validate(p)
    assert r["consistency_errors"], r
    assert r["status"] == "FAIL", (
        "a master with an A2->B1 orphan strain must FAIL; it previously returned "
        f"{r['status']!r} because only column/sheet errors flipped status"
    )


def test_control_consistent_master_passes(tmp_path):
    """Control: the same structure with matching A2/B1 strain sets has no consistency
    errors and must still PASS — the fix must not fail a well-formed master."""
    p = _build_master(str(tmp_path / "ok.xlsx"),
                      a2_strains=["AS-001"], b1_strains=["AS-001"])
    r = validate(p)
    assert r["column_errors"] == [], r["column_errors"]
    assert r["consistency_errors"] == [], r["consistency_errors"]
    assert r["status"] == "PASS", r


# ======================================================================================
# SEAL-02 — _phase_package_seal must honor the FINAL post-seal re-validation, rewrite
# gate_validation.json from it, and block on a non-terminal-success status.
# ======================================================================================

def _seed_seal_pkg(tmp_path) -> Path:
    pkg = tmp_path / "AS-TEST"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(
        json.dumps({"strain_id": "AS-TEST", "mode": "gold", "bgcs": []}), encoding="utf-8")
    # stale on-disk gate written from the mid-build result, so we can prove it is refreshed.
    (pkg / "gate_validation.json").write_text(
        json.dumps({"status": "MAMEY_COMPLETE", "note": "mid-build"}), encoding="utf-8")
    return pkg


def test_seal_honors_final_status_and_blocks_on_regression(tmp_path, monkeypatch):
    """KNOWN-BAD: the mid-build validate_result says MAMEY_COMPLETE, but the FINAL post-seal
    re-validation regresses to FAIL (a gate that only fires after gene tables / triage patch /
    report exist). Previously the seal returned and receipted the stale mid-build status and
    never refreshed gate_validation.json, so the regression could not fail the seal. SEAL-02
    honors the final status, rewrites the on-disk gate, and appends a [BLOCKING] issue."""
    from mamey import cli
    pkg = _seed_seal_pkg(tmp_path)

    def _fake_post_seal(package_dir, **kw):
        return {"status": "FAIL", "missing_required_suffixes": [],
                "rggmci_gate": "FAIL", "note": "post-seal regression"}
    monkeypatch.setattr(cli, "validate_package", _fake_post_seal)

    issues: list = []
    mid_build = {"status": "MAMEY_COMPLETE"}
    zip_path, status = cli._phase_package_seal(
        pkg, tmp_path, "AS-TEST", "standard", 0, mid_build, issues)

    assert status == "FAIL", "seal must honor the final post-seal status, not the mid-build one"
    on_disk = json.loads((pkg / "gate_validation.json").read_text())
    assert on_disk["status"] == "FAIL", "gate_validation.json must be refreshed from the final result"
    assert on_disk.get("note") == "post-seal regression", on_disk
    assert any("[BLOCKING]" in i for i in issues), issues


def test_seal_control_terminal_success_does_not_block(tmp_path, monkeypatch):
    """Control: when the final post-seal status is a terminal success, the seal returns it
    unchanged and appends no [BLOCKING] issue — the fix must not block healthy packages."""
    from mamey import cli
    pkg = _seed_seal_pkg(tmp_path)

    def _fake_post_seal(package_dir, **kw):
        return {"status": "MAMEY_COMPLETE", "missing_required_suffixes": []}
    monkeypatch.setattr(cli, "validate_package", _fake_post_seal)

    issues: list = []
    mid_build = {"status": "PASS"}
    zip_path, status = cli._phase_package_seal(
        pkg, tmp_path, "AS-TEST", "standard", 0, mid_build, issues)

    assert status == "MAMEY_COMPLETE"
    assert not any("[BLOCKING]" in i for i in issues), issues
    assert json.loads((pkg / "gate_validation.json").read_text())["status"] == "MAMEY_COMPLETE"

# NOTE: SEAL-03 (verify_checksums reciprocal coverage) was investigated for this batch but
# deliberately NOT landed — a correct reciprocal scan must exempt the full post-seal artifact
# surface (root-level figures, *_fig_*_data.csv companions, PRINT_FIGURE_PACK.md /
# FIGURES_SUPPLEMENTARY.md / figure_manifest_print.csv, repro_fingerprint.json, *_cnbu.json,
# smoke_figures/*), not just the .png/.svg set is_checksum_excluded currently covers. That is a
# separate design decision; see PATCH_CARD_v9_7_338.md (SEAL-03 STOPPED). No SEAL-03 tests here.
