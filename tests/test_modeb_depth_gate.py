"""test_modeb_depth_gate.py — depth-floor checks for modeb_structure_gate (v9.7.162).

Motivating failure: AS-696 top-8 (v9.7.161) — cards whose headings were present
but whose bodies were ~1-2 sentences each, ~10x under the depth standard, passed
structurally because the gate had no body-length notion. These tests lock in the
THIN_SECTION / THIN_CARD behavior and prove it does not false-positive on a deep
card or regress the structural checks.
"""
import mamey.modeb_structure_gate as g


def _all_headings(contract, body_for):
    lines = []
    for s in contract["sections"]:
        n = s["number"]
        lines.append(f"## §{n} {s['title']}")
        lines.append(body_for(n))
    return "\n\n".join(lines)


LARGE_CTX = {"total_domains": 68, "length_kb": 49.32, "boundary": "Interior"}
SMALL_CTX = {"total_domains": 10, "length_kb": 11.42, "boundary": "Edge"}


def test_depth_off_by_default_is_backcompat():
    """check_depth defaults False: no THIN findings, existing callers unaffected."""
    c = g.load_contract()
    card = _all_headings(c, lambda n: "x")
    findings = g.lint_card(card, bgc_context=LARGE_CTX)
    assert not any(f["code"].startswith("THIN") for f in findings)


def test_thin_card_flagged_when_depth_on():
    """A one-token-body card trips THIN_SECTION on heavy sections and THIN_CARD."""
    c = g.load_contract()
    card = _all_headings(c, lambda n: "short.")
    findings = g.lint_card(card, bgc_context=LARGE_CTX, check_depth=True)
    codes = [f["code"] for f in findings]
    assert "THIN_CARD" in codes
    assert codes.count("THIN_SECTION") >= 1
    # heavy sections (§4/§16/§17) must be among those flagged
    thin_secs = {f["section"] for f in findings if f["code"] == "THIN_SECTION"}
    assert thin_secs & {4, 16, 17}


def test_strict_depth_escalates_to_error():
    c = g.load_contract()
    card = _all_headings(c, lambda n: "short.")
    findings = g.lint_card(card, bgc_context=LARGE_CTX,
                           check_depth=True, strict_depth=True)
    thin = [f for f in findings if f["code"].startswith("THIN")]
    assert thin and all(f["severity"] == "ERROR" for f in thin)


def test_deep_card_passes_depth():
    """A genuinely deep card must NOT be flagged — no false positives.
    v9.7.164: fixtures reflect raised floors (ordinary 700 / heavy 1400 / card 20000)."""
    c = g.load_contract()
    heavy = "Gene-by-gene interpretation grounded in named fields. " * 30   # ~1600 chars > 1400
    normal = "Evidence-grounded interpretation, observed and inferred. " * 16  # ~900 chars > 700
    card = _all_headings(c, lambda n: heavy if n in (4, 16, 17) else normal)
    findings = g.lint_card(card, bgc_context=LARGE_CTX,
                           check_depth=True, strict_depth=True)
    assert not any(f["code"].startswith("THIN") for f in findings)


def test_small_bgc_gets_lower_floor():
    """A modest card that is THIN for a large BGC can pass for a small fragment.
    v9.7.227: floors lowered (padding fix) — body sized between the new small (150) and
    large (250) ordinary section floors so the small<large relationship still holds."""
    c = g.load_contract()
    body = "Evidence-grounded interpretation, observed. " * 5  # ~220 chars: >150, <250
    card = _all_headings(c, lambda n: body)
    large = g.lint_card(card, bgc_context=LARGE_CTX, check_depth=True)
    small = g.lint_card(card, bgc_context=SMALL_CTX, check_depth=True)
    large_thin = sum(1 for f in large if f["code"] == "THIN_SECTION")
    small_thin = sum(1 for f in small if f["code"] == "THIN_SECTION")
    assert small_thin < large_thin


def test_body_extraction_ignores_duplicate_and_keeps_first():
    card = "## §1 Identity\n\nfirst body\n\n## §1 Identity\n\nsecond body\n\n## §2 X\n\nb2"
    bodies = g.extract_section_bodies(card)
    assert bodies[1] == "first body"
    assert bodies[2] == "b2"


def test_structural_checks_unchanged_with_depth_on():
    """Depth is additive: a structurally broken card still gets its structural
    ERRORs, plus depth findings — depth never suppresses structure."""
    findings = g.lint_card("## §2 Assembly\n\nx", check_depth=True)
    assert any(f["code"] == "LEGACY_SCAFFOLD_TITLE" for f in findings)


# ---------------- v9.7.164: raised floors + N/A exemption ----------------

def test_marked_na_section_uses_small_floor():
    """A section explicitly reasoned as N/A is held to the small floor, not the large/heavy one."""
    c = g.load_contract()
    # §21/§22 marked N/A with real reasoning (~350 chars) should pass; large floor is 700
    na_body = ("Not applicable — this is a non-RiPP NRPS cluster, so a precursor mass ladder "
               "is not the right tool here. Recorded as considered-N/A rather than left blank "
               "to distinguish a reasoned non-application from a missing analysis section "
               "entirely. The class predicate (ribosomal precursor) is absent, so the ladder "
               "cannot be constructed and would be meaningless if forced; this is a deliberate, "
               "reasoned non-application and not an omission.")
    def body_for(n):
        if n in (21, 22):
            return na_body
        return "Evidence-grounded interpretation, observed and inferred. " * 16  # >700
    card = _all_headings(c, body_for)
    findings = g.lint_card(card, bgc_context=LARGE_CTX, check_depth=True)
    thin_secs = {f["section"] for f in findings if f["code"] == "THIN_SECTION"}
    assert 21 not in thin_secs and 22 not in thin_secs   # N/A exempt at small floor


def test_bare_na_oneliner_still_fails():
    """A bare 'N/A' with no reasoning is below even the small floor and still flags."""
    c = g.load_contract()
    def body_for(n):
        if n == 21:
            return "N/A"
        return "Evidence-grounded interpretation, observed and inferred. " * 16
    card = _all_headings(c, body_for)
    findings = g.lint_card(card, bgc_context=LARGE_CTX, check_depth=True)
    thin_secs = {f["section"] for f in findings if f["code"] == "THIN_SECTION"}
    assert 21 in thin_secs   # bare N/A does not escape the floor


def test_class_content_wired_into_lint_card():
    """check_class_content=True surfaces CONTENT_GAP for a card silent on its class biology."""
    c = g.load_contract()
    card = _all_headings(c, lambda n: "Evidence-grounded interpretation. " * 20)
    ctx = dict(LARGE_CTX, products="NRPS; thioamide-NRP")
    findings = g.lint_card(card, bgc_context=ctx, check_depth=True, check_class_content=True)
    assert any(f["code"] == "CONTENT_GAP" for f in findings)
