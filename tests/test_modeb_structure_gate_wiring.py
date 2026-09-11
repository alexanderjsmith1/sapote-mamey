"""test_modeb_structure_gate_wiring.py — tests that the W9 structure gate
is wired into the three ingest paths (ingest_one_card, auto_detect_ingest,
ingest_receipt) and that the --force-structure escape valve works.

All fixtures use AS-XXX.
"""
from __future__ import annotations
import json
import pathlib

import pytest


def _make_pkg_with_register(tmp_path: pathlib.Path) -> pathlib.Path:
    pkg = tmp_path / "AS-XXX" / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "AS-XXX"}))
    (pkg / "manifest_short.json").write_text(json.dumps({
        "strain_id": "AS-XXX", "assembly_tier": "POOR", "interior_pct": 25.0}))
    (pkg / "AS-XXX_4_triage_board.csv").write_text(
        "BGC_ID,Node_ID,Contig,Products,Boundary,AB_auto,AF_auto,"
        "Lead_tier_auto,Corrected_rank,KCB_top\n"
        "BGC033,NODE_7,ctg7,NRPS,Interior,65,40,HIGH,1,nystatin\n"
    )
    (pkg / "AS-XXX_judgment_register.json").write_text(json.dumps({
        "schema_version": "1.0",
        "strain_id": "AS-XXX",
        "total_bgcs": 1,
        "complete_bgcs": 0,
        "completion_pct": 0.0,
        "judgment_status": "PENDING",
        "last_sapote_session": None,
        "bgcs": {"BGC033": {
            "status": "PENDING", "mode_b_file": None,
            "session_id": None, "timestamp": None}},
    }))
    return pkg


def _full_card():
    """A complete §1–§30 card (always-required + applicable conditional
    sections for an antimicrobial NRPS BGC)."""
    sections = [
        (1, "Identity and node/region"),
        (2, "Why this BGC was selected"),
        (3, "Boundary and assembly status"),
        (4, "Gene-by-gene interpretation"),
        (5, "Core biosynthetic logic"),
        (6, "Tailoring and maturation logic"),
        (7, "Transport, resistance, and regulation"),
        (8, "Comparator/KCB interpretation"),
        (9, "Alternative hypotheses"),
        (10, "Fragmentation and co-capture risks"),
        (11, "Product-family interpretation"),
        (12, "Bee/microbe ecological interpretation"),
        (13, "Antibacterial/antifungal relevance"),
        (14, "What cannot be claimed"),
        (15, "Missing evidence"),
        (16, "BLASTP/HMMER next steps"),
        (17, "LC-MS / fermentation implications"),
        (18, "Figure/locus-map notes"),
        (19, "Final Mode B judgement"),
        (20, "Next actions"),
        (25, "Genome neighbourhood"),       # isolation_worthy (HIGH lead tier)
        (27, "Self-resistance assessment"),  # antimicrobial NRPS
        (28, "Evidence provenance ledger"),
        (30, "Experimental decision tree"),
    ]
    return "".join(f"## §{n} {t}\n\nbody\n\n" for n, t in sections)


def _legacy_card():
    """The BGC033-pattern card."""
    return (
        "<!-- MODE B: BGC033 | strain: AS-XXX | session: S-test | 2026-06-30 -->\n\n"
        "## §1 Identity\nbody\n\n"
        "## §2 Assembly\nbody\n\n"
        "## §9 Activation\nbody\n\n"
        "## §10 Forensic sweep\nbody\n\n"
    )


# ---------------------------------------------------------------------------
# ingest_one_card wiring
# ---------------------------------------------------------------------------

def test_ingest_one_card_refuses_legacy_scaffold_by_default(tmp_path):
    from mamey.mode_b_receipt import ingest_one_card
    pkg = _make_pkg_with_register(tmp_path)
    card = tmp_path / "AS-XXX_BGC033_mode_b.md"
    card.write_text(_legacy_card())

    res = ingest_one_card(pkg, card)
    assert res["status"] == "SKIPPED_STRUCTURE_INVALID"
    assert len(res["structure_findings"]) > 0
    # And the register was NOT advanced
    reg = json.loads((pkg / "AS-XXX_judgment_register.json").read_text())
    assert reg["bgcs"]["BGC033"]["status"] == "PENDING"


