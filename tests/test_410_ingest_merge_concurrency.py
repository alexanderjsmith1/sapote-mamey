"""v9.7.410 hostile audit — two processes banking into the same cohort dir.

Before: tools/ingest_package.merge was an unlocked eight-file read-modify-write staging through a
FIXED ``<file>.tmp`` name. Two concurrent bankers reproduced (a) ``FileNotFoundError`` in
``os.replace`` when one process's stage was moved by the other, and (b) a lost update — one
strain's modeb_verdicts rows vanished from the cohort CSV. Now: unique private stage files and a
blocking exclusive advisory lock around the merge.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import multiprocessing as mp
import os
import sys
from pathlib import Path

import pytest

import mamey

ROOT = Path(mamey.__file__).resolve().parent.parent
TOOL = ROOT / "tools" / "ingest_package.py"

pytestmark = pytest.mark.skipif(not hasattr(os, "fork"), reason="fork-based race needs POSIX")


def _load():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("ingest_package_under_test", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _entry(sid: str, salt: int) -> dict:
    return {
        "sid": sid, "strain": {"sid": sid},
        "bgcs": [{"sid": sid, "bgc_id": f"BGC{i:03d}", "products": f"p-{sid}-{i}",
                  "length_kb": 10 + i + salt, "edge_status": "Interior"} for i in range(3)],
        "scan_agg": {}, "tfbs": {}, "rggmci_full": {}, "tigrfam": {}, "coupling": {},
        "resistance_coupling": {},
        "modeb_verdicts": [{"strain": sid, "bgc_id": "BGC001", "verdict": f"v{salt}"}],
    }


def _banker(sid: str, base: int, banked: str, barrier, rounds: int) -> None:
    mod = _load()
    barrier.wait()
    for k in range(rounds):
        mod.merge(_entry(sid, base * 100 + k), banked, allow_dup=True)


def test_two_bankers_do_not_lose_each_others_rows(tmp_path):
    banked = tmp_path / "banked"
    banked.mkdir()
    ctx = mp.get_context("fork")
    barrier = ctx.Barrier(2)
    procs = [ctx.Process(target=_banker, args=(sid, i, str(banked), barrier, 12))
             for i, sid in enumerate(("AS-A", "AS-B"))]
    for p in procs:
        p.start()
    for p in procs:
        p.join(120)
    assert [p.exitcode for p in procs] == [0, 0], "a banker died (os.replace race)"
    bgc = json.loads((banked / "bgc_data.json").read_text(encoding="utf-8"))
    assert sorted(bgc["strains"]) == ["AS-A", "AS-B"]
    per_sid = {s: sum(1 for b in bgc["bgcs"] if b["sid"] == s) for s in ("AS-A", "AS-B")}
    assert per_sid == {"AS-A": 3, "AS-B": 3}, per_sid
    with (banked / "modeb_verdicts.csv").open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    # the cohort CSV is re-headed to the engine's canonical verdict columns; count rows per strain
    per_strain = {s: sum(1 for r in rows if r.get("strain") == s) for s in ("AS-A", "AS-B")}
    assert per_strain == {"AS-A": 1, "AS-B": 1}, per_strain  # neither strain's rows were lost
    assert not list(banked.glob("*.tmp")), "stage files left behind"


def test_atomic_writers_use_private_stage_files(tmp_path):
    mod = _load()
    target = tmp_path / "x.json"
    a, b = mod._private_tmp(str(target)), mod._private_tmp(str(target))
    assert a != b and Path(a).parent == target.parent == Path(b).parent
    for t in (a, b):
        os.unlink(t)
    mod.atomic_dump({"k": 1}, target)
    assert json.loads(target.read_text()) == {"k": 1}
    assert not list(tmp_path.glob(".x.json.*.tmp"))
