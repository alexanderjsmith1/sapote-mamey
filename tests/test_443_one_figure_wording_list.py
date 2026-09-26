"""One wording list for figures (v9.7.443).

The figure save path (mamey/figure_policy.py) and the caption and render-QC checks
(tools/caption_guard.py) used to keep separate lists. On v9.7.442a they gave opposite verdicts on
13 of 25 strings, so a figure could pass one check and fail the other. These tests hold them to
one verdict.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from caption_guard import BLOCKED, check_caption  # noqa: E402
from mamey.figure_policy import figure_text_violations  # noqa: E402

EXTRA = [
    "Figure 3. Class-level distribution of BGCs across isolates.",
    "Screening signal is class-level.",
    "Activity shown is class-level only.",
    "Cross-strain shared biosynthetic threads (class-level capacity)",
    "similarity, not identity",
    "KCB novelty composition across strains",
    "percent identity to the nearest reference",
    "production medium ISP2",
]


@pytest.mark.parametrize("text", sorted(BLOCKED) + EXTRA)
def test_save_path_and_caption_check_agree(text):
    saved = bool(figure_text_violations([text]))
    captioned = bool(check_caption(text, raises=False))
    assert saved == captioned, f"{text!r}: save path {saved}, caption check {captioned}"


def test_caption_list_is_the_save_path_list():
    from mamey.figure_policy import FIGURE_BANNED_PHRASES

    assert BLOCKED == FIGURE_BANNED_PHRASES


def test_a_line_break_inside_a_phrase_is_still_refused():
    assert figure_text_violations(["shared families: similarity,\nnot\nidentity"])
    assert figure_text_violations(["EPA-ng placement; judgment\ndeferred"])
