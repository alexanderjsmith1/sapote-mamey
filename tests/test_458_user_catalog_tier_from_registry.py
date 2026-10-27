"""The user catalog shows each cassette's evidence tier.

gen_user_catalog read entry["tier"], but every registry entry stores "evidence_tier", so all 15
cassettes had a blank tier and the generated catalog printed no tier line at all.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_every_cassette_has_a_tier():
    data = json.loads((ROOT / "docs" / "USER_CATALOG.generated.json").read_text())
    tiers = [c["tier"] for c in data["cassettes"]]
    assert len(tiers) == 15 and all(t.startswith("TIER_") for t in tiers), tiers


def test_markdown_shows_the_tier():
    md = (ROOT / "docs" / "USER_CATALOG.generated.md").read_text()
    assert md.count("*Tier:* TIER_") == 15
