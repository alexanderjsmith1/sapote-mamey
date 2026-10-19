"""Offline runner control: a returned RID binds the exact submitted query buffer."""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import sys
import time as real_time

import pytest

ROOT = Path(__file__).resolve().parents[1]
HEADER = "SID-999999|BGC001|NODE_1_length_1000_cov_1|gene=ctg1_1|aa=40"
SEQUENCE = "ACDEFGHIKLMNPQRSTVWY" * 2


class Clock:
    def __init__(self):
        self.now = 1_800_000_000.0

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds

    def strftime(self, fmt):
        return real_time.strftime(fmt, real_time.localtime(self.now))

    def strptime(self, value, fmt):
        return real_time.strptime(value, fmt)

    def mktime(self, value):
        return real_time.mktime(value)


def load_runner(tmp_path, monkeypatch):
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("RID_DATABASE", "nr")
    monkeypatch.setenv("RID_QUERIES", "_QUERIES_TEST")
    monkeypatch.setenv("RID_BASE", "_OFFLINE_TEST")
    spec = importlib.util.spec_from_file_location(
        "c09_runner", ROOT / "tools/blastp_crawl/nr_rid_runner.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    clock = Clock()
    monkeypatch.setattr(module, "time", clock)
    monkeypatch.setattr(module, "paced_sleep", lambda value: 0.0)
    monkeypatch.setattr(module, "status", lambda rid: "WAITING")
    def forbidden(*args, **kwargs):
        raise AssertionError("No real transport, fetch or live process probe in this fixture")
    monkeypatch.setattr(module, "_curl", forbidden)
    monkeypatch.setattr(module, "fetch_xml2", forbidden)
    monkeypatch.setattr(module, "live_runner_count", forbidden)
    return module


def run_args():
    # Exactly one simulated five-second cycle; no real waiting or remote analysis.
    return argparse.Namespace(
        hours=1.0 / 3600.0, sleep=300.0, limit=1, max_inflight=1,
        hold_after=3600.0, max_held=4, max_wait=129600.0,
        min_aa=20, max_aa=1000, max_one_residue=0.6,
        allow_mixed_tree=False, ignore_handoff=False)


def staged_query(module, newline="\n"):
    query = module.QUERIES / "SID-999999" / "PANEL001" / "query.faa"
    query.parent.mkdir(parents=True)
    raw = (">" + HEADER + newline + SEQUENCE + newline).encode("utf-8")
    query.write_bytes(raw)
    return query, raw


@pytest.mark.parametrize("change", ["inplace", "atomic", "unlink"])
def test_returned_rid_binds_submitted_buffer_despite_path_change(tmp_path, monkeypatch, change):
    module = load_runner(tmp_path, monkeypatch)
    query, raw = staged_query(module)
    expected_text = query.read_text(errors="replace")
    sent = []
    def submit_and_change(text):
        sent.append(text)
        replacement = (">" + HEADER + "\n" + SEQUENCE[::-1] + "\n").encode("utf-8")
        if change == "inplace":
            query.write_bytes(replacement)
        elif change == "atomic":
            alternate = query.with_name("replacement.faa")
            alternate.write_bytes(replacement)
            alternate.replace(query)
        else:
            query.unlink()
        return "SYNTHETIC_RID_001", 30
    monkeypatch.setattr(module, "submit", submit_and_change)
    rc = module.cmd_run(run_args())
    ledger = module.load_ledger()
    assert sent == [expected_text]
    assert len(ledger) == 1, "A successfully returned RID must survive a changed/missing query path"
    record = next(iter(ledger.values()))
    assert record["rid"] == "SYNTHETIC_RID_001"
    assert record["query_sha256"] == hashlib.sha256(raw).hexdigest(), "Ledger hash must bind the submitted buffer"
    assert record["query_roster"] == __import__("json").dumps([HEADER])
    assert rc == 0
    assert not (module.BASE / "_runner.pid").exists()


@pytest.mark.parametrize("newline", ["\n", "\r\n", "\r"])
def test_unchanged_query_preserves_text_decoding_and_raw_file_hash(tmp_path, monkeypatch, newline):
    module = load_runner(tmp_path, monkeypatch)
    query, raw = staged_query(module, newline)
    expected_text = query.read_text(errors="replace")
    sent = []
    def submit(text):
        sent.append(text)
        return "SYNTHETIC_RID_001", 30
    monkeypatch.setattr(module, "submit", submit)
    assert module.cmd_run(run_args()) == 0
    record = next(iter(module.load_ledger().values()))
    assert sent == [expected_text]
    assert record["query_sha256"] == hashlib.sha256(raw).hexdigest()
    assert query.read_bytes() == raw


def test_unsuccessful_submit_does_not_invent_a_returned_rid(tmp_path, monkeypatch):
    module = load_runner(tmp_path, monkeypatch)
    query, raw = staged_query(module)
    calls = []
    def failed(text):
        calls.append(text)
        query.write_bytes(raw.replace(b"ACDE", b"EDCA"))
        return "", 0
    monkeypatch.setattr(module, "submit", failed)
    assert module.cmd_run(run_args()) == 0
    assert len(calls) == 1
    assert module.load_ledger() == {}

