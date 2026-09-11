"""test_locator_reconciliation_gate.py — STEP 2 (SM-P0-003): Header/locator reconciliation gate.

Tests the four spec fixtures:
  1. correct: card header matches triage row → PASS
  2. wrong_node: full node mismatch → Exit 1
  3. missing_region: incomplete four-part identity → UNPARSEABLE (Exit 1)
  4. unparseable: card header is garbled → UNPARSEABLE (Exit 1)

Also tests:
  - emit of header_locator_reconciliation.csv
  - regex parses BGC header correctly (spec regex)
  - Misanchor_Flag cross-reference column present in output
"""
import csv
import sys
import tempfile
from io import StringIO
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "tools"))

import locator_reconciliation as lr


# ── spec regex from the handoff ────────────────────────────────────────────────
import re
_RE_CARD_HEADER = re.compile(
    r'BGC(\d+)\s*\(([^·()\n]+?)(?:\s*·\s*(region\d+))?\)', re.I
)


# ── Fixture data ───────────────────────────────────────────────────────────────
TRIAGE_ROW_CORRECT = {
    "Strain": "AS-900",
    "BGC_ID": "BGC001",
    "Node_ID": "NODE_10_length_54129_cov_72",
    "antiSMASH_Region": "region001",
    "Assembly_Locator": "AS-900",
    "Products": "NRPS",
    "Boundary": "Edge",
    "Misanchor_Flag": "",
}

# Card with matching fields
CARD_CORRECT = """\
# Mode B — AS-900 / NODE_10_length_54129_cov_72 / region001 / BGC001
## BGC001 (AS-900 · region1)
**Node/Contig:** NODE_10_length_54129_cov_72 · Edge
**Products:** NRPS
"""

# Card with wrong node
CARD_WRONG_NODE = """\
# Mode B — AS-900 / NODE_99_length_1000_cov_10 / region001 / BGC001
## BGC001 (AS-900 · region1)
**Node/Contig:** NODE_99_length_1000_cov_10 · Edge
**Products:** NRPS
"""

# Card missing antiSMASH region (hard refusal)
CARD_MISSING_REGION = """\
# Mode B — AS-900 / NODE_10_length_54129_cov_72 / ? / BGC001
## BGC001 (AS-900)
**Node/Contig:** NODE_10_length_54129_cov_72 · Edge
**Products:** NRPS
"""

# Completely garbled header
CARD_UNPARSEABLE = """\
## [[ GARBLED_ENTRY ]] no BGC id here
Node info missing
"""


# ── 1. Correct card: zero mismatches ──────────────────────────────────────────
def test_correct_card_no_mismatches():
    errors = lr.reconcile_card(CARD_CORRECT, TRIAGE_ROW_CORRECT)
    assert errors == [], f"Expected no mismatches, got: {errors}"


# ── 2. Wrong node: contig mismatch detected ───────────────────────────────────
def test_wrong_node_detected():
    errors = lr.reconcile_card(CARD_WRONG_NODE, TRIAGE_ROW_CORRECT)
    fields = [e["field"] for e in errors]
    assert "Node_ID" in fields, f"Node_ID mismatch not detected; errors={errors}"


# ── 3. Missing region: fail closed ────────────────────────────────────────────
def test_missing_region_refused():
    """Missing region cannot be repaired from a secondary body field."""
    verdict = lr.reconcile_card_verdict(CARD_MISSING_REGION, TRIAGE_ROW_CORRECT)
    assert verdict["exit_code"] == 1
    assert verdict["status"] == "UNPARSEABLE"
    assert verdict["refusal_reason"] == "INCOMPLETE_EXACT_IDENTITY"


# ── 4. Unparseable: exit 1 ────────────────────────────────────────────────────
def test_unparseable_card_exit_1():
    verdict = lr.reconcile_card_verdict(CARD_UNPARSEABLE, TRIAGE_ROW_CORRECT)
    assert verdict["exit_code"] == 1, f"Unparseable should exit 1: {verdict}"
    assert verdict["status"] == "UNPARSEABLE"


# ── 5. Spec regex parses header correctly ─────────────────────────────────────
def test_spec_regex_parses_card_header():
    m = _RE_CARD_HEADER.search(CARD_CORRECT)
    assert m is not None, "Spec regex failed to match correct header"
    assert m.group(1) == "001"
    assert "AS-900" in m.group(2)
    assert m.group(3) == "region1"


def test_spec_regex_missing_region():
    m = _RE_CARD_HEADER.search(CARD_MISSING_REGION)
    assert m is not None, "Spec regex failed on missing-region header"
    assert m.group(3) is None  # region group absent


def test_spec_regex_unparseable():
    m = _RE_CARD_HEADER.search(CARD_UNPARSEABLE)
    assert m is None, "Spec regex should not match garbled header"