def test_ingest_one_card_accepts_canonical_30_section_card(tmp_path):
    from mamey.mode_b_receipt import ingest_one_card
    pkg = _make_pkg_with_register(tmp_path)
    card = tmp_path / "AS-XXX_BGC033_mode_b.md"
    card.write_text(
        "<!-- MODE B: BGC033 | strain: AS-XXX | session: S-test | 2026-06-30 -->\n\n"
        + _full_card())

    res = ingest_one_card(pkg, card)
    assert res["status"] == "RECORDED", (
        f"got {res['status']}; findings: {res.get('structure_findings')}"
    )
    reg = json.loads((pkg / "AS-XXX_judgment_register.json").read_text())
    assert reg["bgcs"]["BGC033"]["status"] == "COMPLETE"


def test_ingest_one_card_force_structure_overrides_refusal(tmp_path):
    from mamey.mode_b_receipt import ingest_one_card
    pkg = _make_pkg_with_register(tmp_path)
    card = tmp_path / "AS-XXX_BGC033_mode_b.md"
    card.write_text(_legacy_card())

    res = ingest_one_card(pkg, card, force_structure=True)
    assert res["status"] == "RECORDED_WITH_STRUCTURE_OVERRIDE"
    # findings still surfaced even though it was recorded
    assert any(f["severity"] == "ERROR" for f in res["structure_findings"])
    reg = json.loads((pkg / "AS-XXX_judgment_register.json").read_text())
    assert reg["bgcs"]["BGC033"]["status"] == "COMPLETE"


# ---------------------------------------------------------------------------
# auto_detect_ingest wiring
# ---------------------------------------------------------------------------

def test_auto_detect_skips_legacy_scaffold_cards(tmp_path):
    from mamey.mode_b_receipt import auto_detect_ingest
    pkg = _make_pkg_with_register(tmp_path)
    jd = pkg / "judgment"
    jd.mkdir()
    (jd / "AS-XXX_BGC033_mode_b.md").write_text(_legacy_card())

    res = auto_detect_ingest(pkg)
    assert res["recorded"] == []
    assert any(bid == "BGC033" for bid, _ in res["skipped_structure_invalid"])
    reg = json.loads((pkg / "AS-XXX_judgment_register.json").read_text())
    assert reg["bgcs"]["BGC033"]["status"] == "PENDING"


def test_auto_detect_records_canonical_card(tmp_path):
    from mamey.mode_b_receipt import auto_detect_ingest
    pkg = _make_pkg_with_register(tmp_path)
    jd = pkg / "judgment"
    jd.mkdir()
    (jd / "AS-XXX_BGC033_mode_b.md").write_text(
        "<!-- MODE B: BGC033 | strain: AS-XXX | session: S-real | 2026-06-30 -->\n\n"
        + _full_card())

    res = auto_detect_ingest(pkg)
    assert "BGC033" in res["recorded"]
    assert res["skipped_structure_invalid"] == []


def test_auto_detect_force_structure_records_legacy_card(tmp_path):
    from mamey.mode_b_receipt import auto_detect_ingest
    pkg = _make_pkg_with_register(tmp_path)
    jd = pkg / "judgment"
    jd.mkdir()
    (jd / "AS-XXX_BGC033_mode_b.md").write_text(_legacy_card())

    res = auto_detect_ingest(pkg, force_structure=True)
    assert "BGC033" in res["recorded_with_structure_override"]
    assert res["skipped_structure_invalid"] == []


# ---------------------------------------------------------------------------
# ingest_receipt wiring
# ---------------------------------------------------------------------------

def test_ingest_receipt_skips_legacy_cards_in_batch(tmp_path):
    from mamey.mode_b_receipt import ingest_receipt
    pkg = _make_pkg_with_register(tmp_path)
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps({
        "schema_version": "mode-b-receipt-1.0",
        "strain_id": "AS-XXX",
        "session_id": "S-batch",
        "cards": [{"bgc_id": "BGC033", "mode_b_md": _legacy_card()}],
    }))
    res = ingest_receipt(pkg, receipt)
    assert res["recorded"] == []
    assert any(bid == "BGC033" for bid, _ in res["skipped_structure_invalid"])


def test_ingest_receipt_force_structure_records(tmp_path):
    from mamey.mode_b_receipt import ingest_receipt
    pkg = _make_pkg_with_register(tmp_path)
    receipt = tmp_path / "receipt.json"
    receipt.write_text(json.dumps({
        "schema_version": "mode-b-receipt-1.0",
        "strain_id": "AS-XXX",
        "session_id": "S-batch",
        "cards": [{"bgc_id": "BGC033", "mode_b_md": _legacy_card()}],
    }))
    res = ingest_receipt(pkg, receipt, force_structure=True)
    assert "BGC033" in res["recorded_with_structure_override"]
