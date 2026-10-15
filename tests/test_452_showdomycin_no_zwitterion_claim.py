"""The showdomycin row makes no zwitterion claim: the structure (PubChem CID 28032) has no basic amine, and no source
supports it (owner ruling, 14 Oct 2026). The peptidyl-nucleoside rows keep theirs."""
from pathlib import Path

MONOLITH = Path(__file__).resolve().parents[1] / "docs" / "SAPOTE_MAMEY_BUNDLE_MONOLITH.md"


def _row(prefix):
    rows = [l for l in MONOLITH.read_text(encoding="utf-8").splitlines() if l.startswith(prefix)]
    assert len(rows) == 1
    return rows[0]


def test_showdomycin_row_has_no_zwitterion_claim():
    row = _row("| Showdomycin (maleimide C-nucleoside)")
    assert "zwitterion" not in row.lower()
    assert "verify ionization mode empirically" in row


def test_peptidyl_nucleoside_row_unchanged():
    assert "zwitterionic" in _row("| Peptidyl nucleoside (nikkomycin/polyoxin class)")
