"""Regression: tools/deliverable_citation_audit.py's §15 pre-delivery citation gate must fire on
a lowercase/mixed-case BGC citation exactly as it does on the canonical uppercase form.

Fails against the pristine .394 file: `_ANY_BGC_RE` was case-sensitive, so a compiled deliverable
citing a BGC only as "bgc039" (lowercase) produced ZERO findings at all -- not even the milder
NO_PROVENANCE_TAGS finding -- completely bypassing the BLOCK-severity BARE_IN_PROSE check this
tool exists specifically to enforce (per its own docstring: the check that catches "the actual
shipping incident" that a §1-§30-only Mode B check misses). Same bypass class already fixed at
.383/.384 in bgc_citation_gate.py / sapote_hooks/bgc_citation_node_guard.py, and this session in
the sibling modeb_structure_gate.py MISSING_LOCATOR check.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import deliverable_citation_audit as dca  # noqa: E402


def test_lowercase_bare_citation_produces_the_same_block_finding_as_uppercase():
    lower = "The compound bgc039 shows strong activity."
    upper = "The compound BGC039 shows strong activity."

    findings_upper, _, _ = dca.scan_text(upper, source="test.md")
    findings_lower, _, _ = dca.scan_text(lower, source="test.md")

    upper_codes = {f["code"] for f in findings_upper}
    assert "BARE_IN_PROSE" in upper_codes, "sanity: the uppercase case must already BLOCK"

    lower_codes = {f["code"] for f in findings_lower}
    assert "BARE_IN_PROSE" in lower_codes, (
        "a lowercase 'bgc039' bare citation produced no BARE_IN_PROSE finding at all -- the "
        "case-sensitive regex let it bypass the §15 shipping BLOCK gate entirely"
    )


def test_mixed_case_citation_with_a_real_locator_is_not_falsely_blocked():
    # _LOCATOR_INLINE_RE already had re.IGNORECASE before this fix -- confirms the _ANY_BGC_RE
    # fix doesn't introduce a NEW false-positive on a correctly-cited lowercase mention.
    card = "The compound Bgc039 (node_5 · region001) is well characterized."
    findings, _, _ = dca.scan_text(card, source="test.md")
    codes = {f["code"] for f in findings}
    assert "BARE_IN_PROSE" not in codes, (
        "a mixed-case citation WITH a valid locator was still flagged BARE_IN_PROSE"
    )
