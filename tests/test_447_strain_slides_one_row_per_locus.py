"""A found gene that is the best hit of two reference genes takes the label the map uses: the reciprocal best, then the
higher identity, whatever the row order. a validamycin-like BGC's strip read valJ where the map read valE."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import strain_slides as ss  # noqa: E402


def rows(*spec):
    return [dict(name=n, best_locus="ctg290_4", reciprocal_best=rb, best_identity_pct=str(i)) for n, rb, i in spec]


def test_reciprocal_best_wins_over_a_later_row():
    got = ss.one_row_per_locus(rows(("valE", "True", 59.5), ("valJ", "False", 58.6)))
    assert got["ctg290_4"]["name"] == "valE"
    got = ss.one_row_per_locus(rows(("valJ", "False", 58.6), ("valE", "True", 59.5)))
    assert got["ctg290_4"]["name"] == "valE"


def test_reciprocal_best_wins_over_higher_identity_then_identity_breaks_ties():
    assert ss.one_row_per_locus(rows(("a", "True", 40), ("b", "False", 70)))["ctg290_4"]["name"] == "a"
    assert ss.one_row_per_locus(rows(("a", "False", 40), ("b", "False", 70)))["ctg290_4"]["name"] == "b"


def test_rows_without_a_locus_are_skipped():
    assert ss.one_row_per_locus([dict(name="x", best_locus="", reciprocal_best="True", best_identity_pct="90")]) == {}
