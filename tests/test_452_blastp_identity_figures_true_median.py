"""Card 018c0f08_452_blastp_identity_figures_true_median.

The BLASTp identity figures quoted the upper middle value as the "median" (sorted(v)[len(v) // 2], from the bee paper's v6
script), which overstates the median of an even count. The tables and panel titles now give the true median.
"""
import importlib.util
import statistics
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"


def _tool():
    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))
    spec = importlib.util.spec_from_file_location("bif_t452m", TOOLS / "blastp_identity_figures.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_even_count_takes_the_mean_of_the_two_middle_values():
    bif = _tool()
    assert bif.median([88.0, 95.0]) == 91.5
    assert bif.median([60.0, 70.0, 80.0, 90.0]) == 75.0
    assert bif.median([1.0, 2.0, 9.0]) == 2.0
    assert bif.median([3.0, 1.0, 4.0, 1.0, 5.0, 9.0]) == statistics.median([3.0, 1.0, 4.0, 1.0, 5.0, 9.0])


def test_no_upper_median_left_in_the_tool():
    src = (TOOLS / "blastp_identity_figures.py").read_text()
    assert "upper_median" not in src and "[len(v) // 2]" not in src.split('"""')[-1]
