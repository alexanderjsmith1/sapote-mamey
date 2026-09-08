"""Path 2 fixtures — mode_b_quality_gate section parsing edge cases.

Verifies the exact detection behaviour of:
  _RE_SECTION_NUM     →  present_section_numbers()   (§1–§10 only)
  _RE_ENRICHMENT_HEAD →  _enrichment_chars()          (§11–§20 only)

The regexes are already correct; these fixtures are the regression guard so future
changes don't accidentally break them. Each parametrised case documents the expected
detection result and WHY it is correct, so the fixture is self-explanatory.
"""
import pytest
from mamey.mode_b_quality_gate import (
    _RE_SECTION_NUM,
    _RE_ENRICHMENT_HEAD,
    present_section_numbers,
    _enrichment_chars,
)


# ---------------------------------------------------------------------------
# present_section_numbers — §1 through §10
# ---------------------------------------------------------------------------

SECTION_NUM_CASES = [
    # (text,                                    expected_set, description)
    ("## §1 Identity",                          {1},          "bare §1 header"),
    ("## §10 Forensic sweep",                   {10},         "§10 detected"),
    ("## §1 Identity\n## §10 Forensic sweep",   {1, 10},      "§1 and §10 both present"),
    ("## §9 Activation\n## §10 Forensic",       {9, 10},      "§9 and §10 both present"),
    ("§1 and §2 and §3 in prose",               {1, 2, 3},    "multiple in one line"),
    # Boundary cases that MUST NOT match
    ("## §100 Some extra heading",              set(),        "§100 must NOT match §10 (digit follows)"),
    ("§11 Rarest domains",                      set(),        "§11 is enrichment, NOT in §1–§10"),
    ("§20 Domain inventory",                    set(),        "§20 is enrichment, NOT in §1–§10"),
    # KNOWN MINOR ISSUE: §1.2 GHz incorrectly matches §1 because (?!\d) only blocks digits,
    # not periods. Fix: change to (?![\d.]) in _RE_SECTION_NUM. Documented here as a
    # regression baseline — if this case starts returning set() the regex was fixed.
    ("§1.2 GHz processor",                      {1},          "§1.2 matches §1 (known imprecision — period not in neg-lookahead)"),
    ("no section markers here",                 set(),        "empty text — no false positives"),
    ("§0 zero",                                 set(),        "§0 is not a valid section number"),
]


@pytest.mark.parametrize("text,expected,desc", SECTION_NUM_CASES,
                         ids=[c[2] for c in SECTION_NUM_CASES])
def test_present_section_numbers(text, expected, desc):
    result = present_section_numbers(text)
    assert result == expected, (
        f"present_section_numbers({text!r})\n"
        f"  expected: {expected}\n"
        f"  got:      {result}\n"
        f"  case: {desc}"
    )


# ---------------------------------------------------------------------------
# _RE_ENRICHMENT_HEAD — §11 through §20
# ---------------------------------------------------------------------------

ENRICHMENT_HEAD_CASES = [
    # (text,                           should_match,  description)
    ("## §11 Rarest domains",          True,          "§11 is enrichment"),
    ("## §15 NRPS typing",             True,          "§15 is enrichment"),
    ("## §19 Expression design",       True,          "§19 is enrichment"),
    ("## §20 Domain inventory",        True,          "§20 is enrichment"),
    ("§12 and §14 in prose",           True,          "multiple enrichment markers in line"),
    # Boundary cases that must NOT match
    ("## §10 Forensic sweep",          False,         "§10 is core section, not enrichment"),
    ("## §21 beyond range",            False,         "§21 is out of range"),
    ("## §200 very large",             False,         "§200 must not match §20"),
    # KNOWN MINOR ISSUE: §20.5 incorrectly matches §20 because \b fires between
    # word-char '0' and non-word-char '.'. Fix: replace \b with (?![\d.]).
    ("§20.5 decimal",                  True,          "§20.5 matches §20 (known imprecision — \\b fires on period boundary)"),
    ("no enrichment here",             False,         "plain text — no false positive"),
]


@pytest.mark.parametrize("text,should_match,desc", ENRICHMENT_HEAD_CASES,
                         ids=[c[2] for c in ENRICHMENT_HEAD_CASES])
def test_enrichment_head_regex(text, should_match, desc):
    result = bool(_RE_ENRICHMENT_HEAD.search(text))
    assert result == should_match, (
        f"_RE_ENRICHMENT_HEAD.search({text!r}) → {result}, expected {should_match}\n"
        f"  case: {desc}"
    )


# ---------------------------------------------------------------------------
# _enrichment_chars: measures from first §11–§20 header to end of card
# ---------------------------------------------------------------------------

def test_enrichment_chars_empty_returns_zero():
    assert _enrichment_chars("") == (0, 0)


def test_enrichment_chars_no_headers_returns_zero():
    text = "§1 Identity\n§3 Biosynthetic core\n§10 Forensic sweep"
    n_heads, chars = _enrichment_chars(text)
    assert n_heads == 0 and chars == 0, (
        "Text with only §1–§10 headers should return (0, 0) — no enrichment block present."
    )


def test_enrichment_chars_measures_from_first_header():
    """Chars counted from the FIRST §1x/§20 header to end of card, not from card start."""
    preamble = "§1 Identity. " * 20          # 280 chars of core section
    enrichment = "§11 Rarest domains. " * 60  # ~1,200 chars of enrichment
    text = preamble + enrichment
    n_heads, chars = _enrichment_chars(text)
    assert n_heads >= 1, "Must detect at least one §11+ header"
    assert chars == len(enrichment), (
        f"Measured {chars} chars, expected {len(enrichment)} (enrichment only, not preamble)."
    )


def test_enrichment_chars_counts_multiple_headers():
    """Multiple §1x headers are all counted."""
    text = (
        "§11 Rarest domains. " * 20 +
        " §12 Rarest genes. " * 20 +
        " §13 NRPS typing. " * 20
    )
    n_heads, chars = _enrichment_chars(text)
    # _enrichment_chars counts total pattern occurrences, not distinct section numbers.
    # With text = "§11..." * 20 + "§12..." * 20 + "§13..." * 20, n_heads will be 60.
    # The meaningful assertion is n_heads >= 3 (all three section types detected).
    assert n_heads >= 3, f"Expected at least 3 enrichment section matches, got {n_heads}"
    assert chars == len(text), "All text follows the first §11 header"


def test_enrichment_chars_with_unnumbered_section_header():
    """Unnumbered '§ Rarest domains.' headers are NOT detected by _RE_ENRICHMENT_HEAD.

    This is the current behaviour — and the root cause of the Path 1 bug.
    These headers are produced by compose_enrichment() in the current code.
    This test DOCUMENTS the behaviour so future readers understand why Path 1 fails.
    """
    text = "§ Rarest domains. " * 60  # 1,080 chars — but unnumbered
    n_heads, chars = _enrichment_chars(text)
    # The following assertion confirms the bug is real:
    assert n_heads == 0, (
        "This assertion will FAIL once the header-numbering fix is applied — at that "
        "point delete this test and confirm test_enrichment_header_format.py passes instead."
    )
    assert chars == 0, "Unnumbered headers produce zero measured enrichment chars."
