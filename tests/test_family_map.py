"""P03: the grown family map must stay compound-class level and never false-concordant on the
adjudicated discordant set. Uses the lexicon shipped in the bundle (no private data)."""
import json, os
from mamey import diagnostic_rescue as DR

LEX = os.path.join(os.path.dirname(__file__), "..", "mamey", "data", "families", "kcb_compound_family.json")


def test_lexicon_loads_and_grew():
    m = json.load(open(LEX))
    assert m["schema_version"].startswith("kcb-family")
    assert len(m["by_accession"]) >= 100, "P03 lexicon should be substantially larger than the 13 seed"


def test_curated_indolocarbazole_preserved():
    m = DR.load_family_map(LEX)
    # the validated indolocarbazole-split anchors must still both resolve to indolocarbazole
    assert DR.kcb_family("BGC0000809.3 | AT2433-A1", m) == "indolocarbazole"
    assert DR.kcb_family("BGC0002460.3 | loonamycin", m) == "indolocarbazole"
    assert DR._concordance("indolocarbazole", "indolocarbazole", m) == "concordant"


def test_cross_family_is_discordant():
    m = DR.load_family_map(LEX)
    # a glycopeptide vs a tetronate must be discordant, never concordant
    assert DR._concordance("glycopeptide", "tetronate", m) == "discordant"
