"""Sol 02 regression contract for present verification context and typed predicates."""
from pathlib import Path
from types import SimpleNamespace
import json

import pytest

import mamey.authored_verify as authored_verify
import mamey.genome_explore as genome_explore
import mamey.mode_b_receipt as mode_b_receipt
import mamey.modeb_structure_gate as structure_gate


_FIXTURE_ID = "TEST-001 / NODE_1 / region001 / BGC001"


def _package(tmp_path: Path) -> Path:
    package = tmp_path / "package"
    package.mkdir()
    return package


def _verify_args(card: Path, package: Path, report: Path) -> SimpleNamespace:
    return SimpleNamespace(
        file=str(card), package=str(package), bgc="BGC001",
        no_strict_depth=False, interp=False, summary_only=True,
        report_json=str(report), force=False,
    )


def test_blastp_discovery_io_failure_becomes_context_error(tmp_path, monkeypatch):
    package = _package(tmp_path)
    real_glob = Path.glob

    def guarded_glob(path, pattern):
        if path == package and pattern == "*_manual_blastp_worklist.csv":
            raise PermissionError("generic fixture denies discovery")
        return real_glob(path, pattern)

    monkeypatch.setattr(Path, "glob", guarded_glob)
    ctx = authored_verify._bgc_context_from_package(package, "BGC001")
    assert any(
        row["code"] == "VERIFICATION_CONTEXT_UNREADABLE"
        and "BLASTp panel discovery" in row["message"]
        for row in ctx["_verification_context_findings"]
    ), _FIXTURE_ID


def test_triage_merge_failure_becomes_context_error(tmp_path, monkeypatch):
    package = _package(tmp_path)

    def fail_merge(*_args, **_kwargs):
        raise RuntimeError("generic merge failure")

    monkeypatch.setattr(mode_b_receipt, "_bgc_context_from_triage", fail_merge)
    ctx = authored_verify._bgc_context_from_package(package, "BGC001")
    assert any(
        row["code"] == "VERIFICATION_CONTEXT_MERGE_FAILED"
        for row in ctx["_verification_context_findings"]
    ), _FIXTURE_ID


@pytest.mark.parametrize("bgcs", [{"BGC001": {}}, [None]])
def test_malformed_manifest_inventory_becomes_context_error(tmp_path, bgcs):
    package = _package(tmp_path)
    (package / "manifest.json").write_text(
        json.dumps({"bgcs": bgcs}) + "\n", encoding="utf-8")
    ctx = authored_verify._bgc_context_from_package(package, "BGC001")
    assert any(
        row["code"] == "VERIFICATION_CONTEXT_MALFORMED"
        for row in ctx["_verification_context_findings"]
    ), _FIXTURE_ID


def test_conservation_background_io_failure_reaches_context_error(tmp_path, monkeypatch):
    package = _package(tmp_path)
    (package / "manifest.json").write_text(
        '{"bgcs": [], "source_scans": {}}\n', encoding="utf-8")

    def denied(_package):
        raise PermissionError("generic fixture denies background")

    monkeypatch.setattr(genome_explore, "_conservation_background_observation", denied)
    ctx = authored_verify._bgc_context_from_package(package, "BGC001")
    assert any(
        row["code"] == "VERIFICATION_CONTEXT_UNREADABLE"
        and "conservation" in row["message"]
        for row in ctx["_verification_context_findings"]
    ), _FIXTURE_ID


def test_malformed_gene_context_cds_member_becomes_context_error(tmp_path):
    package = _package(tmp_path)
    (package / "TEST-001_gene_context.jsonl").write_text(
        '{"bgc_id":"BGC001","cds":[null]}\n', encoding="utf-8")
    ctx = authored_verify._bgc_context_from_package(package, "BGC001")
    assert any(
        row["code"] == "VERIFICATION_CONTEXT_MALFORMED"
        for row in ctx["_verification_context_findings"]
    ), _FIXTURE_ID


def test_invalid_numeric_triage_value_reaches_verify_modeb_report(tmp_path):
    package = _package(tmp_path)
    (package / "TEST-001_4_triage_board.csv").write_text(
        "BGC_ID,AB_auto,AF_auto\nBGC001,not-a-score,20\n", encoding="utf-8")
    card = tmp_path / "TEST-001__NODE_1__region001__BGC001_ModeB.md"
    card.write_text(f"# {_FIXTURE_ID}\n", encoding="utf-8")
    report = tmp_path / "verify.json"

    assert authored_verify.verify_modeb_command(_verify_args(card, package, report)) == 1
    receipt = json.loads(report.read_text(encoding="utf-8"))
    assert any(
        row["code"] == "VERIFICATION_CONTEXT_NUMERIC_INVALID"
        and "AB_auto" in row["message"]
        for row in receipt["findings"]
    ), _FIXTURE_ID


@pytest.mark.parametrize(
    "ctx",
    [
        {"AB_auto": "inf"},
        {"AF_auto": -1},
        {"strain_high_priority_count": "1.5"},
        {"module_count": -2},
        {"total_domains": True},
    ],
)
def test_invalid_present_numeric_predicate_inputs_are_errors(ctx):
    findings = structure_gate._numeric_context_findings(ctx)
    assert [row["code"] for row in findings] == [
        "VERIFICATION_CONTEXT_NUMERIC_INVALID"
    ]


@pytest.mark.parametrize(
    "value", [None, "", "UNBOUND", "NOT_MEASURED", "SOURCE_UNAVAILABLE", "nan"])
def test_typed_missing_numeric_states_remain_nonerrors(value):
    assert structure_gate._numeric_context_findings({"AB_auto": value}) == []


def test_invalid_alias_does_not_suppress_independent_valid_alias():
    ctx = {"ab_score": "malformed", "AB_auto": "5",
           "module_count": "malformed", "n_modules": "2"}
    predicates = structure_gate._build_predicates(ctx)
    assert predicates["antimicrobial_candidate"] is True
    assert predicates["has_measured_assembly_line"] is True
    assert len(structure_gate._numeric_context_findings(ctx)) == 2


def test_malformed_large_signal_does_not_suppress_valid_length_signal():
    assert structure_gate._is_large_bgc(
        {"total_domains": "malformed", "length_kb": "31"}) is True


def test_absent_optional_sources_and_numeric_fields_remain_nonerrors(tmp_path):
    ctx = authored_verify._bgc_context_from_package(_package(tmp_path), "BGC001")
    assert "_verification_context_findings" not in ctx
    assert structure_gate._numeric_context_findings(ctx) == []
