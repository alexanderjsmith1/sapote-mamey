"""v9.7.410 (MODEB-GATE-410) — `_HEADING_RE` over-matched and REFUSED valid cards.

Round-6 re-audit on sealed .409 (`development/round6_v409/MODEB_GATE_REAUDIT_V409.md`,
Findings 1, 2 and 5) confirmed by execution that three ordinary authoring shapes made
strict `verify-modeb` refuse a structurally valid, in-order, depth-sufficient card:

  1. a numbered subsection `#### 4.1` / `### 4.2 ·` parsed as a second top-level §4
     (DUPLICATE_SECTION) and truncated the real §4 body at the subsection line
     (measured 1359 -> 78 chars) -> THIN_SECTION ERROR under strict depth. The
     project's own `wiki/User-Manual.md` writes subsections as `### N.M ·`.
  2. a `### 2.`-style numbered subheading inside §4 parsed as a top-level §2 ->
     ERROR OUT_OF_ORDER.
  3. a prose line opening `§12 ecological context ...` or `Section 5 genes were
     absent ...` parsed as a phantom heading -> OUT_OF_ORDER + THIN + DUPLICATE.
     Mode B cards cross-reference sections by number constantly.

One root cause, one fix (see `_iter_headings`): a captured number immediately followed
by `.<digit>` is a subsection, not a heading; and a heading that carries no explicit
`§`/`Section ` marker is admitted only when its title IS the canonical contract title.

The regression half of this file is the load-bearing half: genuine out-of-order,
genuine duplicate and genuine thin cards must STILL be caught.
"""
from __future__ import annotations

import pytest

from mamey.modeb_structure_gate import (
    extract_section_bodies,
    extract_section_titles,
    lint_card,
    load_contract,
)

# A small-BGC context: section floor 150 chars, heavy (§4/§16/§17) 300, card 3000.
CTX = {"products": "NRPS", "kcb_top": "BGC0000001", "novelty_auto": "LOW",
       "lead_tier_auto": "MEDIUM ACT", "n_genes": 12}

_FILLER = ("The locus is read from the bound antiSMASH record and every statement here "
           "is tied to that record; no compound identity, structure or bioactivity is "
           "asserted beyond the class-level hypothesis the evidence file carries. "
           "Domain content, gene coordinates and comparator scores are quoted as "
           "extracted, and the interpretation is deferred where the evidence stops. ")


def _sections():
    contract = load_contract()
    secs = [s for s in contract["sections"]
            if s.get("required") == "always" or s["number"] == 24]
    secs.sort(key=lambda s: s["number"])
    return secs


def _body(num: int) -> str:
    """Prose comfortably over the small-BGC floor for this section."""
    reps = 4 if num in (4, 16, 17) else 2
    return f"Interpretation for this section (§{num}) follows. " + _FILLER * reps


def build_card(section4_body: str | None = None,
               section5_body: str | None = None,
               overrides: dict[int, str] | None = None,
               duplicate_section4: bool = False,
               swap_4_and_5: bool = False) -> str:
    """A §1–§30-contract-valid card, with hooks for the adversarial variants."""
    overrides = overrides or {}
    parts: list[str] = ["# Mode B card — AS-XXX BGC001", ""]
    secs = _sections()
    if swap_4_and_5:
        nums = [s["number"] for s in secs]
        i4, i5 = nums.index(4), nums.index(5)
        secs = list(secs)
        secs[i4], secs[i5] = secs[i5], secs[i4]
    for s in secs:
        num = s["number"]
        parts.append(f"## §{num} — {s['title']}")
        parts.append("")
        if num == 4 and section4_body is not None:
            parts.append(section4_body)
        elif num == 5 and section5_body is not None:
            parts.append(section5_body)
        else:
            parts.append(overrides.get(num, _body(num)))
        parts.append("")
        if num == 4 and duplicate_section4:
            parts.append("## §4 — Gene-by-gene interpretation")
            parts.append("")
            parts.append(_body(4))
            parts.append("")
    return "\n".join(parts) + "\n"


def _errors(card: str) -> list[dict]:
    return [f for f in lint_card(card, bgc_context=CTX, check_depth=True,
                                 strict_depth=True) if f["severity"] == "ERROR"]


def _codes(card: str) -> set[str]:
    return {f["code"] for f in _errors(card)}


# ---------------------------------------------------------------------------
# Symptom 1 — numbered subsections `#### 4.1` / `### 4.2 ·`
# ---------------------------------------------------------------------------

_S4_INTRO = "The gene-by-gene walk is split by committed step.\n"
_S4_NUMBERED = (_S4_INTRO
                + "\n#### 4.1 ctg1_10 core NRPS\n\n" + _body(4)
                + "\n\n### 4.2 · Tailoring block\n\n" + _body(4) + "\n")
_S4_FLAT = _S4_INTRO + "\n" + _body(4) + "\n\n" + _body(4) + "\n"


def test_numbered_subsection_is_not_a_heading():
    assert extract_section_titles("#### 4.1 ctg1_10 core NRPS") == []
    assert extract_section_titles("### 4.2 · Tailoring block") == []
    assert extract_section_titles("## §10.5 sub-note") == []
    assert extract_section_titles("#### 4.1.2 deeper still") == []


