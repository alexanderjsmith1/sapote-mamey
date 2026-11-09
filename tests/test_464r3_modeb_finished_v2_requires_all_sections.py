"""Ruling 9: a FINISHED_FULL50_CURRENT50_V2 card contains all 50 sections.

Before, an optional section (§31, §37, §39-§42, §44-§47) could be left out of a
finished card and the structure gate passed it. Now an absent section fails for
that profile, a NOT_APPLICABLE section needs a written reason, and a draft (no
finished-profile declaration) keeps the optional-section behavior.
"""
import argparse

from mamey.authored_verify import verify_modeb_command
from mamey.modeb_current50_v2 import header_line, load_contract
from mamey.modeb_structure_gate import lint_card

CONTRACT = load_contract("current50_v2")
RULE_CODES = {"MISSING_FINISHED_PROFILE_SECTION", "NOT_APPLICABLE_WITHOUT_REASON"}


def _card(*, finished=True, skip=(), bodies=None):
    bodies = bodies or {}
    lines = []
    if finished:
        lines.append(header_line("PUBLIC-1", "CP000001.1", "region001", "BGC001"))
    for s in CONTRACT["sections"]:
        n = s["number"]
        if n in skip:
            continue
        lines.append(f"## §{n} {s['title']}")
        lines.append(bodies.get(n, f"Locus-specific interpretation for section {n} of this region."))
        lines.append("")
    return "\n".join(lines) + "\n"


def _codes(md):
    return {f["code"] for f in lint_card(md, contract=CONTRACT)} & RULE_CODES


def test_contract_names_the_rule():
    rule = CONTRACT["finished_profile_section_rule"]
    assert rule["profile"] == "FINISHED_FULL50_CURRENT50_V2" and rule["all_sections_required"]


def test_finished_card_missing_optional_section_fails():
    assert _codes(_card(skip=(31,))) == {"MISSING_FINISHED_PROFILE_SECTION"}


def test_finished_card_missing_conditional_section_fails():
    assert _codes(_card(skip=(21,))) == {"MISSING_FINISHED_PROFILE_SECTION"}


def test_finished_card_with_reasoned_not_applicable_passes():
    md = _card(bodies={31: "NOT_APPLICABLE: no region CDS census was requested for this locus."})
    assert _codes(md) == set()


def test_bare_not_applicable_fails():
    assert _codes(_card(bodies={31: "NOT_APPLICABLE"})) == {"NOT_APPLICABLE_WITHOUT_REASON"}


def test_draft_missing_optional_section_passes():
    assert _codes(_card(finished=False, skip=(31,))) == set()


def test_verify_modeb_enforces_the_rule(tmp_path, capsys):
    card = tmp_path / "card.md"
    card.write_text(_card(skip=(31,)), encoding="utf-8")
    args = argparse.Namespace(file=str(card), card=str(card), package=None, bgc=None,
                              contract="current50_v2", report_json=None)
    verify_modeb_command(args)
    assert "MISSING_FINISHED_PROFILE_SECTION" in capsys.readouterr().out