# ── 6. CSV output has Misanchor_Flag column ───────────────────────────────────
def test_reconciliation_csv_has_misanchor_flag_column():
    """The emitted header_locator_reconciliation.csv must include Misanchor_Flag."""
    rows = lr.reconcile_batch(
        [{"card_text": CARD_CORRECT, "triage_row": TRIAGE_ROW_CORRECT}]
    )
    assert rows, "reconcile_batch returned no rows"
    assert "Misanchor_Flag" in rows[0], \
        f"Misanchor_Flag missing from CSV row keys: {list(rows[0].keys())}"


# ── 7. Correct exit codes for all four fixtures ───────────────────────────────
def test_exit_code_correct():
    v = lr.reconcile_card_verdict(CARD_CORRECT, TRIAGE_ROW_CORRECT)
    assert v["exit_code"] == 0

def test_exit_code_wrong_node():
    v = lr.reconcile_card_verdict(CARD_WRONG_NODE, TRIAGE_ROW_CORRECT)
    assert v["exit_code"] == 1

def test_exit_code_missing_region():
    v = lr.reconcile_card_verdict(CARD_MISSING_REGION, TRIAGE_ROW_CORRECT)
    assert v["exit_code"] == 1

def test_exit_code_unparseable():
    v = lr.reconcile_card_verdict(CARD_UNPARSEABLE, TRIAGE_ROW_CORRECT)
    assert v["exit_code"] == 1


# ── 8. Bunny Hop: misanchor_flag set on mismatch card ─────────────────────────
def test_misanchor_flag_propagated_in_csv():
    """When triage row has a Misanchor_Flag, the CSV row must carry it."""
    row_with_flag = dict(TRIAGE_ROW_CORRECT, Misanchor_Flag="polyene_anchor_<4_PKS_KS(ks=1)")
    rows = lr.reconcile_batch(
        [{"card_text": CARD_CORRECT, "triage_row": row_with_flag}]
    )
    assert rows[0]["Misanchor_Flag"] == "polyene_anchor_<4_PKS_KS(ks=1)"



# ── reconcile_heading_only (v9.7.124 STEP 5: card-write-time, heading-only) ──────
def test_heading_only_pass():
    row = {"Strain": "AS-900", "BGC_ID": "BGC001", "Node_ID": "NODE_10",
           "antiSMASH_Region": "region001"}
    out = lr.reconcile_heading_only(
        "# Mode B — AS-900 / NODE_10 / region001 / BGC001\nbody", row)
    assert out["status"] == "PASS"


def test_heading_only_node_mismatch():
    row = {"Strain": "AS-900", "BGC_ID": "BGC001", "Node_ID": "NODE_10",
           "antiSMASH_Region": "region001"}
    out = lr.reconcile_heading_only(
        "# Mode B — AS-900 / NODE_99 / region001 / BGC001\nbody", row)
    assert out["status"] == "MISMATCH"
    assert out["errors"] and out["errors"][0]["field"] == "full_node_or_contig"


def test_heading_only_region_diff_is_conflict():
    row = {"Strain": "AS-900", "BGC_ID": "BGC001", "Node_ID": "NODE_10",
           "antiSMASH_Region": "region001"}
    out = lr.reconcile_heading_only(
        "# Mode B — AS-900 / NODE_10 / region009 / BGC001\nbody", row)
    assert out["status"] == "MISMATCH"
    assert out["refusal_reason"] == "IDENTITY_CONFLICT"


def test_heading_only_falls_back_to_contig():
    """A declared full Contig is the authoritative node component."""
    row = {"Strain": "AS-900", "BGC_ID": "BGC001", "Contig": "NODE_10",
           "antiSMASH_Region": "region001"}
    out = lr.reconcile_heading_only(
        "# Mode B — AS-900 / NODE_10 / region001 / BGC001\nbody", row)
    assert out["status"] == "PASS"


def test_heading_only_unparseable():
    row = {"Strain": "AS-900", "BGC_ID": "BGC001", "Node_ID": "NODE_10",
           "antiSMASH_Region": "region001"}
    out = lr.reconcile_heading_only("## Some heading with no BGC locator\nbody", row)
    assert out["status"] == "UNPARSEABLE"
    assert out["refusal_reason"] == "ZERO_EXACT_IDENTITIES"


def test_heading_only_region_absent_is_refused():
    row = {"Strain": "AS-900", "BGC_ID": "BGC001", "Node_ID": "NODE_10",
           "antiSMASH_Region": "region001"}
    out = lr.reconcile_heading_only("## BGC001 (NODE_10)\nbody", row)
    assert out["status"] == "UNPARSEABLE"
    assert out["refusal_reason"] == "ZERO_EXACT_IDENTITIES"
