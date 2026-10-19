"""Generic receipt bytes must bind the quarantine rows consumed."""
import hashlib
import json

from mamey import blastp_gate as gate
from tests.source_change_helpers import replace_after_first_binary_read


def _toy_package(tmp_path, monkeypatch):
    quarantine = tmp_path / "blastp_quarantine" / "toy.csv"
    quarantine.parent.mkdir()
    original = (
        "source_file,source_file_sha256,resolved_bgc,reason\n"
        + "toy-input.csv," + "a" * 64 + ",current-old,TOY_HOLD\n"
    ).encode()
    quarantine.write_bytes(original)
    receipt = {
        "schema": "mamey_blastp_locus_rekey_ingest_v2", "channel": "nr",
        "locus_rekey": {"enabled": True, "admitted_current_bgcs": {}},
        "sources": [{"bgc": "item001", "file": "toy-input.csv", "sha256": "a" * 64,
                     "destination_bgcs": []}],
        "quarantined_by_reason": {"TOY_HOLD": 1}, "admitted_total": 0,
        "quarantined_total": 1, "quarantine_file": "toy.csv",
        "quarantine_sha256": hashlib.sha256(original).hexdigest(),
    }
    receipts = tmp_path / "blastp_ingest_receipts"
    receipts.mkdir()
    (receipts / "toy.json").write_text(json.dumps(receipt), encoding="utf-8")
    monkeypatch.setattr(gate, "read_ingest_ledger",
                        lambda package: {"nr": {"item001": {"receipt": "toy.json"}}})
    return quarantine, original


def test_quarantine_rows_share_the_receipt_verified_buffer(tmp_path, monkeypatch):
    quarantine, original = _toy_package(tmp_path, monkeypatch)
    replacement = original.replace(b"current-old", b"current-new")
    changed = replace_after_first_binary_read(
        monkeypatch, quarantine, replacement, binary_only=False)
    refusal = None
    index = None
    try:
        index, _ = gate._referenced_rekey_source_index(tmp_path)
    except gate.BlastpDiscoveryError as exc:
        refusal = str(exc)
    assert changed == [True]
    assert quarantine.read_bytes() == replacement
    if refusal is None:
        assert index[("nr", "ITEM001", "a" * 64)][0]["held_current_bgcs"] == ["current-old"]
    else:
        assert "HOLD" in refusal


def test_unchanged_quarantine_retains_existing_receipt_shape(tmp_path, monkeypatch):
    quarantine, original = _toy_package(tmp_path, monkeypatch)
    index, summaries = gate._referenced_rekey_source_index(tmp_path)
    assert index[("nr", "ITEM001", "a" * 64)][0]["held_current_bgcs"] == ["current-old"]
    assert summaries == [{"receipt": "toy.json", "channel": "nr", "admitted_total": 0,
                          "quarantined_total": 1, "hold_reasons": {"TOY_HOLD": 1}}]
    assert quarantine.read_bytes() == original
