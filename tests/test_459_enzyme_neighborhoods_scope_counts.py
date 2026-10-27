"""The pilot/full receipt scope line states the counts actually selected.

It used to be fixed text ("Five representative candidates and one real no-call",
"... five real no-call controls") whatever the source roster gave.
"""
import re
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[1] / "mamey" / "cohort_enzyme_neighborhoods.py"


def test_no_fixed_count_scope_text_left_in_source():
    text = SOURCE.read_text()
    assert not re.search(r"Five representative candidates|five real no-call", text), (
        "receipt scope still hard-codes 'five' / 'one' control text")


@pytest.mark.parametrize("pilot,cands,controls,expect", [
    (True, 5, 0, ["5 representative candidates", "no real no-call control"]),
    (True, 5, 1, ["5 representative candidates", "1 real no-call control"]),
    (False, 37, 0, ["37 candidates", "no real no-call control"]),
    (False, 37, 3, ["37 candidates", "3 real no-call controls"]),
    (False, 37, 5, ["37 candidates", "5 real no-call controls"]),
])
def test_scope_text_follows_counts(pilot, cands, controls, expect):
    from mamey.cohort_enzyme_neighborhoods import scope_text
    out = scope_text(pilot, cands, controls)
    for piece in expect:
        assert piece in out, (piece, out)
    if controls == 0:
        assert "one" not in out.lower().split() and "five" not in out.lower().split()
