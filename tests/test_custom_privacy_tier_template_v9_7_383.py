"""v9.7.383 — a downstream user must be able to establish their own privacy tiers.

The five-tier release framework already supports user-defined privacy separation
(private/ dirs, the denylist, AS_SCRUB), but a GitHub user was left with nothing
to start from: the real tools/release_denylist.txt is stripped from every public
tier, and there was no how-to. This suite pins the two things that unlock the
existing capability so a future cut cannot silently drop them:

  1. tools/release_denylist.example.txt SHIPS (its name does not match the cut's
     exact-name strip of release_denylist.txt, so it survives to the public tier).
  2. docs/CUSTOM_PRIVACY_TIERS.md SHIPS and points a user at the template + the
     one tool that drives the cut.

It also asserts the strip is by EXACT name, which is what makes the .example
template survive — if that ever became a glob, the template would vanish.
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_denylist_example_template_ships_and_is_documented():
    tpl = ROOT / "tools" / "release_denylist.example.txt"
    assert tpl.is_file(), "release_denylist.example.txt must ship as the user's starting template"
    body = tpl.read_text(encoding="utf-8")
    assert body.strip(), "template must not be empty"
    # tells the user how to activate it
    assert "release_denylist.txt" in body, "template must document copying to release_denylist.txt"


def test_custom_privacy_tiers_doc_ships_and_links_the_pieces():
    doc = ROOT / "docs" / "CUSTOM_PRIVACY_TIERS.md"
    assert doc.is_file(), "docs/CUSTOM_PRIVACY_TIERS.md must ship"
    body = doc.read_text(encoding="utf-8")
    assert "release_denylist.example.txt" in body, "doc must point users at the template"
    assert "make_public_tier.sh" in body, "doc must name the tool that drives the cut"
    assert "AS_SCRUB" in body, "doc must cover the strain-ID redaction switch"


def test_denylist_strip_is_exact_name_so_example_survives():
    """The cut strips release_denylist.txt by EXACT name; the .example template
    must therefore survive. Guard against the strip becoming a glob."""
    cut = ROOT / "tools" / "make_public_tier.sh"
    src = cut.read_text(encoding="utf-8")
    assert '-name "release_denylist.txt"' in src, (
        "expected an exact-name strip of release_denylist.txt in make_public_tier.sh"
    )
    # a glob strip (release_denylist*) would also delete the .example template
    assert '-name "release_denylist*"' not in src, (
        "strip must not glob release_denylist* — that would delete the shipped .example template"
    )


def test_tier_framework_still_has_all_arms():
    """P0-11 direction: KEEP the multi-tier machinery (do not consolidate it away)."""
    cut = (ROOT / "tools" / "make_public_tier.sh").read_text(encoding="utf-8")
    for arm in ("code)", "clean)", "sid)", "merged)", "public)"):
        assert arm in cut, f"tier arm {arm!r} must remain — tiers are a user-facing privacy feature"
