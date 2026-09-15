"""Conservative display normalization for phylogeny metadata.

The raw deposited value remains evidence. These helpers produce a small visual vocabulary for
tree strips and a state describing the transformation; they do not infer ecological provenance.
"""
from __future__ import annotations

import re


_CATEGORY_RULES = (
    # Keep the curated bee/wasp distinctions used by cohort figures.  These
    # must precede the broad insect rule or every project isolate becomes the
    # same uninformative "insect-associated" colour.
    ("honeybee", r"\b(honey ?bee|apis(?:\s+mellifera)?)\b"),
    ("bumblebee", r"\b(bumble ?bee|bombus)\b"),
    ("solitary bee", r"\b(solitary bee|andrena|megachile|osmia|colletes|halictus|xylocopa)\b"),
    ("other bee", r"\b(other apidae|unidentified (?:bee|apidae)|other bee)\b"),
    ("wasp", r"\b(wasp|wasps|vespa|vespula|polistes|philanthus|beewolf)\b"),
    ("attine ant", r"\b(attine|lower attine|atta|acromyrmex|myrmicocrypta|trachymyrmex)\b"),
    # v9.7.430: bare "gut" was removed from this alternation and re-added BELOW the insect rule.
    # Because this rule precedes "insect-associated", bare "gut" here classified "termite gut",
    # "bee gut", "ant gut" and "insect gut" as clinical — a visible mislabel on the tree reference
    # series for a thesis whose cohort is insect-associated. Deleting "gut" outright was the
    # obvious fix and is wrong: it drops "mouse gut", "rat gut", "chicken gut", "fish gut",
    # "porcine gut", "murine gut contents" and bare "gut" out of EVERY rule (measured: 8 sources
    # fall through to no category). Reordering the whole insect rule above this one is also wrong:
    # it steals genuinely clinical strings that merely mention an insect ("blood of a patient with
    # insect bite" -> insect-associated; measured: 6 such sources change). Scoping "gut" below the
    # insect rule changes exactly the 6 insect-gut sources and nothing else.
    ("clinical/animal-associated", r"\b(patient|clinical|human|homo sapiens|infected|liver|tissue|pus|blood|bovine|bos taurus|animal|feces|faeces)\b"),
    ("insect-associated", r"\b(ant|ants|bee|bees|wasp|wasps|termite|insect|arthropod|hymenopter)\b"),
    # "gut" with no insect and no explicit clinical term: a non-insect animal gut. Must stay BELOW
    # the insect rule and ABOVE the environmental rules, or "termite gut" returns to clinical.
    ("clinical/animal-associated", r"\bgut\b"),
    ("plant-associated", r"\b(plant|root|rhizosphere|potato|barley|grain|leaf|leaves|stem|seed|wood|fruit|mangrove)\b"),
    ("bryophyte/lichen-associated", r"\b(moss|bryophyte|lichen|liverwort)\b"),
    ("aquatic", r"\b(freshwater|groundwater|lake|river|pond|stream|seawater|marine|ocean|coral|sponge|aquatic|brine|water|waters)\b"),
    ("soil/rock/sediment", r"\b(soil|rock|sand|sediment|desert|cryoconite|glacier|cave|mud)\b"),
    ("fungal-associated", r"\b(fungus|fungal|mushroom|hypha|myceli)\w*\b"),
    ("built environment", r"\b(activated sludge|wastewater|sewage|compost|bioreactor|industrial)\b"),
)


def _clean(value: str | None) -> str:
    value = (value or "").strip()
    return "" if value.lower() in {"", "unknown", "n/a", "na", "none", "not provided", "not recorded", "missing", "-"} else value


def normalize_isolation_source(isolation_source: str | None, host: str | None = None) -> dict[str, str]:
    """Return raw text plus a controlled figure category and explicit normalization state."""
    raw = _clean(isolation_source) or _clean(host)
    if not raw:
        return {"raw": "", "display_category": "", "state": "NOT_RECORDED"}
    lowered = re.sub(r"\s+", " ", raw.lower())
    for category, pattern in _CATEGORY_RULES:
        if re.search(pattern, lowered):
            return {"raw": raw, "display_category": category, "state": "RULE_NORMALIZED"}
    return {"raw": raw, "display_category": "other documented", "state": "DOCUMENTED_OTHER"}


