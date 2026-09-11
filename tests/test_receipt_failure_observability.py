"""Regression coverage for Mode B recovery/context and doctor observability."""

from __future__ import annotations

import argparse
import builtins
import json
from pathlib import Path
import zipfile

from mamey import cli
from mamey import mode_b_receipt as receipt
from mamey import judgment_store
from tests._modeb_card_fixtures import valid_modeb_card_stub


STRAIN = "FIXTURE-01"
BGC = "BGC001"
NODE = "NODE_1_length_12000_cov_20.000000"
REGION = "region001"
IDENTITY = f"{STRAIN} / {NODE} / {REGION} / {BGC}"


def _package(tmp_path: Path) -> Path:
    package = tmp_path / "package"
    package.mkdir(parents=True)
    (package / "manifest.json").write_text(json.dumps({"strain_id": STRAIN}), encoding="utf-8")
    judgment_store.init_register(package, strain_id=STRAIN, bgc_ids=[BGC])
    (package / f"{STRAIN}_2_inventory.csv").write_text(
        "BGC_ID,Contig,Node_ID,antiSMASH_Region\n"
        f"{BGC},{NODE},{NODE},{REGION}\n",
        encoding="utf-8",
    )
    (package / f"{STRAIN}_4_triage_board.csv").write_text(
        "BGC_ID,Products,Corrected_rank,Boundary,Lead_tier_auto\n"
        f"{BGC},NRPS,1,Interior,Inventory\n",
        encoding="utf-8",
    )
    judgment = package / "judgment"
    judgment.mkdir()
    (judgment / f"{STRAIN}_{BGC}_mode_b.md").write_text(
        valid_modeb_card_stub(BGC, node=NODE, strain_id=STRAIN),
        encoding="utf-8",
    )
    return package


def _auto_args(package: Path) -> argparse.Namespace:
    return argparse.Namespace(
        package=str(package), auto_detect=True, receipt=None, card=None,
        force_structure=False, master=None,
    )


def test_auto_detect_unreadable_card_is_structured_and_cli_nonzero(
    tmp_path, monkeypatch, capsys
):
    package = _package(tmp_path)
    original = Path.read_text

    def fail_card(self, *args, **kwargs):
        if self.name == f"{STRAIN}_{BGC}_mode_b.md":
            raise OSError("fixture read refusal")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", fail_card)
    seen = {}
    original_auto = receipt.auto_detect_ingest

    def spy(*args, **kwargs):
        result = original_auto(*args, **kwargs)
        seen.update(result)
        return result

    monkeypatch.setattr(receipt, "auto_detect_ingest", spy)
    assert receipt.ingest_receipts_command(_auto_args(package)) == 1
    assert seen["skipped_unreadable"] == [{
        "identity": IDENTITY, "error_type": "OSError",
    }]
    assert "FAILED (unreadable): 1 card(s)" in capsys.readouterr().err


def test_auto_detect_record_failure_is_structured_and_cli_nonzero(
    tmp_path, monkeypatch, capsys
):
    package = _package(tmp_path)

    def fail_record(*args, **kwargs):
        raise OSError("fixture persistence refusal")

    monkeypatch.setattr(judgment_store, "record_mode_b", fail_record)
    seen = {}
    original_auto = receipt.auto_detect_ingest

    def spy(*args, **kwargs):
        result = original_auto(*args, **kwargs)
        seen.update(result)
        return result

    monkeypatch.setattr(receipt, "auto_detect_ingest", spy)
    assert receipt.ingest_receipts_command(_auto_args(package)) == 1
    assert seen["record_failures"] == [{
        "identity": IDENTITY, "error_type": "OSError",
    }]
    assert "FAILED (persistence): 1 card(s)" in capsys.readouterr().err


def test_auto_detect_success_remains_zero_and_has_no_failure_records(tmp_path):
    package = _package(tmp_path)
    summary = receipt.auto_detect_ingest(package)
    assert summary["recorded"] == [BGC]
    assert summary["skipped_unreadable"] == []
    assert summary["record_failures"] == []


def test_present_malformed_triage_is_context_error_but_absence_is_not(tmp_path):
    package = _package(tmp_path)
    card = valid_modeb_card_stub(BGC, node=NODE, strain_id=STRAIN)
    (package / f"{STRAIN}_4_triage_board.csv").write_text(
        "wrong,header\nvalue,row\n", encoding="utf-8"
    )
    malformed = receipt.lint_card_in_package(package, BGC, card_md=card)
    assert any(row.get("code") == "VERIFICATION_CONTEXT_MALFORMED" for row in malformed)

    (package / f"{STRAIN}_4_triage_board.csv").unlink()
    absent = receipt.lint_card_in_package(package, BGC, card_md=card)
    assert not any(str(row.get("code", "")).startswith("VERIFICATION_CONTEXT_") for row in absent)


