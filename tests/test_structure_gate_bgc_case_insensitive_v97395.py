"""Regression: modeb_structure_gate.py's MISSING_LOCATOR citation lint (item #59) must fire on a
lowercase/mixed-case BGC citation exactly as it does on the canonical uppercase form.

Fails against the pristine .394 file: `_ANY_BGC_RE`/`_LOCATOR_BGC_RE` were case-sensitive, so a
card that cites a BGC only as "bgc039" (never "BGC039") never entered the `mentioned` set at all
-- the check silently never fired for it, the same case-insensitivity bypass already fixed in the
sibling bgc_citation_gate.py / sapote_hooks/bgc_citation_node_guard.py gates this session.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mamey import modeb_structure_gate as gate  # noqa: E402


def _codes(card_md: str) -> set[str]:
    return {f["code"] for f in gate._citation_findings(card_md)}


def test_lowercase_bare_citation_is_flagged_same_as_uppercase():
    lower = "Section 4. The compound bgc039 was studied but no locator is given anywhere."
    upper = "Section 4. The compound BGC039 was studied but no locator is given anywhere."
    assert "MISSING_LOCATOR" in _codes(upper), "sanity: the uppercase case must already be flagged"
    assert "MISSING_LOCATOR" in _codes(lower), (
        "a lowercase 'bgc039' citation was not flagged -- the case-sensitive regex let it "
        "bypass the MISSING_LOCATOR check entirely"
    )


def test_mixed_case_citation_with_a_real_locator_is_still_recognized_as_located():
    # A card that DOES give a locator, but in mixed case, must not be falsely flagged as missing
    # one -- proves the fix also closes the matching gap on the _LOCATOR_BGC_RE side, not just
    # _ANY_BGC_RE.
    card = "Section 4. The compound Bgc039 (node_5 · region001) is well characterized."
    assert "MISSING_LOCATOR" not in _codes(card), (
        "a mixed-case citation WITH a locator was still flagged as missing one -- "
        "_LOCATOR_BGC_RE didn't recognize the mixed-case locator form"
    )
