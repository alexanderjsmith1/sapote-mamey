"""v9.7.335 EXTENSION — the structure-gate fail-open in the other two receipt paths.

The shipped .335 patch closed `except Exception: structure_findings = []` in
`mode_b_receipt.ingest_one_card`. Auditing the rest of the module for the same shape found
two further call sites carrying the identical fail-open, both spelled out in a comment that
said so:

    except Exception:
        n_errors = 0  # gate fail-open

  * `ingest_receipt`      (line ~168) — the PRIMARY documented Sapote -> durable-store front
                                        door, the batch path SESSION_START_MANIFEST points at
  * `auto_detect_ingest`  (line ~371) — the session-start orphan-card recovery sweep

So a crashed gate was still recorded as a clean card on both of the paths a real session
actually uses, while the CHANGELOG would have claimed the class of bug was closed. These
tests feed each path a gate that raises and assert the card is skipped as unverified rather
than recorded.

Not changed, and flagged rather than patched: the `except Exception: _gate_available = False`
guard at the top of both functions. If the gate module fails to IMPORT the gate is skipped for
every card with no sentinel at all. That is a wider behaviour decision (some tier variants may
legitimately ship without it), so it is left for a sign-off rather than folded in here.
"""

import json
from pathlib import Path

import pytest

from mamey.judgment_store import init_register, read_register
from mamey import mode_b_receipt
from mamey.mode_b_receipt import RECEIPT_SCHEMA_VERSION

from tests._modeb_card_fixtures import valid_modeb_card_stub

STRAIN = "AS-TEST"


def _pkg(tmp_path: Path, bgc_ids=("BGC001",)) -> Path:
    pkg = tmp_path / STRAIN
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": STRAIN}), encoding="utf-8")
    init_register(pkg, strain_id=STRAIN, bgc_ids=list(bgc_ids))
    return pkg


def _boom(*a, **k):
    raise RuntimeError("simulated bundle-integrity fault")


def _break_gate(monkeypatch):
    """Make the structure-gate step raise, deterministically.

    `_bgc_context_from_triage` is called inside the SAME try: block as `lint_card`, and it is
    an attribute of mode_b_receipt itself, so patching it is order-independent. Patching
    `modeb_structure_gate.lint_card` instead is not: several tests in this suite load modules
    via spec_from_file_location, so under a full-suite run the object the receipt module
    imports is not always the object the test patched, and the gate quietly kept working.
    """
    monkeypatch.setattr(mode_b_receipt, "_bgc_context_from_triage", _boom)


# --------------------------------------------------------------------------------------
# ingest_receipt — the batch front door
# --------------------------------------------------------------------------------------

def test_ingest_receipt_does_not_record_a_card_whose_gate_crashed(tmp_path, monkeypatch):
    """KNOWN-BAD: gate raises during a receipt batch -> card skipped, not recorded COMPLETE."""
    _break_gate(monkeypatch)
    pkg = _pkg(tmp_path)
    rcpt = tmp_path / "mode_b_receipt.json"
    rcpt.write_text(json.dumps({
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "strain_id": STRAIN,
        "session_id": "sess-gatecrash",
        "cards": [{"bgc_id": "BGC001",
                   "mode_b_md": valid_modeb_card_stub("BGC001", strain_id=STRAIN)}],
    }), encoding="utf-8")

    summary = mode_b_receipt.ingest_receipt(pkg, rcpt)

    assert "BGC001" not in (summary.get("recorded") or []), (
        "a card whose structure gate crashed must not be recorded; the gate produced no "
        "verdict, which is not the same as a clean verdict"
    )
    assert any(b == "BGC001" for b, _ in (summary.get("skipped_structure_invalid") or [])), summary
    assert read_register(pkg)["bgcs"]["BGC001"]["status"] != "COMPLETE"


def test_control_ingest_receipt_still_records_a_clean_card(tmp_path):
    """Control: with the gate working normally, a valid card is still recorded."""
    pkg = _pkg(tmp_path)
    rcpt = tmp_path / "mode_b_receipt.json"
    rcpt.write_text(json.dumps({
        "schema_version": RECEIPT_SCHEMA_VERSION,
        "strain_id": STRAIN,
        "session_id": "sess-ok",
        "cards": [{"bgc_id": "BGC001",
                   "mode_b_md": valid_modeb_card_stub("BGC001", strain_id=STRAIN)}],
    }), encoding="utf-8")

    summary = mode_b_receipt.ingest_receipt(pkg, rcpt)
    assert summary.get("recorded") == ["BGC001"], summary
    assert read_register(pkg)["bgcs"]["BGC001"]["status"] == "COMPLETE"


# --------------------------------------------------------------------------------------
# auto_detect_ingest — the session-start recovery sweep
# --------------------------------------------------------------------------------------

def test_auto_detect_does_not_record_a_card_whose_gate_crashed(tmp_path, monkeypatch):
    """KNOWN-BAD: orphan-card sweep must not promote a card it could not lint."""
    _break_gate(monkeypatch)
    pkg = _pkg(tmp_path)
    jdir = pkg / "judgment"
    jdir.mkdir(exist_ok=True)
    (jdir / f"{STRAIN}_BGC001_mode_b.md").write_text(
        valid_modeb_card_stub("BGC001", strain_id=STRAIN), encoding="utf-8")

    summary = mode_b_receipt.auto_detect_ingest(pkg)

    assert "BGC001" not in (summary.get("recorded") or []), summary
    assert any(b == "BGC001" for b, _ in (summary.get("skipped_structure_invalid") or [])), summary
    assert read_register(pkg)["bgcs"]["BGC001"]["status"] != "COMPLETE"


def test_control_auto_detect_still_records_a_clean_orphan_card(tmp_path):
    """Control: the recovery sweep still works when the gate runs normally."""
    pkg = _pkg(tmp_path)
    jdir = pkg / "judgment"
    jdir.mkdir(exist_ok=True)
    (jdir / f"{STRAIN}_BGC001_mode_b.md").write_text(
        valid_modeb_card_stub("BGC001", strain_id=STRAIN), encoding="utf-8")

    summary = mode_b_receipt.auto_detect_ingest(pkg)
    assert "BGC001" in (summary.get("recorded") or []), summary
    assert read_register(pkg)["bgcs"]["BGC001"]["status"] == "COMPLETE"
