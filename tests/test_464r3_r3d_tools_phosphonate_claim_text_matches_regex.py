"""The phosphonate cassette's claim-safety text must not say the regex vetoes false positives it
still matches; the generated catalog carries the registry text."""
import json
import re
from pathlib import Path

from mamey.source_scans import CASSETTE_PATTERNS

ROOT = Path(__file__).resolve().parents[1]


def _entry():
    entries = json.loads((ROOT / "bundle_support/registry_inventory_v1.9.4.json").read_text(encoding="utf-8"))
    return next(e for e in entries if e["id"] == "MMC-004")


def _matches(text):
    return any(re.search(p, text, re.I) for p in CASSETTE_PATTERNS["phosphonate"])


def test_reversed_word_order_still_matches_so_no_veto_is_claimed():
    assert not _matches("phosphonate c-p lyase subunit")
    assert _matches("c-p lyase phosphonate degradation protein")
    text = _entry()["claim_safety"]
    assert "already vetoes" not in text
    assert "annotation-level candidate" in text and "not screened" in text


def test_generated_catalog_carries_the_registry_text():
    catalog = (ROOT / "docs/USER_CATALOG.generated.md").read_text(encoding="utf-8")
    assert _entry()["claim_safety"] in catalog
    assert "already vetoes" not in catalog
