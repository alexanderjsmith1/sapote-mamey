"""Guard: the TFBS scan's reverse-strand branch must call a defined reverse_complement.

A v9.7.19 edit briefly clobbered the `reverse_complement` def while inserting `couple_kcb_ptm`; the unit
suite missed it because no fixture carried a minus-strand CDS to exercise scan_tfbs's else-branch — only
real strain contigs did. This locks the path so the function can't be silently removed again.
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mamey.models import CDSFeature
from mamey.source_scans import scan_tfbs, reverse_complement


def test_reverse_complement_defined_and_correct():
    assert reverse_complement("ACGTN") == "NACGT"


def test_scan_tfbs_minus_strand_exercises_reverse_complement():
    contigs = {"NODE_1": "ACGTACGT" * 100}
    cds = [CDSFeature("NODE_1", 100, 400, -1, "m1", "hypothetical protein", None, None, {})]
    out = scan_tfbs(contigs, cds)  # must not raise NameError on the reverse-strand branch
    assert isinstance(out, dict)


if __name__ == "__main__":
    test_reverse_complement_defined_and_correct()
    test_scan_tfbs_minus_strand_exercises_reverse_complement()
    print("tfbs reverse-strand guard: all tests pass")
