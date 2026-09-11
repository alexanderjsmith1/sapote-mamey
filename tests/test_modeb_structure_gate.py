"""test_modeb_structure_gate.py — tests for the W9 §1–§30 structural validator.

The motivating bug: BGC033 case in v9.7.150 where a chat authored a card
against the historical §1 Identity / §2 Assembly / §9 Activation /
§10 Forensic sweep / §11–§20 enrichment scaffold instead of the canonical
§1–§30 contract. The validator must catch that pattern at ingest time.

All fixtures use AS-XXX.
"""
from __future__ import annotations
import pytest


def _full_card(*, drop=None, extras=None, title_overrides=None):
    """Build a synthetic well-formed card with all §1–§20 + §28 + §30
    sections. `drop` removes named section numbers, `extras` appends extra
    section blocks, `title_overrides` swaps titles."""
    drop = set(drop or [])
    extras = extras or []
    overrides = title_overrides or {}
    titles = [
        (1, "Identity and node/region"),
        (2, "Why this BGC was selected"),
        (3, "Boundary and assembly status"),
        (4, "Gene-by-gene interpretation"),
        (5, "Core biosynthetic logic"),
        (6, "Tailoring and maturation logic"),
        (7, "Transport, resistance, and regulation"),
        (8, "Comparator/KCB interpretation"),
        (9, "Alternative hypotheses"),
        (10, "Fragmentation and co-capture risks"),
        (11, "Product-family interpretation"),
        (12, "Bee/microbe ecological interpretation"),
        (13, "Antibacterial/antifungal relevance"),
        (14, "What cannot be claimed"),
        (15, "Missing evidence"),
        (16, "BLASTP/HMMER next steps"),
        (17, "LC-MS / fermentation implications"),
        (18, "Figure/locus-map notes"),
        (19, "Final Mode B judgement"),
        (20, "Next actions"),
        (28, "Evidence provenance ledger"),
        (30, "Experimental decision tree"),
    ]
    out = ""
    for n, t in titles:
        if n in drop:
            continue
        t = overrides.get(n, t)
        out += f"## §{n} {t}\n\nBody for §{n}.\n\n"
    for n, t in extras:
        out += f"## §{n} {t}\n\nBody for §{n}.\n\n"
    return out


# v9.7.364: the contract gained the §31-§48 OPTIONAL extension tier. The invariant these tests
# protect is 'the §1-§30 required core did not change', NOT 'the file has exactly 30 rows' — the
# latter would block every future extension. Pinned to the core instead.
def test_contract_loads_and_has_30_sections():
    from mamey.modeb_structure_gate import load_contract
    c = load_contract()
    assert c["schema_version"] == "modeb_corrective_full48_v1"  # v9.7.364: 48-row contract (Codex #7)
    nums = sorted(s["number"] for s in c["sections"])
    assert nums[:30] == list(range(1, 31))          # §1-§30 core intact
    assert nums == sorted(set(nums))                 # no duplicates in the extension
    # §28 and §30 always required
    by_n = {s["number"]: s for s in c["sections"]}
    assert by_n[28]["required"] == "always"
    assert by_n[30]["required"] == "always"
    # §21, §22 conditional on is_ripp
    assert by_n[21]["required"] == "conditional"
    assert by_n[21]["condition_key"] == "is_ripp"


def test_well_formed_card_with_minimal_context_passes():
    """A complete §1–§20 + §28 + §30 card with a context that triggers no
    conditional sections should pass."""
    from mamey.modeb_structure_gate import lint_card
    card = _full_card()
    # Context that triggers no conditional sections
    ctx = {"products": "NRPS", "kcb_top": "actinomycin", "ab_score": 0,
           "af_score": 0, "lead_tier_auto": "MEDIUM"}
    findings = lint_card(card, bgc_context=ctx)
    errs = [f for f in findings if f["severity"] == "ERROR"]
    assert errs == [], f"unexpected errors: {errs}"


