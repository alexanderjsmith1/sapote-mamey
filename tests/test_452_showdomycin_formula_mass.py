"""The showdomycin row states a formula whose mass matches its printed values.

Showdomycin is C9H11NO6 (PubChem CID 28032; monoisotopic 229.0586 Da), so [M+H]+ is
m/z 230.0659. The earlier row printed C5H5NO4 = 175.0269, which no formula of that
composition can give.
"""
from pathlib import Path

MONOLITH = Path(__file__).resolve().parents[1] / "docs" / "SAPOTE_MAMEY_BUNDLE_MONOLITH.md"
MONO = {"C": 12.0, "H": 1.00782503207, "N": 14.0030740048, "O": 15.99491461956}
PROTON = 1.007276467


def _row():
    rows = [line for line in MONOLITH.read_text(encoding="utf-8").splitlines()
            if line.startswith("| Showdomycin (maleimide C-nucleoside) |")]
    assert len(rows) == 1
    return rows[0]


def test_formula_and_masses_are_consistent():
    row = _row()
    assert "C₉H₁₁NO₆ = 229.0586" in row and "230.0659" in row
    neutral = 9 * MONO["C"] + 11 * MONO["H"] + MONO["N"] + 6 * MONO["O"]
    assert round(neutral, 4) == 229.0586
    assert round(neutral + PROTON, 4) == 230.0659


def test_inconsistent_values_are_gone():
    row = _row()
    assert "C₅H₅NO₄" not in row and "175.0269" not in row and "176.034" not in row
