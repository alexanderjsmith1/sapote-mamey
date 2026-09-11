"""Seal-time guard for stale or contradictory prose in the newest CHANGELOG entry.

Historical entries are evidence and remain untouched.  Only the first release entry is
eligible to describe the tree being sealed, so the scan is deliberately bounded there.
"""
from pathlib import Path
import re

import pytest


ROOT = Path(__file__).resolve().parents[1]
PROHIBITED_NEWEST_ENTRY_PHRASES = (
    "CANDIDATE — not a seal",
    "absent by defined-symbol",
    "TO BE FILLED",
    "PENDING, not yet in this tree",
)
ENTRY_HEADER = re.compile(r"(?m)^# v\d+\.\d+\.\d+[^\n]*$")


def newest_changelog_entry(text: str) -> str:
    """Return exactly the first versioned entry, failing closed on malformed input."""
    headers = list(ENTRY_HEADER.finditer(text))
    if not headers or headers[0].start() != 0:
        raise ValueError("CHANGELOG must start with a versioned '# vX.Y.Z' entry")
    end = headers[1].start() if len(headers) > 1 else len(text)
    return text[:end]


def prohibited_phrases(entry: str) -> list[str]:
    return [phrase for phrase in PROHIBITED_NEWEST_ENTRY_PHRASES if phrase in entry]


def test_newest_changelog_entry_is_seal_ready():
    entry = newest_changelog_entry((ROOT / "CHANGELOG.md").read_text(encoding="utf-8"))
    found = prohibited_phrases(entry)
    assert not found, (
        "newest CHANGELOG entry contains composition-only or contradictory prose: "
        + ", ".join(repr(item) for item in found)
    )


@pytest.mark.parametrize("phrase", PROHIBITED_NEWEST_ENTRY_PHRASES)
def test_each_prohibited_phrase_is_detected_in_newest_entry_only(phrase):
    text = f"# v9.7.406 · current\n{phrase}\n\n# v9.7.405 · history\nretained\n"
    assert prohibited_phrases(newest_changelog_entry(text)) == [phrase]


def test_historical_prohibited_phrase_is_not_a_current_release_failure():
    text = (
        "# v9.7.406 · current\nSeal-ready prose.\n\n"
        "# v9.7.405 · history\nCANDIDATE — not a seal\n"
    )
    assert prohibited_phrases(newest_changelog_entry(text)) == []


@pytest.mark.parametrize("text", ["", "preface\n# v9.7.406 · current\n"])
def test_malformed_changelog_fails_closed(text):
    with pytest.raises(ValueError, match="must start"):
        newest_changelog_entry(text)