def test_bgc033_legacy_scaffold_caught():
    """The exact BGC033 failure mode: a card with §2 Assembly, §9 Activation,
    §10 Forensic sweep, §11 Enrichment etc."""
    from mamey.modeb_structure_gate import lint_card
    bad = (
        "## §1 Identity\nbody\n\n"
        "## §2 Assembly\nbody\n\n"
        "## §9 Activation\nbody\n\n"
        "## §10 Forensic sweep\nbody\n\n"
        "## §11 Enrichment\nbody\n\n"
    )
    findings = lint_card(bad, bgc_context={"products": "NRPS"})
    codes = [f["code"] for f in findings]
    # Legacy scaffold detection fires
    assert "LEGACY_SCAFFOLD_TITLE" in codes
    # Many missing required sections
    missing = [f for f in findings
               if f["code"] == "MISSING_REQUIRED_SECTION"]
    assert len(missing) >= 10
    # §28 + §30 specifically called out
    missing_nums = {f["section"] for f in missing}
    assert 28 in missing_nums
    assert 30 in missing_nums


def test_missing_28_and_30_are_errors():
    from mamey.modeb_structure_gate import lint_card
    card = _full_card(drop=[28, 30])
    findings = lint_card(card, bgc_context={"products": "NRPS"})
    missing = {f["section"] for f in findings
               if f["code"] == "MISSING_REQUIRED_SECTION"}
    assert missing == {28, 30}


def test_conditional_ripp_section_required_when_ripp():
    """For a RiPP BGC, §21 + §22 become mandatory."""
    from mamey.modeb_structure_gate import lint_card
    card = _full_card()  # no §21/§22
    ctx = {"products": "RiPP-like", "lead_tier_auto": "MEDIUM"}
    findings = lint_card(card, bgc_context=ctx)
    missing_cond = {f["section"] for f in findings
                    if f["code"] == "MISSING_CONDITIONAL_SECTION"}
    assert 21 in missing_cond
    assert 22 in missing_cond


def test_conditional_self_resistance_required_for_antimicrobial():
    from mamey.modeb_structure_gate import lint_card
    card = _full_card()  # no §27
    ctx = {"products": "NRPS", "ab_score": 60, "lead_tier_auto": "MEDIUM",
           "kcb_top": "actinomycin"}
    findings = lint_card(card, bgc_context=ctx)
    missing_cond = {f["section"] for f in findings
                    if f["code"] == "MISSING_CONDITIONAL_SECTION"}
    assert 27 in missing_cond


def test_title_mismatch_caught():
    from mamey.modeb_structure_gate import lint_card
    # §7 expected: "Transport, resistance, and regulation"
    # Drop §7 from the auto-build, then add it with a wrong title
    base = _full_card(title_overrides={7: "Manual BLASTP evidence"})
    findings = lint_card(base, bgc_context={"products": "NRPS"})
    mismatch = [f for f in findings if f["code"] == "TITLE_MISMATCH"]
    assert any(f["section"] == 7 for f in mismatch), (
        f"§7 title mismatch not caught: {[f['code'] for f in findings]}"
    )


def test_out_of_order_caught():
    from mamey.modeb_structure_gate import lint_card
    # §1, §3, §2, ... — out of order
    card = (
        "## §1 Identity and node/region\nbody\n\n"
        "## §3 Boundary and assembly status\nbody\n\n"
        "## §2 Why this BGC was selected\nbody\n\n"
    )
    findings = lint_card(card)
    assert any(f["code"] == "OUT_OF_ORDER" for f in findings)


def test_duplicate_section_warned():
    from mamey.modeb_structure_gate import lint_card
    card = _full_card() + "\n## §1 Identity and node/region\n\nextra dup.\n\n"
    findings = lint_card(card, bgc_context={"products": "NRPS"})
    assert any(f["code"] == "DUPLICATE_SECTION" for f in findings)


def test_empty_card_caught():
    from mamey.modeb_structure_gate import lint_card
    findings = lint_card("", bgc_context={"products": "NRPS"})
    assert findings[0]["code"] == "EMPTY_CARD"


def test_no_headings_caught():
    from mamey.modeb_structure_gate import lint_card
    findings = lint_card("Just prose. No headings whatsoever.\n",
                          bgc_context={"products": "NRPS"})
    assert findings[0]["code"] == "NO_HEADINGS_DETECTED"


def test_heading_form_tolerance():
    """The validator tolerates different markdown heading levels and the
    `## §N Title` vs `## §N — Title` vs `## N. Title` variants."""
    from mamey.modeb_structure_gate import extract_section_titles
    variants = [
        "## §1 Identity and node/region",
        "### §1 — Identity and node/region",
        "## §1: Identity and node/region",
        "## 1. Identity and node/region",
        "## Section 1 — Identity and node/region",
    ]
    for v in variants:
        out = extract_section_titles(v + "\n\nbody\n")
        assert len(out) == 1, f"failed to parse: {v}"
        n, t = out[0]
        assert n == 1
        assert "Identity" in t


