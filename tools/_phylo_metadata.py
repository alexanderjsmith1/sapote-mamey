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
    ("clinical/animal-associated", r"\b(patient|clinical|human|homo sapiens|infected|liver|tissue|pus|blood|bovine|bos taurus|animal|gut|feces|faeces)\b"),
    ("insect-associated", r"\b(ant|ants|bee|bees|wasp|wasps|termite|insect|arthropod|hymenopter)\b"),
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
    "Australia", "Austria", "Canada", "China", "Finland", "Japan", "Pakistan", "Russia",
    "South Africa", "South Korea", "Spain", "Taiwan", "USA", "Vietnam", "United Kingdom",
    "Germany", "France", "India", "Brazil", "Mexico", "Mongolia", "Namibia",
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
    """Normalize explicit country spellings; retain unrecognized deposited text unchanged."""
    raw = _clean(location)
    if not raw:
        return {"raw": "", "display_location": "", "state": "NOT_RECORDED"}
    direct = _country_name(raw)
    if direct:
        state = "AS_RECORDED" if direct == raw else "ALIASED"
        return {"raw": raw, "display_location": direct, "state": state}
    if ":" in raw:
        prefix = raw.split(":", 1)[0].strip()
        country = _country_name(prefix)
        if country:
            return {"raw": raw, "display_location": country, "state": "COUNTRY_PREFIX"}
    return {"raw": raw, "display_location": raw, "state": "AS_RECORDED"}