def test_present_malformed_satellite_is_context_error_but_absence_is_not(tmp_path):
    package = _package(tmp_path)
    card = valid_modeb_card_stub(BGC, node=NODE, strain_id=STRAIN)
    satellite = package / f"{STRAIN}_3_antismash_modules.csv"
    satellite.write_text(
        "bgc_id,feature_type\n"
        f"{BGC},aSModule,unexpected\n",
        encoding="utf-8",
    )
    malformed = receipt.lint_card_in_package(package, BGC, card_md=card)
    assert any(row.get("code") == "VERIFICATION_CONTEXT_MALFORMED" for row in malformed)

    satellite.unlink()
    absent = receipt.lint_card_in_package(package, BGC, card_md=card)
    assert not any(row.get("code") == "VERIFICATION_CONTEXT_MALFORMED" for row in absent)


def test_present_malformed_gene_context_is_error_but_absence_is_not(tmp_path):
    package = _package(tmp_path)
    card = valid_modeb_card_stub(BGC, node=NODE, strain_id=STRAIN)
    gene_context = package / f"{STRAIN}_gene_context.jsonl"
    gene_context.write_text("{not-json}\n", encoding="utf-8")
    malformed = receipt.lint_card_in_package(package, BGC, card_md=card)
    assert any(row.get("code") == "VERIFICATION_CONTEXT_MALFORMED" for row in malformed)

    gene_context.unlink()
    absent = receipt.lint_card_in_package(package, BGC, card_md=card)
    assert not any(row.get("code") == "VERIFICATION_CONTEXT_MALFORMED" for row in absent)


def test_batch_receipt_refuses_malformed_present_context_but_accepts_absence(tmp_path):
    malformed_pkg = _package(tmp_path / "malformed")
    malformed_card = valid_modeb_card_stub(BGC, node=NODE, strain_id=STRAIN)
    (malformed_pkg / f"{STRAIN}_4_triage_board.csv").write_text(
        "wrong,header\nvalue,row\n", encoding="utf-8"
    )
    malformed_receipt = tmp_path / "malformed_receipt.json"
    malformed_receipt.write_text(json.dumps({
        "schema_version": receipt.RECEIPT_SCHEMA_VERSION,
        "strain_id": STRAIN,
        "cards": [{"bgc_id": BGC, "mode_b_md": malformed_card}],
    }), encoding="utf-8")
    refused = receipt.ingest_receipt(malformed_pkg, malformed_receipt)
    assert refused["recorded"] == []
    assert refused["skipped_structure_invalid"] == [(BGC, 1)]

    absent_pkg = _package(tmp_path / "absent")
    (absent_pkg / f"{STRAIN}_4_triage_board.csv").unlink()
    absent_receipt = tmp_path / "absent_receipt.json"
    absent_receipt.write_text(json.dumps({
        "schema_version": receipt.RECEIPT_SCHEMA_VERSION,
        "strain_id": STRAIN,
        "cards": [{"bgc_id": BGC, "mode_b_md": malformed_card}],
    }), encoding="utf-8")
    accepted = receipt.ingest_receipt(absent_pkg, absent_receipt)
    assert accepted["recorded"] == [BGC]


def test_lint_wrapper_gate_import_failure_is_explicit(tmp_path, monkeypatch):
    package = _package(tmp_path)
    card = valid_modeb_card_stub(BGC, node=NODE, strain_id=STRAIN)
    original_import = builtins.__import__

    def fail_gate(name, *args, **kwargs):
        if name.endswith("modeb_structure_gate"):
            raise ImportError("fixture gate unavailable")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fail_gate)
    findings = receipt.lint_card_in_package(package, BGC, card_md=card)
    assert any(row.get("code") == "GATE_UNAVAILABLE" for row in findings)


def test_doctor_reports_bad_zip_and_denominator_probe_failure(
    tmp_path, monkeypatch, capsys
):
    (tmp_path / "broken.zip").write_bytes(b"not a zip")
    monkeypatch.chdir(tmp_path)
    from mamey import exclusions, external_data
    monkeypatch.setattr(external_data, "status", lambda: {})
    monkeypatch.setattr(exclusions, "governed_denominator",
                        lambda: (_ for _ in ()).throw(ValueError("fixture denominator failure")))
    assert cli.doctor_command(argparse.Namespace()) == 0
    output = capsys.readouterr().out
    assert "antiSMASH ZIP unreadable: broken.zip (BadZipFile)" in output
    assert "governed denominator status unavailable (ValueError)" in output


def test_doctor_valid_zip_remains_detected(tmp_path, monkeypatch, capsys):
    archive = tmp_path / "fixture.zip"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr("fixture.region001.gbk", "LOCUS fixture")
    monkeypatch.chdir(tmp_path)
    assert cli.doctor_command(argparse.Namespace()) == 0
    output = capsys.readouterr().out
    assert "antiSMASH ZIP(s) detected in current dir: fixture.zip" in output
    assert "antiSMASH ZIP unreadable" not in output
