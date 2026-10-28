"""ingest-receipts --card never prints a structure PASS for a card the gate did not evaluate.

A card for a BGC already COMPLETE in the register, or for a BGC the register does not know, returns
before the structure gate runs, with no findings. The CLI read "no findings" as a clean lint and
printed "structure: PASS (§1–§48 contract satisfied)" for a card it never checked.
"""
import subprocess
import sys
from pathlib import Path

from mamey.mode_b_receipt import ingest_one_card
from tests.test_ingest_one_card import _card_with_header, _make_pkg_with_register

ROOT = Path(__file__).resolve().parents[1]


def _cli(pkg, card):
    return subprocess.run([sys.executable, str(ROOT / "mamey_run.py"), "ingest-receipts", "--package", str(pkg),
                           "--card", str(card)], capture_output=True, text=True, cwd=ROOT)


def _card(tmp_path, bgc):
    card = tmp_path / f"AS-XXX_{bgc}_mode_b.md"
    card.write_text(_card_with_header(bgc, "AS-XXX", "S-9"))
    return card


def test_already_complete_card_is_not_evaluated_and_not_passed(tmp_path):
    pkg = _make_pkg_with_register(tmp_path, bgc_states={"BGC001": "COMPLETE"})
    card = _card(tmp_path, "BGC001")
    summary = ingest_one_card(pkg, card)
    assert summary["status"] == "SKIPPED_ALREADY_COMPLETE"
    assert summary["structure_evaluated"] is False
    r = _cli(pkg, card)
    assert "PASS" not in r.stdout, r.stdout
    assert "structure:         NOT EVALUATED (status SKIPPED_ALREADY_COMPLETE" in r.stdout
    assert r.returncode == 1


def test_unknown_bgc_card_is_not_evaluated_and_not_passed(tmp_path):
    pkg = _make_pkg_with_register(tmp_path, bgc_states={"BGC001": "PENDING"})
    card = _card(tmp_path, "BGC009")
    assert ingest_one_card(pkg, card)["status"] == "SKIPPED_UNKNOWN"
    r = _cli(pkg, card)
    assert "PASS" not in r.stdout, r.stdout
    assert "NOT EVALUATED (status SKIPPED_UNKNOWN" in r.stdout


def test_a_card_the_gate_ran_on_is_marked_evaluated(tmp_path):
    pkg = _make_pkg_with_register(tmp_path)
    summary = ingest_one_card(pkg, _card(tmp_path, "BGC001"))
    assert summary["structure_evaluated"] is True
    assert "NOT EVALUATED" not in str(summary["structure_findings"])
