"""The caption band must not print markdown italics as literal asterisks.

Captions italicize species names (*Usnea*, *Micromonospora pisi*). flatten_md already dropped
**bold**, `code` and links, but single-asterisk italics reached the band as "*Usnea*" (moss S4,
12 Oct). A leading "* item" list marker must still be treated as a list item, not as italics.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import caption_band  # noqa: E402


def test_single_asterisk_italics_are_dropped():
    lines = caption_band.flatten_md("Isolated from the lichen *Usnea* and *Micromonospora pisi* DSM 45175.")
    assert lines == ["Isolated from the lichen Usnea and Micromonospora pisi DSM 45175."]


def test_bold_and_list_items_still_work():
    lines = caption_band.flatten_md("**Bold** text\n* item one\n- item two\n")
    assert lines == ["Bold text", "item one", "item two"]


def test_a_lone_asterisk_is_kept():
    assert caption_band.flatten_md("p < 0.05 * 2") == ["p < 0.05 * 2"]
