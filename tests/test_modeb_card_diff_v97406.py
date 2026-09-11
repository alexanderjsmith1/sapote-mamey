from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("modeb_card_diff", ROOT / "tools" / "modeb_card_diff.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def _write(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _fixture(tmp_path, *, card_node="NODE_OLD"):
    package = tmp_path / "package"
    package.mkdir()
    _write(package / "SYN-001_2_inventory.csv", [
        "BGC_ID", "Node_ID", "antiSMASH_Region", "Boundary", "Length_kb", "KCB_evidence_state",
    ], [{"BGC_ID": "BGC001", "Node_ID": "NODE_1", "antiSMASH_Region": "region002",
         "Boundary": "Interior", "Length_kb": "40", "KCB_evidence_state": "UNKNOWN_KCB"}])
    _write(package / "SYN-001_4_triage_board.csv", [
        "BGC_ID", "Protocluster_count", "Chemical_hybrid", "Overmerge_state",
    ], [{"BGC_ID": "BGC001", "Protocluster_count": "2", "Chemical_hybrid": "",
         "Overmerge_state": "OVERMERGE_SUSPECT"}])
    card = tmp_path / "stored.md"
    card.write_text(
        f"<!-- MODE B TEMPLATE | bgc: BGC001 | node: {card_node} | strain: SYN-001 | products: NRPS -->\n"
        "# Mode B\n\n## §1 Identity and node/region\nSYN-001 / NODE_OLD / region002 / BGC001\n",
        encoding="utf-8",
    )
    return package, card


def test_reports_sections_without_regenerating_card(tmp_path):
    package, card = _fixture(tmp_path)
    before = card.read_bytes()
    result = MODULE.compare(package, card)
    assert result["status"] == "STALE_DIFFERENCES_FOUND"
    assert result["full_identity"] == "SYN-001 / NODE_1 / region002 / BGC001"
    assert 1 in result["changed_sections"] and 28 in result["changed_sections"]
    assert any(item["kind"] == "CURRENT_OVERMERGE_STATE_NOT_RECORDED" for item in result["differences"])
    assert card.read_bytes() == before


def test_incomplete_card_identity_fails_closed(tmp_path):
    package, card = _fixture(tmp_path)
    card.write_text("## §1 Identity and node/region\nmissing metadata\n", encoding="utf-8")
    try:
        MODULE.compare(package, card)
    except MODULE.CardDiffHold as exc:
        assert exc.code == "CARD_EXACT_IDENTITY_HOLD"
    else:
        raise AssertionError("incomplete stored identity was accepted")
