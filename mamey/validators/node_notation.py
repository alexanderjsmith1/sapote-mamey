"""Node notation validator — BGC IDs must cite NODE/contig at first mention (v9.7.145b).

Standing rule: every BGC ID (e.g. BGC028) must be accompanied by its node/contig
identifier at first mention in any section. Correct forms:
    BGC028 (NODE_32_length_60747_cov_53 · region001)   ← parenthesised full form
    BGC028 (NODE_32 · region001)                        ← parenthesised short form
    NODE_32                                             ← bare node reference (also accepted)

Fixes over v9.7.145a:
    - Section title is carried forward from heading blocks (was '[block_N]')
    - Bare NODE_XXX references (without parens) are now accepted
    - BGC IDs in ## headings are now checked (not silently skipped)
    - INLINE_CITATION_RE removed (was defined but unused)
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Matches BGC IDs: BGC followed by 3+ digits
BGC_ID_RE = re.compile(r"\bBGC\d{3,}\b", re.IGNORECASE)
# v9.7.395: was case-sensitive, so a lowercase/mixed-case citation ("bgc039") bypassed this
# file's own standing-rule enforcement entirely -- validate_node_citations() found zero
# violations for a lowercase BGC mention with no node/contig citation, while the identical
# uppercase mention correctly flagged one. Same bypass class fixed at .383/.384
# (bgc_citation_gate.py / sapote_hooks/bgc_citation_node_guard.py) and this session in
# modeb_structure_gate.py / deliverable_citation_audit.py -- the fifth instance found.
# NODE_CITATION_RE below already had re.IGNORECASE, so this closes the gap symmetrically.

# Matches a node/contig citation: parenthesised OR bare node reference
#   (NODE_32 · region001)    — parenthesised full
#   (NODE_32_length_...)     — parenthesised long form
#   NODE_32                  — bare, no parens
#   contig_105               — bare contig reference
NODE_CITATION_RE = re.compile(
    r"(?:"
    r"\(\s*(?:NODE_\d+|contig[_\s]\d+)[^)]*\)"   # parenthesised form
    r"|"
    r"\bNODE_\d+\b"                                # bare NODE_NNN reference
    r"|"
    r"\bcontig[_\s]\d+\b"                          # bare contig_NNN reference
    r")",
    re.IGNORECASE,
)

LOOKAHEAD_CHARS = 60    # characters after BGC ID to search for citation


@dataclass
class NodeNotationViolation:
    section: str        # actual heading text, not synthetic [block_N]
    bgc_id: str
    context: str        # surrounding text snippet
    char_offset: int


def _parse_sections(text: str) -> list[tuple[str, str]]:
    """Split text into (heading_title, body_text) pairs.

    The first pair has heading_title='' if text begins before any heading.
    Heading BGC IDs are checked within the heading text itself.
    """
    # Split on ## lines but keep the heading text
    parts = re.split(r"(^##[^\n]*)", text, flags=re.MULTILINE)
    sections: list[tuple[str, str]] = []
    current_heading = ""
    pending_body = parts[0] if parts else ""

    for part in parts[1:]:
        if part.startswith("##"):
            # Flush previous section
            if pending_body or current_heading:
                sections.append((current_heading, pending_body))
            current_heading = part.strip()
            pending_body = ""
        else:
            pending_body += part

    # Flush last section
    if pending_body or current_heading:
        sections.append((current_heading, pending_body))

    return sections


def validate_node_citations(text: str) -> list[NodeNotationViolation]:
    """Return list of violations: BGC IDs at first section mention lacking node citation.

    Only the first mention of each BGC ID per section is checked.
    Subsequent mentions in the same section are allowed without citation.
    BGC IDs in headings are also checked.

    A citation is valid only when the node/contig reference appears within
    LOOKAHEAD_CHARS characters immediately after THIS BGC ID, with no
    intervening BGC ID (to prevent sharing a neighbour's citation).
    """
    violations: list[NodeNotationViolation] = []
    sections = _parse_sections(text)

    for heading, body in sections:
        seen_in_section: set[str] = set()

        # Check BGC IDs in the heading itself
        for m in BGC_ID_RE.finditer(heading):
            bgc_id = m.group(0)
            if bgc_id in seen_in_section:
                continue
            seen_in_section.add(bgc_id)
            window_end = m.start() + len(bgc_id) + LOOKAHEAD_CHARS
            next_bgc = BGC_ID_RE.search(heading, m.end())
            if next_bgc and next_bgc.start() < window_end:
                window_end = next_bgc.start()
            window = heading[m.start(): window_end]
            if NODE_CITATION_RE.search(window):
                continue
            violations.append(NodeNotationViolation(
                section=heading or "[preamble]",
                bgc_id=bgc_id,
                context=heading[max(0, m.start()-20): m.start()+60].replace("\n", " "),
                char_offset=m.start(),
            ))

        # Check BGC IDs in the body
        for m in BGC_ID_RE.finditer(body):
            bgc_id = m.group(0)
            if bgc_id in seen_in_section:
                continue
            seen_in_section.add(bgc_id)

            # Clip window at next BGC ID to prevent citation sharing
            window_end = m.start() + len(bgc_id) + LOOKAHEAD_CHARS
            next_bgc = BGC_ID_RE.search(body, m.end())
            if next_bgc and next_bgc.start() < window_end:
                window_end = next_bgc.start()
            window = body[m.start(): window_end]

            if NODE_CITATION_RE.search(window):
                continue

            violations.append(NodeNotationViolation(
                section=heading or "[preamble]",
                bgc_id=bgc_id,
                context=body[max(0, m.start()-20): m.start()+60].replace("\n", " "),
                char_offset=m.start(),
            ))

    return violations


def has_node_citation_violations(text: str) -> bool:
    """Return True if any node citation violations are found."""
    return bool(validate_node_citations(text))
