"""ingest-receipts --master updates E1 for --card and --auto-detect, not only for --receipt.

The help says "+ optional --master E1 reconcile". The --card and --auto-detect flows returned
before --master was read, so the workbook was silently left stale.
"""
from types import SimpleNamespace

import pytest

import mamey.master_workbook as master_workbook
import mamey.mode_b_receipt as mbr


@pytest.fixture
def e1_calls(monkeypatch):
    calls = []

    def fake_update(pkg, wb):
        calls.append((pkg, wb))
        return {"bgcs_complete": 1, "bgcs_written": 2}

    monkeypatch.setattr(master_workbook, "update_e1_from_judgment", fake_update)
    return calls


def _args(pkg, **kw):
    base = dict(package=str(pkg), auto_detect=False, receipt=None, card=None,
                master=None, force_structure=False)
    base.update(kw)
    return SimpleNamespace(**base)


def test_card_flow_applies_master(tmp_path, monkeypatch, e1_calls, capsys):
    monkeypatch.setattr(mbr, "ingest_one_card", lambda pkg, card, force_structure=False: {
        "strain_id": "S1", "bgc_id": "B1", "session_id": None, "status": "RECORDED",
        "structure_findings": [], "judgment_status": "OK"})
    wb = tmp_path / "master.xlsx"
    rc = mbr.ingest_receipts_command(_args(tmp_path, card=str(tmp_path / "c.md"), master=str(wb)))
    assert rc == 0
    assert len(e1_calls) == 1 and str(e1_calls[0][1]) == str(wb)
    assert "workbook E1:       updated" in capsys.readouterr().out


def test_auto_flow_applies_master(tmp_path, monkeypatch, e1_calls):
    monkeypatch.setattr(mbr, "auto_detect_ingest", lambda pkg, force_structure=False: {
        "strain_id": "S1", "scanned_count": 1, "recorded": ["B1"],
        "skipped_already_complete": [], "skipped_unknown": [], "judgment_status": "OK"})
    rc = mbr.ingest_receipts_command(_args(tmp_path, auto_detect=True, master=str(tmp_path / "m.xlsx")))
    assert rc == 0
    assert len(e1_calls) == 1


def test_failed_card_ingest_leaves_workbook_alone(tmp_path, monkeypatch, e1_calls):
    monkeypatch.setattr(mbr, "ingest_one_card", lambda pkg, card, force_structure=False: {
        "strain_id": "S1", "bgc_id": None, "session_id": None, "status": "SKIPPED_UNKNOWN_BGC",
        "structure_findings": [], "judgment_status": "OK"})
    rc = mbr.ingest_receipts_command(_args(tmp_path, card=str(tmp_path / "c.md"), master=str(tmp_path / "m.xlsx")))
    assert rc == 1
    assert e1_calls == []


def test_no_master_no_workbook_call(tmp_path, monkeypatch, e1_calls):
    monkeypatch.setattr(mbr, "ingest_one_card", lambda pkg, card, force_structure=False: {
        "strain_id": "S1", "bgc_id": "B1", "session_id": None, "status": "RECORDED",
        "structure_findings": [], "judgment_status": "OK"})
    assert mbr.ingest_receipts_command(_args(tmp_path, card=str(tmp_path / "c.md"))) == 0
    assert e1_calls == []
