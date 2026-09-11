"""Sol01 round-3 regressions for cross-patch receipt contracts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from mamey import judgment_store
from mamey import mode_b_receipt as receipt
from tests._modeb_card_fixtures import valid_modeb_card_stub


STRAIN = "FIXTURE-03"
BGC = "BGC001"
NODE = "NODE_1_length_12000_cov_20.000000"
REGION = "region001"
IDENTITY = f"{STRAIN} / {NODE} / {REGION} / {BGC}"


def _package(tmp_path: Path, *, with_card: bool = True) -> Path:
    package = tmp_path / "package"
    package.mkdir(parents=True)
    (package / "manifest.json").write_text(
        json.dumps({"strain_id": STRAIN}), encoding="utf-8"
    )
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
    if with_card:
        judgment = package / "judgment"
        judgment.mkdir()
        (judgment / f"{STRAIN}_{BGC}_mode_b.md").write_text(
            _card(), encoding="utf-8"
        )
    return package


def _card() -> str:
    return valid_modeb_card_stub(BGC, node=NODE, strain_id=STRAIN)


def _card_path(package: Path) -> Path:
    return package / "judgment" / f"{STRAIN}_{BGC}_mode_b.md"


def _receipt_file(tmp_path: Path) -> Path:
    path = tmp_path / "mode_b_receipt.json"
    path.write_text(json.dumps({
        "schema_version": receipt.RECEIPT_SCHEMA_VERSION,
        "strain_id": STRAIN,
        "cards": [{"bgc_id": BGC, "mode_b_md": _card()}],
    }), encoding="utf-8")
    return path


def _warning_record(monkeypatch: pytest.MonkeyPatch) -> None:
    original = judgment_store.record_mode_b

    def record_with_warning(*args, **kwargs):
        result = original(*args, **kwargs)
        payload = dict(result) if isinstance(result, dict) else {}
        payload["persistence_warnings"] = [{
            "stage": "write_last_good_snapshot",
            "error_type": "PermissionError",
            "message": "synthetic last-good refusal",
        }]
        return payload

    monkeypatch.setattr(judgment_store, "record_mode_b", record_with_warning)


def _expected_warning() -> list[dict[str, str]]:
    return [{
        "identity": IDENTITY,
        "stage": "write_last_good_snapshot",
        "error_type": "PermissionError",
        "message": "synthetic last-good refusal",
    }]


def _args(package: Path, **overrides) -> argparse.Namespace:
    values = {
        "package": str(package), "auto_detect": False, "receipt": None,
        "card": None, "force_structure": False, "master": None,
    }
    values.update(overrides)
    return argparse.Namespace(**values)


def test_persistence_warning_survives_auto_detect_and_cli_advises(
    tmp_path, monkeypatch, capsys
):
    package = _package(tmp_path / "direct")
    _warning_record(monkeypatch)
    summary = receipt.auto_detect_ingest(package)
    assert summary["persistence_warnings"] == _expected_warning()

    package = _package(tmp_path / "cli")
    assert receipt.ingest_receipts_command(
        _args(package, auto_detect=True)
    ) == 0
    output = capsys.readouterr()
    assert "WARNING: PERSISTENCE_ADVISORY (1)" in output.out + output.err
    assert IDENTITY in output.out + output.err


def test_persistence_warning_survives_batch_and_cli_advises(
    tmp_path, monkeypatch, capsys
):
    package = _package(tmp_path / "direct", with_card=False)
    receipt_path = _receipt_file(tmp_path / "direct")
    _warning_record(monkeypatch)
    summary = receipt.ingest_receipt(package, receipt_path)
    assert summary["persistence_warnings"] == _expected_warning()

    package = _package(tmp_path / "cli", with_card=False)
    receipt_path = _receipt_file(tmp_path / "cli")
    assert receipt.ingest_receipts_command(
        _args(package, receipt=str(receipt_path))
    ) == 0
    output = capsys.readouterr()
    assert "WARNING: PERSISTENCE_ADVISORY (1)" in output.out + output.err
    assert IDENTITY in output.out + output.err


def test_persistence_warning_survives_single_card_and_cli_advises(
    tmp_path, monkeypatch, capsys
):
    package = _package(tmp_path / "direct")
    _warning_record(monkeypatch)
    summary = receipt.ingest_one_card(package, _card_path(package))
    assert summary["status"] == "RECORDED"
    assert summary["persistence_warnings"] == _expected_warning()

    package = _package(tmp_path / "cli")
    assert receipt.ingest_receipts_command(
        _args(package, card=str(_card_path(package)))
    ) == 0
    output = capsys.readouterr()
    assert "WARNING: PERSISTENCE_ADVISORY (1)" in output.out + output.err
    assert IDENTITY in output.out + output.err


def _corrupt(package: Path) -> None:
    register = judgment_store._register_path(package)
    payload = json.loads(register.read_text(encoding="utf-8"))
    payload["judgment_status"] = "CORRUPT_RECOVERY_INCOMPLETE"
    register.write_text(json.dumps(payload), encoding="utf-8")


def test_corrupt_recovery_refuses_single_card_before_mutation(tmp_path):
    package = _package(tmp_path)
    card = _card_path(package)
    before = card.read_bytes()
    _corrupt(package)

    summary = receipt.ingest_one_card(package, card)

    assert summary["status"] == "REGISTER_NOT_INGESTIBLE"
    assert summary["judgment_status"] == "CORRUPT_RECOVERY_INCOMPLETE"
    assert card.read_bytes() == before


def test_corrupt_recovery_auto_cli_is_nonzero_and_typed(tmp_path, capsys):
    package = _package(tmp_path)
    _corrupt(package)

    assert receipt.ingest_receipts_command(
        _args(package, auto_detect=True)
    ) == 1
    output = capsys.readouterr()
    assert "CORRUPT_RECOVERY_INCOMPLETE" in output.out + output.err


def test_unknown_pass_prefix_is_not_terminal_success():
    from mamey import cli

    assert cli._terminal_mamey_status("PASS_THROUGH_CORRUPT", []) == (
        "PASS_THROUGH_CORRUPT"
    )
