"""Exact-head controls for the judgment-store and receipt-consumer contract.

The synthetic locus is
FIXTURE-01 / NODE_1_length_12000_cov_20.000000 / region001 / BGC001.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from mamey import judgment_store
from mamey import mode_b_receipt as receipt
from tests._modeb_card_fixtures import valid_modeb_card_stub


STRAIN = "FIXTURE-01"
NODE = "NODE_1_length_12000_cov_20.000000"
REGION = "region001"
BGC = "BGC001"
IDENTITY = f"{STRAIN} / {NODE} / {REGION} / {BGC}"


def _package(root: Path, *, with_orphan_card: bool = False) -> Path:
    package = root / "package"
    package.mkdir(parents=True)
    (package / "manifest.json").write_text(
        json.dumps({
            "strain_id": STRAIN,
            "mode": "gold",
            "bgcs": [{
                "strain": STRAIN,
                "full_node_or_contig": NODE,
                "region": REGION,
                "bgc_alias": BGC,
                "identity_display": IDENTITY,
            }],
        }),
        encoding="utf-8",
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
    if with_orphan_card:
        judgment = package / "judgment"
        judgment.mkdir()
        (judgment / f"{STRAIN}_{BGC}_mode_b.md").write_text(
            valid_modeb_card_stub(BGC, node=NODE, strain_id=STRAIN),
            encoding="utf-8",
        )
    return package


def _receipt(root: Path) -> Path:
    path = root / "mode_b_receipt.json"
    path.write_text(
        json.dumps({
            "schema_version": receipt.RECEIPT_SCHEMA_VERSION,
            "strain_id": STRAIN,
            "cards": [{
                "bgc_id": BGC,
                "mode_b_md": valid_modeb_card_stub(
                    BGC, node=NODE, strain_id=STRAIN
                ),
            }],
        }),
        encoding="utf-8",
    )
    return path


def _external_card(root: Path) -> Path:
    path = root / f"{STRAIN}_{BGC}_mode_b.md"
    path.write_text(
        valid_modeb_card_stub(BGC, node=NODE, strain_id=STRAIN),
        encoding="utf-8",
    )
    return path


def _inject_snapshot_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    original = judgment_store._atomic_write_text

    def fail_last_good(path: Path, text: str) -> None:
        if path.name.endswith(".last-good"):
            raise PermissionError("synthetic last-good refusal")
        original(path, text)

    monkeypatch.setattr(judgment_store, "_atomic_write_text", fail_last_good)


def _expected_warning() -> list[dict[str, str]]:
    return [{
        "identity": IDENTITY,
        "stage": "write_last_good_snapshot",
        "error_type": "PermissionError",
        "message": "synthetic last-good refusal",
    }]


def _mark_corrupt_recovery(package: Path) -> None:
    register = judgment_store._register_path(package)
    payload = json.loads(register.read_text(encoding="utf-8"))
    payload["judgment_status"] = "CORRUPT_RECOVERY_INCOMPLETE"
    register.write_text(json.dumps(payload), encoding="utf-8")


def test_corrupt_status_family_contract_is_centralized_and_narrow() -> None:
    assert judgment_store.is_corrupt_judgment_status("CORRUPT") is True
    assert judgment_store.is_corrupt_judgment_status(
        "CORRUPT_RECOVERY_INCOMPLETE"
    ) is True
    assert judgment_store.judgment_status_blocks_ingest("NOT_INITIALISED") is True
    assert judgment_store.judgment_status_blocks_ingest("PENDING") is False
    assert judgment_store.judgment_status_blocks_ingest("COMPLETE") is False
    assert judgment_store.judgment_status_blocks_ingest("CORRUPTION_FREE") is False


def test_auto_detect_preserves_nonblocking_persistence_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = _package(tmp_path, with_orphan_card=True)
    _inject_snapshot_failure(monkeypatch)

    summary = receipt.auto_detect_ingest(package)

    assert summary["recorded"] == [BGC]
    assert summary["persistence_warnings"] == _expected_warning()


def test_batch_receipt_preserves_nonblocking_persistence_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = _package(tmp_path)
    receipt_path = _receipt(tmp_path)
    _inject_snapshot_failure(monkeypatch)

    summary = receipt.ingest_receipt(package, receipt_path)

    assert summary["recorded"] == [BGC]
    assert summary["persistence_warnings"] == _expected_warning()


def test_single_card_preserves_nonblocking_persistence_warning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    package = _package(tmp_path)
    card = _external_card(tmp_path)
    _inject_snapshot_failure(monkeypatch)

    summary = receipt.ingest_one_card(package, card)

    assert summary["status"] == "RECORDED"
    assert summary["persistence_warnings"] == _expected_warning()


def test_auto_cli_emits_one_typed_nonblocking_persistence_advisory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    package = _package(tmp_path, with_orphan_card=True)
    _inject_snapshot_failure(monkeypatch)
    args = argparse.Namespace(
        package=str(package), auto_detect=True, receipt=None, card=None,
        force_structure=False, master=None,
    )

    assert receipt.ingest_receipts_command(args) == 0
    captured = capsys.readouterr()
    output = captured.out + captured.err
    assert output.count("PERSISTENCE_ADVISORY") == 1
    assert IDENTITY in output
    assert "write_last_good_snapshot" in output


def test_successful_receipt_writes_have_no_persistence_warning(tmp_path: Path) -> None:
    batch_root = tmp_path / "batch"
    batch_package = _package(batch_root)
    assert receipt.ingest_receipt(batch_package, _receipt(batch_root)).get(
        "persistence_warnings", []
    ) == []

    auto_package = _package(tmp_path / "auto", with_orphan_card=True)
    assert receipt.auto_detect_ingest(auto_package).get("persistence_warnings", []) == []

    single_root = tmp_path / "single"
    single_package = _package(single_root)
    assert receipt.ingest_one_card(
        single_package, _external_card(single_root)
    ).get("persistence_warnings", []) == []


def test_corrupt_recovery_refuses_batch_before_card_write(tmp_path: Path) -> None:
    package = _package(tmp_path)
    receipt_path = _receipt(tmp_path)
    _mark_corrupt_recovery(package)

    with pytest.raises(ValueError, match="CORRUPT_RECOVERY_INCOMPLETE"):
        receipt.ingest_receipt(package, receipt_path)

    assert not (package / "judgment" / f"{STRAIN}_{BGC}_mode_b.md").exists()


def test_corrupt_recovery_refuses_auto_detect_and_cli_exits_nonzero(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    package = _package(tmp_path, with_orphan_card=True)
    _mark_corrupt_recovery(package)
    before = (package / "judgment" / f"{STRAIN}_{BGC}_mode_b.md").read_bytes()

    summary = receipt.auto_detect_ingest(package)
    assert summary["recorded"] == []
    assert summary["judgment_status"] == "CORRUPT_RECOVERY_INCOMPLETE"

    args = argparse.Namespace(
        package=str(package), auto_detect=True, receipt=None, card=None,
        force_structure=False, master=None,
    )
    assert receipt.ingest_receipts_command(args) != 0
    assert "CORRUPT_RECOVERY_INCOMPLETE" in capsys.readouterr().out
    assert (package / "judgment" / f"{STRAIN}_{BGC}_mode_b.md").read_bytes() == before


def test_corrupt_recovery_refuses_single_card_before_mutation(tmp_path: Path) -> None:
    package = _package(tmp_path)
    card = _external_card(tmp_path)
    _mark_corrupt_recovery(package)

    summary = receipt.ingest_one_card(package, card)

    assert summary["status"] == "REGISTER_NOT_INGESTIBLE"
    assert summary["judgment_status"] == "CORRUPT_RECOVERY_INCOMPLETE"
    assert summary["structure_findings"][0]["code"] == "REGISTER_NOT_INGESTIBLE"
    assert not (package / "judgment" / f"{STRAIN}_{BGC}_mode_b.md").exists()