_COUNTRY_ALIASES = {
    "u.s.a.": "USA", "u.s.a": "USA", "us": "USA", "usa": "USA",
    "united states": "USA", "united states of america": "USA",
    "republic of korea": "South Korea", "korea, republic of": "South Korea",
    "south korea": "South Korea", "republic of china": "Taiwan",
    "russian federation": "Russia", "viet nam": "Vietnam",
}
_KNOWN_COUNTRIES = {
    # v9.7.431: "Georgia" added (deposited geo_loc_name "Georgia: Poti" previously fell through
    # to AS_RECORDED). Alphabetised while editing.
    "Australia", "Austria", "Brazil", "Canada", "China", "Finland", "France", "Georgia",
    "Germany", "India", "Japan", "Mexico", "Mongolia", "Namibia", "Pakistan", "Russia",
    "South Africa", "South Korea", "Spain", "Taiwan", "USA", "United Kingdom", "Vietnam",
}
_COUNTRY_TO_DISPLAY = {
    "USA": "US", "Canada": "Canada", "Mexico": "North America",
    "Brazil": "South America",
    # v9.7.431: Georgia RULED "Europe" (NCBI BioSample convention, 2026-09-14). Before this entry
    # a deposited "Georgia: Poti" fell through .get(country, raw) to the full raw string, the same
    # latent gap Russia still has (it genuinely spans two continents; Georgia does not).
    "Austria": "Europe", "Finland": "Europe", "Georgia": "Europe", "Spain": "Europe",
    "United Kingdom": "Europe", "Germany": "Europe", "France": "Europe",
    "China": "Asia", "Japan": "Asia", "Pakistan": "Asia", "South Korea": "Asia",
    "Taiwan": "Asia", "Vietnam": "Asia", "India": "Asia", "Mongolia": "Asia",
    "South Africa": "Africa", "Namibia": "Africa", "Australia": "Oceania",
}
_NAMED_OCEANS = {"Pacific Ocean", "Atlantic Ocean", "Indian Ocean", "Southern Ocean", "Arctic Ocean"}

_COUNTRY_TO_CONTINENT = {
    # Europe
    "Austria":         "Europe",
    "Finland":         "Europe",
    "France":          "Europe",
    "Germany":         "Europe",
    "Russia":          "Europe",
    "Spain":           "Europe",
    "United Kingdom":  "Europe",
    # Georgia: RULED "Europe" by Alex 2026-09-14 (NCBI BioSample convention).
    "Georgia":         "Europe",
    # Asia
    "China":           "Asia",
    "India":           "Asia",
    "Japan":           "Asia",
    "Mongolia":        "Asia",
    "Pakistan":        "Asia",
    "South Korea":     "Asia",
    "Taiwan":          "Asia",
    "Vietnam":         "Asia",
    # North America
    "Canada":          "North America",
    "Mexico":          "North America",
    "USA":             "North America",
    # South America
    "Brazil":          "South America",
    # Africa
    "Namibia":         "Africa",
    "South Africa":    "Africa",
    # Oceania
    "Australia":       "Oceania",
}



def _country_name(value: str) -> str | None:
    alias = _COUNTRY_ALIASES.get(value.lower())
    if alias:
        return alias
    for country in _KNOWN_COUNTRIES:
        if value.lower() == country.lower():
            return country
    return None


def normalize_geography(location: str | None) -> dict[str, str]:
    """Create figure geography without inventing locality.

    US and Canada remain distinct. Other recognized countries become continents; an explicitly
    recorded named ocean is retained. Unrecognized deposited text remains visible so the display
    admission gate can hold it rather than silently guessing a region.
    """
    raw = _clean(location)
    if not raw:
        return {"raw": "", "display_location": "", "state": "NOT_RECORDED"}
    if raw in _NAMED_OCEANS:
        return {"raw": raw, "display_location": raw, "state": "AS_RECORDED"}
    direct = _country_name(raw)
    if direct:
        display = _COUNTRY_TO_DISPLAY.get(direct, raw)
        state = "AS_RECORDED" if display == raw else "REGION_NORMALIZED"
        return {"raw": raw, "display_location": display, "state": state}
    if ":" in raw:
        prefix = raw.split(":", 1)[0].strip()
        country = _country_name(prefix)
        if country:
            return {"raw": raw, "display_location": _COUNTRY_TO_DISPLAY.get(country, raw), "state": "COUNTRY_PREFIX"}
    return {"raw": raw, "display_location": raw, "state": "AS_RECORDED"}


def normalize_geography_continent(location: str | None) -> dict[str, str]:
    """Return country + continent bin for a deposited geo_loc_name value.

    Builds on normalize_geography(), but resolves the matched COUNTRY NAME independently via
    _country_name() rather than reusing normalize_geography()'s own `display_location` field.
    `display_location` is already continent-collapsed for most known countries (e.g. Austria,
    France, United Kingdom all return display_location="Europe" today) via `_COUNTRY_TO_DISPLAY` --
    reusing it here would look up `_COUNTRY_TO_CONTINENT["Europe"]` (a miss) instead of
    `_COUNTRY_TO_CONTINENT["United Kingdom"]`, silently dropping the continent bin for every
    country that already has a `_COUNTRY_TO_DISPLAY` entry. Countries absent from
    _COUNTRY_TO_CONTINENT yield display_continent=''. Does not change normalize_geography()'s
    own contract or return value.
    """
    geo = normalize_geography(location)
    raw = geo["raw"]
    prefix = raw.split(":", 1)[0].strip() if ":" in raw else raw
    country = _country_name(prefix) or geo["display_location"]
    continent = _COUNTRY_TO_CONTINENT.get(country, "")
    return {
        "raw":               geo["raw"],
        "display_country":   country,
        "display_continent": continent,
        "state":             geo["state"],
    }
