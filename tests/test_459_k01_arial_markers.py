"""The K01 6-inch fit checks depend on real Arial widths, so they carry the needs_arial marker.

Linux CI maps "Arial" to Liberation Sans, which measures wider; without the marker the three 6 in
cases fail there (v9.7.458 CI run) although they pass on the M3 and in the cut.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("k01_tests", ROOT / "tests" / "test_458_k01_left_margin_from_labels.py")


def _marks(obj):
    return {m.name for m in getattr(obj, "pytestmark", [])}


def test_six_inch_fit_checks_need_arial():
    src = (ROOT / "tests" / "test_458_k01_left_margin_from_labels.py").read_text()
    for name in ("test_long_row_note_does_not_touch_the_band_label_at_6in",
                 "test_no_text_run_touches_another_or_leaves_the_page_at_6in"):
        before = src.split(f"def {name}")[0].rstrip().splitlines()[-1]
        assert "needs_arial" in before, name
    assert "pytest.param(6.0, marks=pytest.mark.needs_arial)" in src
