"""Bank recovery refuses unknown current bytes; --out never replaces an existing entry file.

Synthetic bank fixtures only.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

from mamey import bank_transaction as B
from tools import ingest_package as I

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("_bank_fixture_464r3", ROOT / "tests" / "test_447_bank_transaction.py")
_fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fx)


def _interrupt(tmp_path, monkeypatch, boundary="published:gene_data.json"):
    bank = _fx.seed(tmp_path)
    monkeypatch.setattr(B, "_boundary", lambda n: (_ for _ in ()).throw(RuntimeError()) if n == boundary else None)
    with pytest.raises(RuntimeError):
        I.merge(_fx.entry("SYN-B"), bank, allow_dup=True)
    monkeypatch.setattr(B, "_boundary", lambda _: None)
    return bank


@pytest.mark.parametrize("mode", ["rollback", "finish"])
def test_recovery_refuses_a_store_edited_outside_the_protocol(tmp_path, monkeypatch, mode):
    bank = _interrupt(tmp_path, monkeypatch)
    edited = b'{"edited": "by hand after the interruption"}\n'
    (bank / "tigrfam.json").write_bytes(edited)
    snapshot = _fx.snap(bank)
    with pytest.raises(B.BankError, match="BANK_RECOVERY_CONFLICT: tigrfam.json"):
        B.recover(bank, mode)
    assert (bank / "tigrfam.json").read_bytes() == edited
    assert _fx.snap(bank) == snapshot
    assert (bank / B.PENDING).exists()


def test_rollback_refuses_to_unlink_a_file_that_was_absent_before_but_now_holds_other_bytes(tmp_path, monkeypatch):
    bank = _interrupt(tmp_path, monkeypatch, boundary="pending")
    journal = json.loads((bank / B.PENDING).read_text())
    absent_before = [n for n, h in journal["before_sha256"].items() if h is None]
    assert "deep_data.json" in absent_before
    (bank / "deep_data.json").write_text('{"someone": "else"}\n')
    with pytest.raises(B.BankError, match="BANK_RECOVERY_CONFLICT: deep_data.json"):
        B.recover(bank, "rollback")
    assert (bank / "deep_data.json").read_text() == '{"someone": "else"}\n'


def test_recovery_refuses_an_unknown_commit_state(tmp_path, monkeypatch):
    bank = _interrupt(tmp_path, monkeypatch)
    (bank / B.STATE).write_text('{"schema": "sapote.bank-commit.v1", "transaction": "other"}\n')
    with pytest.raises(B.BankError, match="BANK_RECOVERY_CONFLICT"):
        B.recover(bank, "rollback")


@pytest.mark.parametrize("boundary", ["pending", "published:gene_data.json", "committed"])
@pytest.mark.parametrize("mode", ["rollback", "finish"])
def test_ordinary_interruptions_still_recover(tmp_path, monkeypatch, boundary, mode):
    bank = _interrupt(tmp_path, monkeypatch, boundary)
    assert B.recover(bank, mode)["state"] in ("ROLLED_BACK", "FINISHED")
    B.coherent(bank)


def test_entry_export_refuses_an_existing_out_file(tmp_path):
    existing = tmp_path / "entry.json"
    existing.write_text("earlier export\n")
    with pytest.raises(FileExistsError):
        I.write_new_entry({"sid": "SYN-A"}, existing)
    assert existing.read_text() == "earlier export\n"
    fresh = tmp_path / "fresh.json"
    I.write_new_entry({"sid": "SYN-A"}, fresh)
    assert json.loads(fresh.read_text()) == {"sid": "SYN-A"}
    assert sorted(p.name for p in tmp_path.iterdir()) == ["entry.json", "fresh.json"]


def test_cli_out_collision_keeps_the_file_and_never_merges(tmp_path, monkeypatch):
    package = tmp_path / "pkg"
    package.mkdir()
    out = tmp_path / "entry.json"
    out.write_text("keep\n")
    built = {"sid": "SYN-A", "bgcs": [], "scan_agg": {"EFLS_pairs": 0, "FLBR_megasynth": 0, "CCTT_triggers": 0}}
    monkeypatch.setattr(I, "find_snapshot", lambda package: "unused")
    monkeypatch.setattr(I, "load", lambda path: {"strain_id": "SYN-A"})
    monkeypatch.setattr(I, "build_entry", lambda *a, **k: dict(built))
    merged = []
    monkeypatch.setattr(I, "merge", lambda *a, **k: merged.append(a))
    monkeypatch.setattr(sys, "argv", ["ingest_package.py", "--package", str(package), "--out", str(out),
                                      "--banked-dir", str(tmp_path / "bank"), "--merge", "--cohort", "REF"])
    with pytest.raises((FileExistsError, SystemExit)):
        I.main()
    assert out.read_text() == "keep\n"
    assert merged == []
