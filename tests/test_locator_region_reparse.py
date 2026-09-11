"""P358-C01 — the §1 region fallback in tools/locator_reconciliation.py.

Regression guard for a defect found 2026-08-10: the current Mode-B emitter writes the
card title as `# Mode B — BGC007 (NODE_..) — AS-932` (node in parens, strain after an
em-dash, NO region), so `_RE_CARD_HEADER.group(3)` was None on every current-engine card
and `_parse_header_region()` returned None for all of them. The region is present in §1.
Two independent consumers (this tool and Codex's corpus audit) both took the locator from
the title and both went blind; the audit consequently reported 334 "duplicate" locator
groups that were actually distinct co-located loci.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import locator_reconciliation as L  # noqa: E402

CURRENT_TITLE_CARD = (
    "<!-- MODE B TEMPLATE | bgc: BGC007 | node: NODE_14_length_159225_cov_15 -->\n\n"
    "# Mode B — BGC007 (NODE_14_length_159225_cov_15) — AS-932\n\n"
    + ("filler line\n" * 400)  # push §1 well past the 500-char header window
    + "**BGC:** BGC007\n"
    "**Node / contig:** NODE_14_length_159225_cov_15\n"
    "**antiSMASH region:** region001\n"
)

OLD_TITLE_CARD = (
    "## BGC001 (NODE_9_length_1000_cov_5 · region004)\n\n"
    "**antiSMASH region:** region001\n"
)


def test_region_recovered_from_section_1_when_title_omits_it():
    assert L._parse_header_region(CURRENT_TITLE_CARD) == "region001"


def test_section_1_is_found_beyond_the_500_char_header_window():
    assert CURRENT_TITLE_CARD.find("**antiSMASH region:**") > 500
    assert L._parse_header_region(CURRENT_TITLE_CARD) == "region001"


def test_title_region_still_wins_when_present():
    """Backward compatibility: an old-format title carries authority over §1."""
    assert L._parse_header_region(OLD_TITLE_CARD) == "region004"


def test_returns_none_when_no_region_anywhere():
    assert L._parse_header_region("# Mode B — BGC001 (NODE_1_length_10_cov_1) — AS-1\n") is None
    assert L._parse_header_region("nothing here") is None


def test_legacy_title_region_is_secondary_not_authoritative():
    row = {"Strain": "AS-932", "BGC_ID": "BGC007",
           "Node_ID": "NODE_14_length_159225_cov_15", "antiSMASH_Region": "region002"}
    verdict = L.reconcile_heading_only(CURRENT_TITLE_CARD, row)
    assert verdict["status"] == "UNPARSEABLE"
    assert verdict["refusal_reason"] == "ZERO_EXACT_IDENTITIES"
    assert verdict["secondary_fields"]["card"]


def test_legacy_title_cannot_fill_four_part_identity_on_agreement():
    row = {"Strain": "AS-932", "BGC_ID": "BGC007",
           "Node_ID": "NODE_14_length_159225_cov_15", "antiSMASH_Region": "region001"}
    verdict = L.reconcile_heading_only(CURRENT_TITLE_CARD, row)
    assert verdict["status"] == "UNPARSEABLE"
    assert verdict["refusal_reason"] == "ZERO_EXACT_IDENTITIES"


def test_co_located_regions_are_distinguishable():
    """The 334-collision case: same node, three regions, must not collapse."""
    def card(region):
        return CURRENT_TITLE_CARD.replace("region001", region)
    got = [L._parse_header_region(card(r)) for r in ("region001", "region002", "region003")]
    assert got == ["region001", "region002", "region003"]
    assert len(set(got)) == 3
