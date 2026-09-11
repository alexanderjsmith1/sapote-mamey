from __future__ import annotations

import json
from types import SimpleNamespace

import mamey.authored_verify as authored_verify
from mamey.authored_verify import (
    VERIFY_REPORT_AUTHORITY_CEILING,
    build_verify_report,
    compact_verify_summary_lines,
    grouped_verify_findings,
)


def _finding(code, section, severity="ERROR"):
    return {"severity": severity, "code": code, "section": section, "message": code.lower()}


def test_grouped_findings_preserves_instances_and_counts_categories():
    findings = [_finding("SECTION_RECONCILIATION_ROW", n) for n in range(1, 49)]
    findings += [_finding("PUBLICATION_GENE_TABLE_MISSING", 4)]
    rows = grouped_verify_findings(findings)
    assert len(rows) == 2
    section_row = next(r for r in rows if r["code"] == "SECTION_RECONCILIATION_ROW")
    assert section_row["count"] == 48
    assert section_row["sections"] == list(range(1, 49))


def test_report_distinguishes_instances_categories_and_authority():
    findings = [_finding("SECTION_RECONCILIATION_ROW", n) for n in range(1, 49)]
    findings += [_finding("COVERAGE_UNVERIFIED", 4, "WARN")]
    report = build_verify_report(
        card_name="fixture.md", profile="§1–§48 publication profile", exit_code=1,
        findings=findings, independent_roster_bound=False,
        package_core_denominator_bound=False,
    )
    assert report["error_instances"] == 48
    assert report["warning_instances"] == 1
    assert report["finding_categories"] == 2
    assert report["coverage_verified"] is False
    assert report["authority_ceiling"] == VERIFY_REPORT_AUTHORITY_CEILING
    assert len(report["findings"]) == 49


def test_compact_summary_is_deterministic():
    lines = compact_verify_summary_lines([
        _finding("ZETA", 7), _finding("ALPHA", 2), _finding("ALPHA", 1),
    ])
    assert lines == [
        "ERROR: ALPHA x2 (sections: §1,§2)",
        "ERROR: ZETA x1 (sections: §7)",
    ]


def test_verify_modeb_writes_json_without_changing_failure_exit(tmp_path, monkeypatch):
    card = tmp_path / "fixture.md"
    card.write_text("## §1 Identity\nSubstantive.\n", encoding="utf-8")
    receipt = tmp_path / "receipts" / "verify.json"
    monkeypatch.setattr(authored_verify, "_bgc_context_from_package", lambda *_a, **_k: {})
    monkeypatch.setattr(authored_verify, "lint_card", lambda *_a, **_k: [
        _finding("SECTION_RECONCILIATION_ROW", 1),
        _finding("SECTION_RECONCILIATION_ROW", 2),
    ])
    args = SimpleNamespace(
        file=str(card), package=None, bgc=None, no_strict_depth=False,
        interp=False, interp_strict=False, summary_only=True,
        report_json=str(receipt),
    )
    assert authored_verify.verify_modeb_command(args) == 1
    data = json.loads(receipt.read_text(encoding="utf-8"))
    assert data["error_instances"] == 2
    assert data["finding_categories"] == 1
    assert data["category_summary"][0]["count"] == 2


def test_verify_modeb_writes_pass_receipt_and_keeps_zero_exit(tmp_path, monkeypatch):
    card = tmp_path / "fixture.md"
    card.write_text("## §1 Identity\nSubstantive.\n", encoding="utf-8")
    receipt = tmp_path / "verify.json"
    monkeypatch.setattr(authored_verify, "_bgc_context_from_package", lambda *_a, **_k: {})
    monkeypatch.setattr(authored_verify, "lint_card", lambda *_a, **_k: [])
    args = SimpleNamespace(
        file=str(card), package=None, bgc=None, no_strict_depth=False,
        interp=False, interp_strict=False, summary_only=False,
        report_json=str(receipt),
    )
    assert authored_verify.verify_modeb_command(args) == 0
    data = json.loads(receipt.read_text(encoding="utf-8"))
    assert data["status"] == "PASS"
    assert data["error_instances"] == 0
    assert data["finding_categories"] == 0


def test_missing_file_can_still_emit_machine_receipt(tmp_path):
    receipt = tmp_path / "missing.json"
    args = SimpleNamespace(file=str(tmp_path / "absent.md"), report_json=str(receipt))
    assert authored_verify.verify_modeb_command(args) == 1
    data = json.loads(receipt.read_text(encoding="utf-8"))
    assert data["category_summary"][0]["code"] == "FILE_NOT_FOUND"
    assert data["card_name"] == "absent.md"
