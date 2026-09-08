"""Regression: mamey/validators/node_notation.py's standing-rule citation validator
(validate_node_citations) must fire on a lowercase/mixed-case BGC citation exactly as it does
on the canonical uppercase form.

Fails against the pristine .394 file: `BGC_ID_RE` was case-sensitive, so a lowercase mention
("bgc039") produced zero violations even with no node/contig citation anywhere -- silently
bypassing the standing rule this file's own docstring states ("every BGC ID must be accompanied
by its node/contig identifier at first mention"). Fifth instance of this bypass class found this
campaign (bgc_citation_gate.py / sapote_hooks/bgc_citation_node_guard.py at .383/.384;
modeb_structure_gate.py / deliverable_citation_audit.py this loop session).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mamey.validators import node_notation as nn  # noqa: E402


def test_lowercase_bgc_id_without_a_locator_is_flagged_same_as_uppercase():
    lower = "## Section 4\nThe compound bgc039 is discussed here without any locator."
    upper = "## Section 4\nThe compound BGC039 is discussed here without any locator."

    assert nn.validate_node_citations(upper), "sanity: the uppercase case must already flag"
    violations_lower = nn.validate_node_citations(lower)
    assert violations_lower, (
        "a lowercase 'bgc039' citation with no node/contig locator produced zero violations -- "
        "the case-sensitive regex let it bypass the standing-rule check entirely"
    )
    assert violations_lower[0].bgc_id.upper() == "BGC039"


def test_mixed_case_citation_with_a_real_node_reference_is_not_falsely_flagged():
    card = "## Section 4\nThe compound bgc039 (node_5 · region001) is well characterized."
    assert not nn.validate_node_citations(card), (
        "a lowercase citation WITH a valid node reference was still flagged as a violation"
    )
