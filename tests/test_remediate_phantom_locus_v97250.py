"""v9.7.250 — tools/remediate_phantom_locus.py, the card-side companion to the PHANTOM_LOCUS lint.

The lint refuses a card that cites a foreign locus. It does not repair one. 74 authored cards
carry the v9.7.246 *Amycolatopsis* leak and are not fixed by the source patch. This tool finds
and deletes the fabricated paragraphs, with the rule the changelog states: DELETE, do not reword —
there is no BLASTp result to reword.

Pinned here: the authoritative (CDS-table) path, the heuristic (known-leak) path, the empty-locus
guard, idempotence, markdown-separator preservation, and that a clean card is left byte-identical.
"""
from __future__ import annotations
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "remediate_phantom_locus.py"

CONTAMINATED = """# Mode B — BGC036

## §4 Gene-by-gene

The core genes ctg5_10 and ctg5_11 form the assembly line.

antiSMASH Pfam calls are a hypothesis — per-gene BLASTp overturned two of ten on BGC006. This is the offline channel that settled BGC006 ctg12_71.

Gene ctg5_12 encodes the transporter.

## §19 Verdict

Capacity consistent with a ranthipeptide.
"""

CLEAN = """# Mode B — BGC037

## §4 Gene-by-gene

Genes ctg5_10 through ctg5_12 are interior.
"""


def _run(*args):
    return subprocess.run([sys.executable, str(TOOL), *args],
                          capture_output=True, text=True)


def _fixture(tmp_path, card_text=CONTAMINATED, with_cds=True):
    cards = tmp_path / "cards"; cards.mkdir()
    (cards / "BGC036_mode_b.md").write_text(card_text, encoding="utf-8")
    (cards / "BGC037_mode_b.md").write_text(CLEAN, encoding="utf-8")
    pkg = tmp_path / "pkg"; pkg.mkdir()
    if with_cds:
        (pkg / "S_cds_table.csv").write_text(
            "locus_tag,bgc_id\nctg5_10,BGC036\nctg5_11,BGC036\nctg5_12,BGC036\n", encoding="utf-8")
    return cards, pkg


def test_dry_run_reports_and_exits_1_without_modifying(tmp_path):
    cards, pkg = _fixture(tmp_path)
    before = (cards / "BGC036_mode_b.md").read_text()
    r = _run("--cards", str(cards), "--package", str(pkg))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "ctg12_71" in r.stdout
    assert (cards / "BGC036_mode_b.md").read_text() == before, "dry run must not modify"


def test_apply_deletes_only_the_fabricated_paragraph(tmp_path):
    cards, pkg = _fixture(tmp_path)
    r = _run("--cards", str(cards), "--package", str(pkg), "--apply")
    assert r.returncode == 0, r.stdout + r.stderr
    out = (cards / "BGC036_mode_b.md").read_text()
    assert "ctg12_71" not in out
    for real in ("ctg5_10", "ctg5_11", "ctg5_12"):
        assert real in out, f"{real} is this strain's own locus and must be retained"
    assert "## §19 Verdict" in out, "unrelated sections must survive"


def test_markdown_separators_are_preserved(tmp_path):
    """A deleted paragraph takes exactly one blank-line separator with it."""
    cards, pkg = _fixture(tmp_path)
    _run("--cards", str(cards), "--package", str(pkg), "--apply")
    out = (cards / "BGC036_mode_b.md").read_text()
    assert "\n\n## §19 Verdict\n" in out
    assert "\n\n\n" not in out, "collapsed or doubled blank lines"


def test_clean_card_is_untouched(tmp_path):
    cards, pkg = _fixture(tmp_path)
    before = (cards / "BGC037_mode_b.md").read_text()
    _run("--cards", str(cards), "--package", str(pkg), "--apply")
    assert (cards / "BGC037_mode_b.md").read_text() == before
    assert not (cards / "BGC037_mode_b.md.bak").exists(), "no .bak for an untouched card"


def test_apply_is_idempotent(tmp_path):
    cards, pkg = _fixture(tmp_path)
    _run("--cards", str(cards), "--package", str(pkg), "--apply")
    once = (cards / "BGC036_mode_b.md").read_text()
    r = _run("--cards", str(cards), "--package", str(pkg))
    assert r.returncode == 0, "second scan must find nothing"
    assert (cards / "BGC036_mode_b.md").read_text() == once


def test_backup_is_written_on_apply(tmp_path):
    cards, pkg = _fixture(tmp_path)
    _run("--cards", str(cards), "--package", str(pkg), "--apply")
    bak = cards / "BGC036_mode_b.md.bak"
    assert bak.exists() and "ctg12_71" in bak.read_text()


def test_empty_locus_universe_is_refused(tmp_path):
    """Guard: an empty CDS table would make every locus look phantom. Refuse, exit 2."""
    cards, pkg = _fixture(tmp_path, with_cds=False)
    r = _run("--cards", str(cards), "--package", str(pkg))
    assert r.returncode == 2, r.stdout + r.stderr
    assert "refusing" in r.stderr.lower()


def test_heuristic_mode_without_package_finds_the_known_leak(tmp_path):
    cards, _ = _fixture(tmp_path)
    r = _run("--cards", str(cards))
    assert r.returncode == 1
    assert "ctg12_71" in r.stdout
    assert "known-leak" in r.stdout, "must state that it cannot see other foreign loci"


def test_heuristic_mode_cannot_see_a_different_foreign_locus(tmp_path):
    """Honest limitation, pinned: without a CDS table, ctg99_1 is invisible."""
    card = CONTAMINATED.replace("ctg12_71", "ctg99_1")
    cards, _ = _fixture(tmp_path, card_text=card)
    r = _run("--cards", str(cards))
    # the leak PHRASE still matches, but the locus itself is not in KNOWN_LEAK_LOCI
    assert "ctg99_1" not in r.stdout
