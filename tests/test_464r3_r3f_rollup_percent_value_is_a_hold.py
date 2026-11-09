"""A percent-signed or digit-underscore tier value is a numeric hold, not a number.

`0.9%` read as the fraction 0.9 is 100 times too large, `4%` is not a count, and Python reads
`1_0` as 10. Each holds the pair at NEEDS-REVIEW. Synthetic rows only.
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("rollup_464r3f", ROOT / "tools/rggmci_cohort_rollup.py")
RR = importlib.util.module_from_spec(spec)
spec.loader.exec_module(RR)

BASE = {"pair": "p1", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE", "subject_tiling_verdict": "COMPLEMENTARY_SPLIT",
        "terminus_override_note": "", "rggmci_score": "30", "complementary_disjoint_refs": "4",
        "n_shared_subjects": "1", "a_core_fraction": "0.3", "b_core_fraction": "0.3", "interpretation_guard": ""}


@pytest.mark.parametrize("key,value", [("a_core_fraction", "0.9%"), ("b_core_fraction", "30%"),
                                       ("complementary_disjoint_refs", "4%"),
                                       ("complementary_disjoint_refs", "1_0"), ("n_shared_subjects", "0_1"),
                                       ("a_core_fraction", "0_5")])
def test_percent_or_underscore_value_is_held(key, value):
    row = dict(BASE, **{key: value})
    assert RR.numeric_holds(row) == [f"{key}:malformed"]
    assert RR.confidence_tier(row) == "NEEDS-REVIEW"


def test_plain_values_are_still_admitted():
    assert RR.numeric_holds(BASE) == []
