"""test_blast_ledger_v9_7_382.py — durable cross-run fair-use budget for the online BLASTp channels.

Hermetic: every test points MAMEY_BLAST_LEDGER at a tmp file (which also switches the ledger from
"inert in pytest" to active), so nothing touches the developer's real ~/.cache.
"""
import json
import time

import pytest

from mamey import blast_ledger as bl


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    p = tmp_path / "blast_ledger.json"
    monkeypatch.setenv("MAMEY_BLAST_LEDGER", str(p))
    monkeypatch.delenv("MAMEY_BLAST_DAILY_CAP", raising=False)
    return p


def test_record_and_count(ledger):
    assert bl.count_last(24) == 0
    bl.record("ncbi", 3)
    bl.record("ebi", 1)
    assert bl.count_last(24) == 4
    assert bl.count_last(24, service="ncbi") == 3
    assert bl.count_last(24, service="ebi") == 1


def test_budget_remaining_and_refusal(ledger):
    bl.record("ncbi", 98)
    assert bl.budget_remaining("ncbi", daily_cap=100) == 2
    # 2 remaining, asking for 2 is fine; asking for 3 must refuse
    bl.refuse_if_exhausted("ncbi", need=2, daily_cap=100)
    with pytest.raises(bl.BlastBudgetExceeded):
        bl.refuse_if_exhausted("ncbi", need=3, daily_cap=100)


def test_rolling_window_prunes_old(ledger):
    # write an entry 25 h old directly; it must fall outside the 24 h window
    old = time.time() - 25 * 3600
    ledger.write_text(json.dumps([{"t": old, "svc": "ncbi"}]), encoding="utf-8")
    assert bl.count_last(24) == 0
    bl.record("ncbi", 1)          # a fresh record prunes the stale entry on write
    assert bl.count_last(24) == 1
    assert len(json.loads(ledger.read_text())) == 1


def test_inert_in_pytest_without_env(monkeypatch):
    # with no MAMEY_BLAST_LEDGER set and PYTEST_CURRENT_TEST present, record/refuse are no-ops so the
    # developer's real ledger is never touched and a real backlog never gates the suite.
    monkeypatch.delenv("MAMEY_BLAST_LEDGER", raising=False)
    assert bl._active() is False
    bl.record("ncbi", 999)                      # no-op
    bl.refuse_if_exhausted("ncbi", need=10**9)  # no-op, does not raise


def test_channels_import_and_wire():
    # the two online channels import the ledger helpers at their submit points
    import mamey.blastp_online as onl
    import mamey.blastp_ebi as ebi
    assert "refuse_if_exhausted" in onl.run_batches_online.__code__.co_names
    src = __import__("inspect").getsource(ebi.submit_ebi)
    assert "refuse_if_exhausted" in src and "record(" in src
