"""v9.7.251 — `remediate_phantom_locus.py` must only ever edit Mode B cards.

The tool DELETES paragraphs from files, in place, under `--apply`. As shipped in v9.7.250 it
globbed `*.md` and treated every result as a card. Measured on the shipped v9.7.250 tree:

    remediate_phantom_locus.py --cards docs --apply
        -> deleted 4 paragraphs, 3,703 of 21,424 chars (17%), from docs/ONLINE_BLASTP_PROTOCOL.md

That is the file the v9.7.250 changelog explicitly protects:

    "docs/ONLINE_BLASTP_PROTOCOL.md is **left alone**: it is the case study itself, its subject
     is named, and its loci are its own."

It also stripped the paragraph from `work_in_progress/README.md` stating those cards are *not*
affected, and two paragraphs from `docs/reference/modeb_exemplars/README.md`, which documents the
fix. A document that *discusses* the leak is not a card that *commits* it. The tool could not tell
the difference, and the one thing it does is delete.

A Mode B card declares itself on line 1 (`<!-- MODE B TEMPLATE | ... -->` or `<!-- MODE B: ... -->`).
Verified 5/5 in-tree: every card carries it, no prose document does.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "remediate_phantom_locus.py"

LEAK_SENTENCE = (
    "**Third channel:** This is the offline, deterministic channel that settled "
    "BGC006 ctg12_71 (esterase, not beta-lactamase).\n"
)
CARD_HEADER = (
    "<!-- MODE B TEMPLATE | bgc: BGC036 | node: NODE_5_length_320211_cov_36 | "
    "strain: AS-XXX | products: RiPP | contract: modeb_corrective_full30_v1 -->\n"
)


def _run(cards_dir: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TOOL), "--cards", str(cards_dir), *extra],
        capture_output=True, text=True,
    )


def test_tool_exists():
    assert TOOL.is_file(), f"{TOOL} not found"


def test_apply_does_not_touch_a_prose_doc_that_mentions_the_leak(tmp_path):
    """The named regression: a doc discussing ctg12_71 must survive --apply untouched."""
    doc = tmp_path / "ONLINE_BLASTP_PROTOCOL.md"
    original = (
        "# Online BLASTp protocol\n\n"
        "Two antiSMASH calls were overturned on BGC006 (NODE_12, region001):\n\n"
        "- `ctg12_71` — antiSMASH Beta-lactamase -> BLASTp EstA esterase (78% id).\n\n"
        "This is the case study. Its loci are its own.\n"
    )
    doc.write_text(original, encoding="utf-8")

    r = _run(tmp_path, "--apply")
    assert r.returncode == 0, r.stderr
    assert doc.read_text(encoding="utf-8") == original, (
        "remediate_phantom_locus.py rewrote a prose document. It must only edit Mode B cards."
    )
    assert not (tmp_path / "ONLINE_BLASTP_PROTOCOL.md.bak").exists(), (
        "a .bak proves the file was rewritten"
    )


def test_apply_does_not_touch_a_readme_documenting_the_incident(tmp_path):
    readme = tmp_path / "README.md"
    original = (
        "# Work in progress\n\n"
        "These two cards cite only their own contigs and never cite `ctg12_71`. "
        "They are **not** among the cards affected by the v9.7.246 incident.\n"
    )
    readme.write_text(original, encoding="utf-8")
    r = _run(tmp_path, "--apply")
    assert r.returncode == 0, r.stderr
    assert readme.read_text(encoding="utf-8") == original


def test_apply_still_excises_the_leak_from_a_real_card(tmp_path):
    """Positive control. If this passes vacuously the test above proves nothing."""
    card = tmp_path / "ripp_exemplar.md"
    card.write_text(
        CARD_HEADER
        + "\n# Mode B — BGC036\n\n## §4 Gene-by-gene interpretation\n\n"
        + "The core is `ctg5_60`, a glycosyltransferase.\n\n"
        + LEAK_SENTENCE,
        encoding="utf-8",
    )
    r = _run(tmp_path, "--apply")
    assert r.returncode == 0, r.stderr
    out = card.read_text(encoding="utf-8")
    assert "ctg12_71" not in out, "the leak was not excised from a genuine card"
    assert "ctg5_60" in out, "excision removed the card's own, legitimate content"
    assert (tmp_path / "ripp_exemplar.md.bak").exists(), "no backup written before an in-place edit"


def test_directory_of_only_prose_reports_nothing_to_do(tmp_path):
    (tmp_path / "notes.md").write_text("Discussion of ctg12_71 and the leak.\n", encoding="utf-8")
    r = _run(tmp_path)
    assert r.returncode == 0
    assert "No Mode B cards" in (r.stderr + r.stdout)


@pytest.mark.parametrize("header", [
    "<!-- MODE B TEMPLATE | bgc: BGC036 | node: NODE_5_x | strain: AS-XXX -->\n",
    "<!-- MODE B: BGC002 | node: NODE_107_x | strain: AS-XXX -->\n",
])
def test_both_header_forms_are_recognised_as_cards(tmp_path, header):
    """Two header forms ship in-tree. A filter that misses one silently stops remediating."""
    card = tmp_path / "card.md"
    card.write_text(header + "\n## §4\n\n" + LEAK_SENTENCE, encoding="utf-8")
    r = _run(tmp_path)
    assert "1 affected" in r.stdout, f"header form not recognised as a card:\n{r.stdout}{r.stderr}"


def test_shipped_protected_files_are_not_cards():
    """Ground truth for the filter, checked against the real tree rather than a fixture."""
    not_cards = [
        ROOT / "docs" / "ONLINE_BLASTP_PROTOCOL.md",
        ROOT / "docs" / "reference" / "modeb_exemplars" / "README.md",
    ]
    cards = [
        ROOT / "docs" / "reference" / "modeb_exemplars" / "ripp_exemplar.md",
        ROOT / "docs" / "reference" / "modeb_exemplars" / "siderophore_exemplar.md",
    ]
    for p in not_cards:
        if p.is_file():
            assert "MODE B" not in p.read_text(encoding="utf-8").split("\n", 1)[0], p
    for p in cards:
        if p.is_file():
            assert "MODE B" in p.read_text(encoding="utf-8").split("\n", 1)[0], p
