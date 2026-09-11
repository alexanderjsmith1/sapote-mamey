"""RV-2 (v9.7.253 Review v2): pin the concordance weights to sum to 1.0.

`tools/fragment_concordance_scorer.py` combines four weighted similarity dimensions
(region/markers/domains/size). The weights are a documented heuristic rubric — fine — but if a
future edit changes one and breaks the sum-to-1 normalization, every concordance score silently
skews with no error. This is XS insurance on a documented-but-tunable constant.
"""
import importlib.util
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
_p = _REPO / "tools" / "fragment_concordance_scorer.py"
sys.path.insert(0, str(_p.parent))
sys.path.insert(0, str(_REPO))
_spec = importlib.util.spec_from_file_location("fragment_concordance_scorer_ut", _p)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)


def test_weights_sum_to_one():
    assert round(sum(_mod.W.values()), 6) == 1.0, f"concordance weights must sum to 1.0, got {_mod.W}"


def test_weight_keys_are_the_four_dimensions():
    assert set(_mod.W) == {"region", "markers", "domains", "size"}


def test_tiers_are_descending_and_bounded():
    thresholds = [t for t, _ in _mod.TIERS]
    assert thresholds == sorted(thresholds, reverse=True), "TIERS must be in descending threshold order"
    assert thresholds[0] <= 1.0 and thresholds[-1] >= 0.0