def test_conditional_section_without_context_is_warn_not_error():
    """When no BGC context is supplied, missing conditional sections
    become WARN-only — the validator can't tell if they apply."""
    from mamey.modeb_structure_gate import lint_card
    card = _full_card()  # no §21–§27/§29
    findings = lint_card(card, bgc_context=None)
    # No ERRORs for conditional sections
    cond_errs = [f for f in findings
                 if f["code"] == "MISSING_CONDITIONAL_SECTION"]
    assert cond_errs == []
    # But warnings for each
    cond_warns = [f for f in findings
                  if f["code"] == "CONDITIONAL_SECTION_NOT_EVALUATED"]
    assert len(cond_warns) >= 8  # §21–§27, §29


def test_summarise_renders_human_text():
    from mamey.modeb_structure_gate import lint_card, summarise
    findings = lint_card(_full_card(),
                          bgc_context={"products": "NRPS",
                                       "kcb_top": "actinomycin",
                                       "ab_score": 0, "lead_tier_auto": "MEDIUM"})
    s = summarise(findings)
    assert "PASS" in s

    bad = lint_card("nothing here", bgc_context={"products": "NRPS"})
    s2 = summarise(bad)
    assert "ERROR" in s2


# --- BC2-405: a missing/malformed bundled contract must surface loudly, never silently ---------
# recognised_section_numbers() used to call load_contract() INSIDE a bare `except Exception: pass`
# -- catching exactly the FileNotFoundError/ValueError load_contract() is documented to raise on a
# missing or malformed bundle, and silently falling back to a hard-coded section-number range
# instead. load_contract()'s own docstring is explicit that callers "should NOT silently degrade
# to a hard-coded fallback; a missing contract is a bundle-integrity failure that should surface."
# lint_card() already calls load_contract() unguarded and raises correctly; this closed the one
# gap left open for a direct caller of the public extract_section_titles() (contract=None).


def test_recognised_section_numbers_propagates_a_missing_contract(monkeypatch):
    import mamey.modeb_structure_gate as gate

    def _raise(path=None):
        raise FileNotFoundError("contract missing (simulated)")

    monkeypatch.setattr(gate, "load_contract", _raise)
    with pytest.raises(FileNotFoundError, match="contract missing"):
        gate.recognised_section_numbers(None)


def test_extract_section_titles_propagates_a_missing_contract(monkeypatch):
    """The real live gap: extract_section_titles() is public API, callable directly without
    going through lint_card() first (see tests/test_modeb_reference_full48_exemplar_v9_7_372.py).
    It must not silently mis-parse against a guessed fallback range when the bundled contract
    cannot be loaded."""
    import mamey.modeb_structure_gate as gate

    def _raise(path=None):
        raise ValueError("contract malformed (simulated)")

    monkeypatch.setattr(gate, "load_contract", _raise)
    with pytest.raises(ValueError, match="contract malformed"):
        gate.extract_section_titles("## 1 Identity\n", contract=None)


def test_recognised_section_numbers_still_falls_back_for_a_malformed_supplied_contract():
    """The narrower, still-legitimate fallback case: a caller passes an already-loaded
    `contract` dict directly (bypassing load_contract() entirely) and that dict turns out to be
    malformed. This is the caller's own input, not a bundle-integrity failure, so the documented
    hard-coded fallback still applies here."""
    from mamey.modeb_structure_gate import recognised_section_numbers, _RECOGNISED_FALLBACK_MAX

    malformed = {"sections": "not-a-list-of-dicts"}
    nums = recognised_section_numbers(malformed)
    assert nums == set(range(1, _RECOGNISED_FALLBACK_MAX + 1))


def test_recognised_section_numbers_unaffected_when_contract_loads_fine():
    """No regression: the ordinary path (bundled contract present and valid) is unchanged --
    load_contract() is simply called one line earlier, outside the try, not removed."""
    from mamey.modeb_structure_gate import recognised_section_numbers, load_contract

    nums_explicit = recognised_section_numbers(load_contract())
    nums_default = recognised_section_numbers(None)
    assert nums_explicit == nums_default
    assert 1 in nums_default and 30 in nums_default
