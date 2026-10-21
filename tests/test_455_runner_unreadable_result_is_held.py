"""Offline runner control: a READY result that cannot be read is held, not downloaded forever.

A READY RID whose body arrives but cannot be admitted was marked `retrieval_unverified` and kept
in flight, so it was downloaded again at every status check and again after every restart, each
time saving another identical raw copy. The count of unreadable downloads now comes from the
per-attempt receipts in xml/, so after three the row is `unsure` for the operator, every raw
response is kept, and a restart does not start the count over. No network, no real waiting.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import time as real_time

ROOT = Path(__file__).resolve().parents[1]
HEADER = "STRAIN_X|BGC001|NODE_1_length_1000_cov_1|gene=g1|aa=40"
SEQUENCE = "ACDEFGHIKLMNPQRSTVWY" * 2
RID = "SYNTHETICRID01"
ATTEMPT = re.compile(re.escape(RID) + r"-[0-9a-f]{32}\.xml")


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


def load_runner(tmp_path, monkeypatch, downloads, fetch_error=None):
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("RID_DATABASE", "nr")
    monkeypatch.setenv("RID_QUERIES", "_QUERIES_TEST")
    monkeypatch.setenv("RID_BASE", "_OFFLINE_TEST")
    spec = importlib.util.spec_from_file_location(
        "unreadable_runner", ROOT / "tools/blastp_crawl/nr_rid_runner.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "time", Clock())
    monkeypatch.setattr(module, "paced_sleep", lambda value: 0.0)
    monkeypatch.setattr(module, "status", lambda rid: "READY")

    def fetch(rid):
        downloads.append(rid)
        if fetch_error is not None:
            raise module.TransportUnverified(fetch_error, response="<html>busy</html>")
        return "<BlastXML2/>"

    def unreadable(*args, **kwargs):
        raise ValueError("Hit missing required result field")

    def forbidden(*args, **kwargs):
        raise AssertionError("No real transport, submit or live process probe in this fixture")
    monkeypatch.setattr(module, "fetch_xml2", fetch)
    monkeypatch.setattr(module, "parse_xml2", unreadable)
    monkeypatch.setattr(module, "submit", forbidden)
    monkeypatch.setattr(module, "_curl", forbidden)
    monkeypatch.setattr(module, "live_runner_count", forbidden)
    return module


def seed_submitted_rid(module):
    """One query file and a ledger row for a RID submitted by an earlier run."""
    query = module.QUERIES / "LANE" / "PANEL001" / "query.faa"
    if not query.exists():
        query.parent.mkdir(parents=True)
        query.write_bytes((">" + HEADER + "\n" + SEQUENCE + "\n").encode("utf-8"))
        key = module.relkey(query)
        module.save_ledger({key: {
            "strain": "LANE", "bgc": "PANEL001", "file": key, "rid": RID, "rtoe": 30,
            "submit_iso": module.now_iso(), "status": "submitted",
            "query_sha256": hashlib.sha256(query.read_bytes()).hexdigest(),
            "query_roster": json.dumps([HEADER]), "database": "nr", "fetch_iso": "", "note": ""}})
    return module.relkey(query)


def run_args(seconds):
    return argparse.Namespace(
        hours=seconds / 3600.0, sleep=300.0, limit=0, max_inflight=1,
        hold_after=3600.0, max_held=4, max_wait=129600.0,
        min_aa=20, max_aa=1000, max_one_residue=0.6,
        allow_mixed_tree=False, ignore_handoff=False)


def attempts(module):
    return sorted(p.name for p in module.XMLDIR.iterdir() if ATTEMPT.fullmatch(p.name))


def test_unreadable_result_is_held_after_three_downloads(tmp_path, monkeypatch):
    downloads = []
    module = load_runner(tmp_path, monkeypatch, downloads)
    key = seed_submitted_rid(module)
    assert module.cmd_run(run_args(900)) == 0
    row = module.load_ledger()[key]
    assert downloads == [RID] * 3, "no fourth download once the result is held"
    assert row["status"] == "unsure"
    assert "unreadable after 3 downloads" in row["note"]
    assert len(attempts(module)) == 3, "every raw response stays in xml/"


def test_count_survives_a_restart(tmp_path, monkeypatch):
    downloads = []
    module = load_runner(tmp_path, monkeypatch, downloads)
    key = seed_submitted_rid(module)
    assert module.cmd_run(run_args(100)) == 0          # two downloads, then the run ends
    assert downloads == [RID] * 2
    assert module.load_ledger()[key]["status"] == "retrieval_unverified"
    module = load_runner(tmp_path, monkeypatch, downloads)
    seed_submitted_rid(module)
    assert module.cmd_run(run_args(100)) == 0          # one more download reaches the hold
    assert downloads == [RID] * 3
    assert module.load_ledger()[key]["status"] == "unsure"
    module = load_runner(tmp_path, monkeypatch, downloads)
    assert module.cmd_run(run_args(100)) == 0          # a held row is not resumed
    assert downloads == [RID] * 3


def test_transport_failures_do_not_count_toward_the_hold(tmp_path, monkeypatch):
    downloads = []
    module = load_runner(tmp_path, monkeypatch, downloads, fetch_error="HTTP 503")
    key = seed_submitted_rid(module)
    assert module.cmd_run(run_args(900)) == 0
    assert len(downloads) > 3
    assert module.load_ledger()[key]["status"] == "retrieval_unverified"
    assert module.unreadable_downloads(RID) == 0
