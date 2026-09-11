"""RED-02 (v9.7.331): RiQ genome-summary median must average the two central
values on even-length score lists.

Root cause (Bunny-Hop bug-hunt, v9.7.330): antismash_evidence.py computed the
per-genome RiQ median as `scores[len(scores) // 2]` on a *sorted* list. For an
even number of regions that returns the UPPER of the two central values, biasing
the reported median high. The fix routes the computation through
`statistics.median` via the module helper `_riq_median`.
"""
import statistics

from mamey.antismash_evidence import _riq_median


def test_even_length_averages_two_middle():
    # old code: sorted([1,2,3,4])[4//2] == 3.0  ->  wrong
    assert _riq_median([1.0, 2.0, 3.0, 4.0]) == 2.5


def test_odd_length_is_the_middle_value():
    assert _riq_median([1.0, 2.0, 3.0]) == 2.0


def test_documents_the_old_bug_value():
    scores = sorted([10.0, 20.0, 30.0, 40.0])
    assert scores[len(scores) // 2] == 30.0   # the OLD (wrong) result
    assert _riq_median(scores) == 25.0        # the NEW (correct) result


def test_matches_stdlib_statistics_median():
    xs = [3.0, 1.0, 4.0, 1.0, 5.0, 9.0]       # unsorted on purpose
    assert _riq_median(xs) == statistics.median(xs)


def test_single_region_is_that_value():
    assert _riq_median([7.5]) == 7.5
