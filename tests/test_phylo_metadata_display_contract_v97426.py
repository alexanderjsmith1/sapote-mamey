"""Controlled display categories for tree metadata, with raw deposited text retained."""
from importlib import util
from pathlib import Path
import sys


TOOLS = Path(__file__).resolve().parents[1] / "tools"


def _load():
    spec = util.spec_from_file_location("_test_phylo_metadata", TOOLS / "_phylo_metadata.py")
    module = util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_isolation_source_rules_reduce_raw_legend_without_erasing_raw_text():
    metadata = _load()
    cases = {
        "potato common scab lesion": "plant-associated",
        "freshwater lake": "aquatic",
        "infected liver tissue": "clinical/animal-associated",
        "garden soil": "soil/rock/sediment",
        "barley grains": "plant-associated",
        "ant": "insect-associated",
        "mugwort root": "plant-associated",
        "glacier cryoconite": "soil/rock/sediment",
        "activated sludge": "built environment",
    }
    for raw, expected in cases.items():
        result = metadata.normalize_isolation_source(raw)
        assert result["raw"] == raw
        assert result["display_category"] == expected
        assert result["state"] == "RULE_NORMALIZED"


def test_unknown_documented_source_is_typed_other_and_blank_stays_missing():
    metadata = _load()
    other = metadata.normalize_isolation_source("special synthetic habitat")
    assert other == {
        "raw": "special synthetic habitat",
        "display_category": "other documented",
        "state": "DOCUMENTED_OTHER",
    }
    assert metadata.normalize_isolation_source("") == {
        "raw": "",
        "display_category": "",
        "state": "NOT_RECORDED",
    }


def test_geography_normalizes_only_explicit_country_forms():
    metadata = _load()
    assert metadata.normalize_geography("USA: Wisconsin") == {
        "raw": "USA: Wisconsin", "display_location": "USA", "state": "COUNTRY_PREFIX"
    }
    assert metadata.normalize_geography("Republic of Korea") == {
        "raw": "Republic of Korea", "display_location": "South Korea", "state": "ALIASED"
    }
    # Unrecognized text is retained rather than guessed into a country.
    assert metadata.normalize_geography("Northwest field site") == {
        "raw": "Northwest field site", "display_location": "Northwest field site",
        "state": "AS_RECORDED",
    }
