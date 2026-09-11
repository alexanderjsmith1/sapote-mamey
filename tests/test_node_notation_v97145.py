"""Tests for node notation validator — v9.7.145."""
from mamey.validators.node_notation import (
    validate_node_citations,
    has_node_citation_violations,
)


def test_bgc_with_node_citation_passes():
    text = """## §1 — Identity
BGC028 (NODE_32_length_60747_cov_53 · region001) is the highest-priority lead.
"""
    assert validate_node_citations(text) == []
    assert not has_node_citation_violations(text)


def test_bgc_without_node_citation_fails():
    text = """## §1 — Identity
BGC028 is the highest-priority lead.
"""
    violations = validate_node_citations(text)
    assert len(violations) == 1
    assert violations[0].bgc_id == "BGC028"


def test_second_mention_in_section_passes_without_citation():
    text = """## §1 — Identity
BGC028 (NODE_32 · region001) is the lead.
BGC028 is also covered in the megacluster section.
"""
    assert validate_node_citations(text) == []


def test_multiple_bgcs_first_mention_each():
    text = """## §2 — Partners
BGC046 (NODE_82 · region001) and BGC011 are both upstream fragments.
BGC002 (NODE_105 · region001) is the loading module.
"""
    violations = validate_node_citations(text)
    # BGC011 has no node citation at first mention in this section
    assert any(v.bgc_id == "BGC011" for v in violations)
    assert all(v.bgc_id != "BGC046" for v in violations)
    assert all(v.bgc_id != "BGC002" for v in violations)


def test_new_section_resets_seen_set():
    text = """## §1 — First section
BGC028 (NODE_32 · region001) mentioned here.
## §2 — Second section
BGC028 is mentioned again without citation.
"""
    violations = validate_node_citations(text)
    # BGC028 first mention in §2 has no citation
    assert any(v.bgc_id == "BGC028" for v in violations)


def test_short_node_form_accepted():
    text = """## §1 — Identity
BGC046 (NODE_82 · region001) is the central elongation contig.
"""
    assert validate_node_citations(text) == []


def test_empty_text_passes():
    assert validate_node_citations("") == []


def test_text_without_bgc_ids_passes():
    assert validate_node_citations("## §1 — Intro\nNo BGC IDs mentioned here.") == []
