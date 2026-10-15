"""Deposited countries in the 16S reference panels map to a display region the shared palette has."""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import _phylo_metadata as m  # noqa: E402


def _palette_geography():
    rows = csv.DictReader(open(ROOT / "tools" / "phylo_display_palette.tsv"), delimiter="\t")
    return {r["value"] for r in rows if r["field"] == "geography"}


def test_added_countries_map_to_palette_regions():
    pal = _palette_geography()
    for country in ("Antarctica", "Denmark", "Indonesia", "Korea", "Lebanon", "Martinique", "Netherlands",
                    "Norway", "Portugal", "Sweden", "Thailand", "Togo", "Turkey", "USSR"):
        assert country in m._KNOWN_COUNTRIES
        assert m._COUNTRY_TO_DISPLAY[country] in pal, country


def test_owner_rulings_for_transcontinental_and_antarctica():
    assert m._COUNTRY_TO_DISPLAY["Turkey"] == "Asia"
    assert "Russia" not in m._COUNTRY_TO_DISPLAY  # labels keep the deposited "Russia"
    assert m._COUNTRY_TO_CONTINENT["Russia"] == "Europe"
    assert m._COUNTRY_TO_DISPLAY["Antarctica"] == "Other documented"
    assert m._COUNTRY_TO_DISPLAY["USSR"] == "Other documented"


def test_existing_mappings_unchanged():
    assert m._COUNTRY_TO_DISPLAY["USA"] == "US"
    assert m._COUNTRY_TO_DISPLAY["Canada"] == "Canada"
    assert m._COUNTRY_TO_DISPLAY["Japan"] == "Asia"
    assert m._COUNTRY_TO_CONTINENT["USA"] == "North America"


def test_korea_is_not_aliased_to_south_korea():
    assert "korea" not in m._COUNTRY_ALIASES
