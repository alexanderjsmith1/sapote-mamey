"""An over-long protein pair that was not aligned is reported as unmeasured, not as a weak match.

Before: the skipped pair's placeholder zeros were classified WEAK_CLOSEST_AVAILABLE.
"""
from mamey import cohort_proteins as cp


def test_skipped_pair_is_unmeasured(monkeypatch):
    monkeypatch.setattr(cp, "_max_align_aa", lambda: 10)
    metrics = cp._metrics(None, "M" * 20, "M" * 20)   # over the cap: never reaches the aligner
    assert metrics["alignment_skipped"]
    assert cp._comparison_state(metrics) == "ALIGNMENT_SKIPPED_UNMEASURED"


def test_measured_low_identity_is_still_weak():
    assert cp._comparison_state({"identity_pct": 20.0, "query_coverage_pct": 30.0,
                                 "subject_coverage_pct": 30.0}) == "WEAK_CLOSEST_AVAILABLE"