def test_numbered_subsection_prose_counts_toward_parent_depth():
    """Finding 2: the subsection body must land in bodies[4], not vanish."""
    flat = extract_section_bodies(build_card(section4_body=_S4_FLAT))[4]
    numbered = extract_section_bodies(build_card(section4_body=_S4_NUMBERED))[4]
    # The subsection headings add characters, so numbered >= flat; the point is that
    # it is the same order of magnitude, not the 78-char stub the .409 gate produced.
    assert len(numbered) >= len(flat), (len(numbered), len(flat))
    assert "Tailoring block" in numbered
    assert numbered.count("Interpretation for this section (§4) follows.") == 2


def test_card_with_numbered_subsections_is_accepted():
    """The end-to-end .409 refusal: same §4 content, flat vs `#### 4.1`."""
    assert _errors(build_card(section4_body=_S4_FLAT)) == []
    assert _errors(build_card(section4_body=_S4_NUMBERED)) == []


def test_numbered_subsections_produce_no_duplicate_or_order_findings():
    nums = [n for n, _ in extract_section_titles(build_card(section4_body=_S4_NUMBERED))]
    assert nums == sorted(nums), nums
    assert nums.count(4) == 1, nums


# ---------------------------------------------------------------------------
# Symptom 2 — a `### 2.`-style numbered subheading inside §4
# ---------------------------------------------------------------------------

_S4_SUBHEAD = (_S4_INTRO
               + "\n### 1. Committed-step core\n\n" + _body(4)
               + "\n\n### 2. Tailoring and release\n\n" + _body(4) + "\n")


def test_markerless_subheading_is_not_a_section():
    assert extract_section_titles("### 2. Tailoring and release") == []
    assert extract_section_titles("### 1. Committed-step core") == []


def test_card_with_numbered_subheadings_is_accepted():
    card = build_card(section4_body=_S4_SUBHEAD)
    assert "OUT_OF_ORDER" not in _codes(card), _errors(card)
    assert _errors(card) == []


# ---------------------------------------------------------------------------
# Symptom 3 (Finding 5) — prose lines opening `§N` / `Section N`
# ---------------------------------------------------------------------------

_PROSE_REFS = [
    "§12 ecological context further supports the host-associated reading of this locus.",
    "Section 5 genes were absent from the comparator assembly, which limits the claim.",
    "Section 4 of the antiSMASH output lists three core biosynthetic genes.",
    "§7 and §8 overlap in function for this cluster.",
]


@pytest.mark.parametrize("line", _PROSE_REFS)
def test_prose_section_reference_is_not_a_heading(line):
    assert extract_section_titles(line) == [], line


def test_card_with_prose_section_references_is_accepted():
    s5 = _body(5) + "\n\n" + "\n\n".join(_PROSE_REFS) + "\n\n" + _body(5)
    card = build_card(section5_body=s5)
    assert _errors(card) == [], _errors(card)
    nums = [n for n, _ in extract_section_titles(card)]
    assert nums == sorted(nums), nums
    assert nums.count(12) == 1, nums
    # the real §5 body is no longer truncated at the cross-reference line
    assert len(extract_section_bodies(card)[5]) > 600


# ---------------------------------------------------------------------------
# REGRESSIONS — true positives must still be caught
# ---------------------------------------------------------------------------

def test_genuine_out_of_order_still_caught():
    card = build_card(swap_4_and_5=True)
    assert "OUT_OF_ORDER" in _codes(card), _errors(card)


def test_genuine_duplicate_still_caught():
    card = build_card(duplicate_section4=True)
    codes = {f["code"] for f in lint_card(card, bgc_context=CTX)}
    assert "DUPLICATE_SECTION" in codes, codes


def test_genuine_thin_section_still_caught():
    card = build_card(section4_body="Short.")
    assert "THIN_SECTION" in _codes(card), _errors(card)


def test_genuine_missing_section_still_caught():
    card = build_card()
    card = card.replace("## §9 — Alternative hypotheses", "## Alternative hypotheses")
    assert "MISSING_REQUIRED_SECTION" in _codes(card), _errors(card)


def test_title_mismatch_still_caught_for_marked_headings():
    card = build_card().replace("## §4 — Gene-by-gene interpretation",
                                "## §4 — Gene walk and notes")
    assert "TITLE_MISMATCH" in _codes(card), _errors(card)


def test_marked_headings_still_admitted_on_number_alone():
    """A `§`/`Section `-marked heading never needs the canonical title."""
    assert extract_section_titles("## §4 — Gene walk and notes") == [
        (4, "Gene walk and notes")]
    assert extract_section_titles("**§31 Region CDS census, invented**") == [
        (31, "Region CDS census, invented")]


def test_v9_7_152_bare_forms_preserved():
    """The historical bare-heading tolerance must not regress (Bug 2.1 test cases)."""
    cases = {
        "## §1 — Identity and node/region": (1, "Identity and node/region"),
        "### §5 — Core biosynthetic logic": (5, "Core biosynthetic logic"),
        "**§3 — Boundary and assembly status**": (3, "Boundary and assembly status"),
        "§7 — Transport, resistance, and regulation":
            (7, "Transport, resistance, and regulation"),
        "Section 4 — Gene-by-gene interpretation": (4, "Gene-by-gene interpretation"),
        "## 20 — Next actions": (20, "Next actions"),
        "§1 Identity and node/region": (1, "Identity and node/region"),
    }
    for heading, expected in cases.items():
        assert extract_section_titles(heading) == [expected], heading
    for line in ("1. BLASTP the locus.", "2. Re-score the lead tier.",
                 "10. Some action sentence here."):
        assert extract_section_titles(line) == [], line
