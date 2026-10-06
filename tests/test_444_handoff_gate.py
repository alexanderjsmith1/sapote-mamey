"""tools/handoff_gate.py: one fail-closed check before a handoff.

2026-09-28: "maybe we need a module or step that checks everything? a gate?" after a session where every miss
reached the owner: dead reply links, a stale HASHES.txt, BGC identities without their alias, claim text on figures.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("handoff_gate", ROOT / "tools/handoff_gate.py")
hg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hg)

DIFF = "--- a/x.txt\n+++ b/x.txt\n@@ -1 +1 @@\n-a\n+b\n"


def _packet(tmp_path, queue_sha=None, hashes_sha=None, orphan=False):
    q = tmp_path / "patches"
    card = q / "card_one"
    card.mkdir(parents=True)
    (card / "CARD.md").write_text("# card one\n")
    (card / "fix.diff").write_text(DIFF)
    h = hashlib.sha256(DIFF.encode()).hexdigest()
    (card / "HASHES.txt").write_text(f"{hashes_sha or h}  fix.diff\n")
    (q / "00_QUEUE_1.md").write_text(f"## 1. card one\n\n`card_one/`, `fix.diff` (sha256 `{(queue_sha or h)[:8]}…`).\n")
    if orphan:
        (q / "card_two").mkdir()
        (q / "card_two" / "other.diff").write_text(DIFF)
    compose = tmp_path / "compose.sh"
    compose.write_text('#!/bin/bash\nQ="unused"\nstep "1 card one" "$Q/card_one/fix.diff"\n')
    return q, compose


def _receipt(path):
    return {r["check"]: r["result"] for r in json.loads(Path(path).read_text())["checks"]}


def test_a_clean_packet_passes(tmp_path):
    q, compose = _packet(tmp_path)
    assert hg.main(["patches", str(q), "--compose", str(compose)]) == 0
    assert set(_receipt(q / "HANDOFF_GATE_RECEIPT.json").values()) == {"PASS"}


def test_queue_and_hashes_drift_and_orphans_fail(tmp_path):
    q, compose = _packet(tmp_path, queue_sha="0" * 64, hashes_sha="1" * 64, orphan=True)
    assert hg.main(["patches", str(q), "--compose", str(compose)]) == 1
    r = _receipt(q / "HANDOFF_GATE_RECEIPT.json")
    assert r["queue sha matches each diff"] == "FAIL"
    assert r["HASHES.txt lines match their files"] == "FAIL"
    assert r["every card with a diff is composed or excluded"] == "FAIL"


def test_reply_links_must_open_files_and_be_encoded(tmp_path):
    (tmp_path / "Some Folder (v1)").mkdir()
    (tmp_path / "Some Folder (v1)" / "a.md").write_text("x\n")
    good = tmp_path / "good.md"
    good.write_text("[a](Some%20Folder%20%28v1%29/a.md)\n")
    assert hg.main(["reply", str(good), "--root", str(tmp_path)]) == 0
    bad = tmp_path / "bad.md"
    bad.write_text("[a](../../Some%20Folder%20%28v1%29/a.md) [b](Some%20Folder%20(v1)/a.md) [c](Some%20Folder%20%28v1%29)\n")
    assert hg.main(["reply", str(bad), "--root", str(tmp_path)]) == 1
    r = _receipt(bad.with_suffix(".handoff_gate.json"))
    assert r["reply links open files under the project root"] == "FAIL"
    assert r["reply links encode parentheses as %28 %29"] == "FAIL"


def test_deliverable_flags_short_identities_unlinked_figures_and_claim_text(tmp_path):
    d = tmp_path / "run"
    (d / "figures").mkdir(parents=True)
    (d / "figures" / "one.png").write_bytes(b"png")
    (d / "figures" / "two.png").write_bytes(b"png")
    (d / "INDEX.md").write_text("| S1 / NODE_1_length_9 / region001 | [png](figures/one.png) |\n")
    (d / "draw.py").write_text('fig.suptitle("S1 cluster (homology is not product identity)")\n')
    assert hg.main(["deliverable", str(d), "--index", "INDEX.md", "--figure-dir", "figures"]) == 1
    r = _receipt(d / "HANDOFF_GATE_RECEIPT.json")
    assert r["every file an index links exists"] == "PASS"
    assert r["every figure is linked by an index"] == "FAIL"
    assert r["BGC identities carry the alias (strain / node / region / BGC)"] == "FAIL"
    assert r["no claim wording drawn on figures (figure_policy)"] == "FAIL"


def test_refuses_to_write_its_receipt_inside_the_bundle(tmp_path):
    q, compose = _packet(tmp_path)
    with pytest.raises(Exception):
        hg.main(["patches", str(q), "--compose", str(compose), "--receipt", str(ROOT / "tmp_gate_receipt.json")])
    assert not (ROOT / "tmp_gate_receipt.json").exists()
