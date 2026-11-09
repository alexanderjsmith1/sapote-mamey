"""Every ingest route records a Mode B card COMPLETE only when its full identity is bound.

The card must carry one four-part header (strain / full node-or-contig / region /
alias) that matches the package triage row. A missing header, a partial header, a
conflicting four-part header or a missing triage row is an identity hold on all three
routes (receipt, single card, auto-detect). ``--force-structure`` overrides structure
findings only, never identity. Ruling 479's legacy short-node header stays accepted.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from mamey import mode_b_receipt as R
from mamey.judgment_store import init_register, read_register
from tests._modeb_card_fixtures import valid_modeb_card_stub

STRAIN = "PUBLIC-1"
BGC = "BGC001"
CONTIG = "NODE_5_length_8000_cov_3.25"
SHORT = "NODE_5_length_8000_cov_3"

FULL = valid_modeb_card_stub(BGC, node=CONTIG, strain_id=STRAIN)
BODY = FULL.split("\n", 2)[2]
CARDS = {
    "no_header": BODY,
    "strain_alias_only": f"# Mode B — {STRAIN} / {BGC}\n\n" + BODY,
    "wrong_region": f"# Mode B — {STRAIN} / {CONTIG} / region009 / {BGC}\n\n" + BODY,
}


def _pkg(tmp_path: Path, *, triage: bool = True) -> Path:
    pkg = tmp_path / STRAIN / "package"
    pkg.mkdir(parents=True)
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": STRAIN}), encoding="utf-8")
    init_register(pkg, strain_id=STRAIN, bgc_ids=[BGC])
    rows = ("BGC_ID,Contig,Node_ID,antiSMASH_Region\n"
            f"{BGC},{CONTIG},{SHORT},region001\n")
    (pkg / f"{STRAIN}_2_inventory.csv").write_text(rows, encoding="utf-8")
    if triage:
        (pkg / f"{STRAIN}_4_triage_board.csv").write_text(rows, encoding="utf-8")
    return pkg


def _ingest(route: str, pkg: Path, tmp_path: Path, card: str, force: bool) -> bool:
    """Run one route; return True when the card was recorded."""
    if route == "receipt":
        rcpt = tmp_path / "receipt.json"
        rcpt.write_text(json.dumps({"strain_id": STRAIN, "session_id": "s",
                                    "cards": [{"bgc_id": BGC, "mode_b_md": card}]}))
        s = R.ingest_receipt(pkg, rcpt, force_structure=force)
        return bool(s["recorded"] or s["recorded_with_structure_override"])
    if route == "card":
        path = tmp_path / f"{STRAIN}_{BGC}_mode_b.md"
        path.write_text(card, encoding="utf-8")
        s = R.ingest_one_card(pkg, path, force_structure=force)
        return s["status"].startswith("RECORDED")
    (pkg / "judgment").mkdir(exist_ok=True)
    (pkg / "judgment" / f"{STRAIN}_{BGC}_mode_b.md").write_text(card, encoding="utf-8")
    s = R.auto_detect_ingest(pkg, force_structure=force)
    return bool(s["recorded"] or s["recorded_with_structure_override"])


ROUTES = ["receipt", "card", "auto"]


@pytest.mark.parametrize("force", [False, True])
@pytest.mark.parametrize("route", ROUTES)
@pytest.mark.parametrize("case", sorted(CARDS))
def test_unbound_card_is_never_recorded(tmp_path, route, case, force):
    pkg = _pkg(tmp_path)
    assert not _ingest(route, pkg, tmp_path, CARDS[case], force)
    assert read_register(pkg)["bgcs"][BGC]["status"] == "PENDING"


@pytest.mark.parametrize("force", [False, True])
@pytest.mark.parametrize("route", ROUTES)
def test_no_triage_row_holds_even_a_full_header(tmp_path, route, force):
    pkg = _pkg(tmp_path, triage=False)
    assert not _ingest(route, pkg, tmp_path, FULL, force)
    assert read_register(pkg)["bgcs"][BGC]["status"] == "PENDING"


@pytest.mark.parametrize("route", ROUTES)
def test_bound_full_header_is_recorded(tmp_path, route):
    pkg = _pkg(tmp_path)
    assert _ingest(route, pkg, tmp_path, FULL, False)
    assert read_register(pkg)["bgcs"][BGC]["status"] == "COMPLETE"


@pytest.mark.parametrize("route", ROUTES)
def test_legacy_short_node_header_still_recorded_with_note(tmp_path, route):
    pkg = _pkg(tmp_path)
    card = valid_modeb_card_stub(BGC, node=SHORT, strain_id=STRAIN)
    assert _ingest(route, pkg, tmp_path, card, False)
    assert read_register(pkg)["bgcs"][BGC]["status"] == "COMPLETE"


def test_hold_reason_is_reported_on_the_receipt_route(tmp_path):
    pkg = _pkg(tmp_path, triage=False)
    rcpt = tmp_path / "receipt.json"
    rcpt.write_text(json.dumps({"strain_id": STRAIN,
                                "cards": [{"bgc_id": BGC, "mode_b_md": CARDS["no_header"]}]}))
    (row,) = R.ingest_receipt(pkg, rcpt, force_structure=True)["skipped_identity_mismatch"]
    assert row["reason"] == R.CARD_IDENTITY_UNBOUND
    assert row["identity_hold"] == "NO_TRIAGE_ROW"
