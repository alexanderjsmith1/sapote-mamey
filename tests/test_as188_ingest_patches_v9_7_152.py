"""Tests for v9.7.152 patches:
  1. auto_detect_ingest surfaces near-miss (misnamed) cards instead of skipping silently.
  2. lint_card_in_package lints with the same BGC context the ingest gate uses,
     closing the standalone-vs-ingest conditional-section gap.
"""
import json
import re
from pathlib import Path

from mamey.mode_b_receipt import auto_detect_ingest, lint_card_in_package
from mamey.modeb_structure_gate import lint_card


def _mk_pkg(tmp: Path) -> Path:
    (tmp / "manifest.json").write_text('{"strain_id":"AS-901"}')
    reg = {
        "schema_version": "1.0", "strain_id": "AS-901", "total_bgcs": 43,
        "complete_bgcs": 0, "completion_pct": 0.0, "judgment_status": "IN_PROGRESS",
        "last_sapote_session": None,
        "bgcs": {f"BGC{n:03d}": {"status": "PENDING", "mode_b_file": None,
                                 "session_id": None, "timestamp": None}
                 for n in range(1, 44)},
    }
    (tmp / "AS-901_judgment_register.json").write_text(json.dumps(reg))
    (tmp / "judgment").mkdir()
    return tmp


def test_misnamed_card_is_flagged(tmp_path):
    pkg = _mk_pkg(tmp_path)
    (pkg / "judgment" / "BGC013_mode_b.md").write_text(
        "<!-- MODE B: BGC013 -->\n# Mode B — BGC013\n## §1 Identity and node/region\nx\n")
    s = auto_detect_ingest(pkg)
    assert ("BGC013", "BGC013_mode_b.md") in s["skipped_misnamed"]
    assert "BGC013" not in s["recorded"]


def test_junk_filename_not_flagged(tmp_path):
    pkg = _mk_pkg(tmp_path)
    (pkg / "judgment" / "notes_mode_b.md").write_text("# random\n")
    s = auto_detect_ingest(pkg)
    assert s["skipped_misnamed"] == []


def test_wrapper_missing_file_fails_open(tmp_path):
    pkg = _mk_pkg(tmp_path)
    r = lint_card_in_package(pkg, "BGC001")
    assert any(x.get("code") == "BAD_PATH" for x in r)


def test_wrapper_catches_required_conditional_section(tmp_path):
    """A RiPP card missing §21/§22 passes bare lint_card but the wrapper
    (with triage context) flags MISSING_CONDITIONAL_SECTION, matching ingest."""
    pkg = _mk_pkg(tmp_path)
    (pkg / "AS-901_4_triage_board.csv").write_text(
        "BGC_ID,Products,Boundary,Node_ID,antiSMASH_Region,Lead_tier_auto\n"
        "BGC015,RiPP; crocagin; saccharide,Interior,NODE_20,region002,Inventory\n")
    card = ("<!-- MODE B: BGC015 -->\n# Mode B — BGC015\n"
            + "".join(f"## §{i} S{i}\nbody\n" for i in range(1, 21))
            + "## §27 Self-resistance assessment\nbody\n"
            + "## §28 Evidence provenance ledger\nbody\n"
            + "## §30 Experimental decision tree\nbody\n")
    assert not [x for x in lint_card(card) if x.get("severity") == "ERROR"
                and x.get("code") == "MISSING_CONDITIONAL_SECTION"]
    e = [x for x in lint_card_in_package(pkg, "BGC015", card_md=card)
         if x.get("severity") == "ERROR"]
    assert any(x.get("code") == "MISSING_CONDITIONAL_SECTION" for x in e)
