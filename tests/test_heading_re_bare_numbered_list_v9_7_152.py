"""v9.7.152 — Bug 2.1: bare numbered list lines must not match _HEADING_RE.

A line like '1. BLASTP the locus.' inside §20 (or any) prose previously
satisfied _HEADING_RE because both prefix groups (markdown/bold and §/Section)
had empty alternatives, so it was mis-detected as a section heading. Fix
requires at least one prefix marker. See W9/FULL30 audit §2.1.

Note: the original audit predicted OUT_OF_ORDER + DUPLICATE_SECTION; the
observed symptom is actually a TITLE_MISMATCH -> MISSING cascade. This test
asserts the *root cause* (bare list no longer parsed as a heading), which is
symptom-independent.
"""
from mamey import modeb_structure_gate as gate


def test_bare_numbered_list_not_a_heading():
    for line in ("1. BLASTP the locus.",
                 "2. Re-score the lead tier.",
                 "10. Some action sentence here."):
        assert gate.extract_section_titles(line) == [], (
            f"bare numbered list line wrongly parsed as heading: {line!r}")


def test_legitimate_headings_still_match():
    cases = {
        "## §1 — Identity and node/region": (1, "Identity and node/region"),
        "### §5 — Core biosynthetic logic": (5, "Core biosynthetic logic"),
        "**§3 — Boundary and assembly status**": (3, "Boundary and assembly status"),
        "§7 — Transport, resistance, and regulation": (7, "Transport, resistance, and regulation"),
        "Section 4 — Gene-by-gene interpretation": (4, "Gene-by-gene interpretation"),
        "## 20 — Next actions": (20, "Next actions"),  # markdown header, no §
        "§1 Identity and node/region": (1, "Identity and node/region"),
    }
    for heading, expected in cases.items():
        got = gate.extract_section_titles(heading)
        assert got == [expected], f"{heading!r} -> {got}, expected [{expected}]"


def test_section20_card_with_action_list_detects_only_section20():
    card = (
        "## §20 — Next actions\n\n"
        "1. BLASTP ctg73_18 against a reference set.\n"
        "2. Re-score the lead tier.\n"
    )
    titles = gate.extract_section_titles(card)
    assert titles == [(20, "Next actions")], titles
    # and the list items must not produce TITLE_MISMATCH/OUT_OF_ORDER noise
    findings = gate.lint_card(card)
    codes = {f["code"] for f in findings}
    assert "OUT_OF_ORDER" not in codes, findings
    # the only TITLE_MISMATCH-like noise from list items must be absent:
    bad = [f for f in findings if f.get("section") in (1, 2)
           and f["code"] in ("TITLE_MISMATCH", "DUPLICATE_SECTION")]
    assert bad == [], f"list items still polluting findings: {bad}"
