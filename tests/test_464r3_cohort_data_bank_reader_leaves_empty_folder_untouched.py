"""A read-only bank path never creates .ingest.lock (or anything) in a folder with no bank state."""
from __future__ import annotations

import hashlib
import json

from mamey import bank_transaction as B
from mamey.comparative_pairs import load_bank
from tools import ingest_package as I


def _snapshot(folder):
    return {p.relative_to(folder).as_posix(): (hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else "DIR")
            for p in sorted(folder.rglob("*"))}


def _entry(sid="SYN-A"):
    return {'workflow_version': 'v1', 'sid': sid, 'strain': {'sid': sid},
            'bgcs': [{'sid': sid, 'bgc_id': 'BGC001', 'products': 'synthetic', 'length_kb': 1, 'edge_status': 'Interior'}],
            'scan_agg': {}, 'tfbs': {}, 'rggmci_full': {}, 'tigrfam': {}, 'coupling': {}, 'resistance_coupling': {},
            'modeb_verdicts': [{'strain': sid, 'bgc': 'BGC001', 'status': 'CANDIDATE', 'modeb_class': '', 'note': ''}]}


def test_empty_bank_folder_read_paths_write_nothing(tmp_path):
    bank = tmp_path / "bank"
    bank.mkdir()
    (bank / "notes.txt").write_text("user file", encoding="utf-8")
    before = _snapshot(bank)
    assert load_bank(bank / "bgc_data.json") == {"strains": {}, "bgcs": []}
    with B.reader(bank):
        pass
    B.hold_reader(bank)
    B.release_reader_locks()
    assert _snapshot(bank) == before
    assert not (bank / ".ingest.lock").exists()


def test_writer_still_creates_its_lock_and_reader_then_locks(tmp_path):
    bank = tmp_path / "bank"
    bank.mkdir()
    I.merge(_entry(), bank, allow_dup=True)
    assert (bank / ".ingest.lock").exists()
    lock_bytes = (bank / ".ingest.lock").read_bytes()
    assert "SYN-A" in load_bank(bank / "bgc_data.json")["strains"]
    assert (bank / ".ingest.lock").read_bytes() == lock_bytes


def test_legacy_bank_with_a_store_still_takes_the_shared_lock(tmp_path):
    bank = tmp_path / "legacy"
    bank.mkdir()
    (bank / "bgc_data.json").write_text(json.dumps({"strains": {}, "bgcs": []}), encoding="utf-8")
    with B.reader(bank):
        pass
    assert (bank / ".ingest.lock").exists()
