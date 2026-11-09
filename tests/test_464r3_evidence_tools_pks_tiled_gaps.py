"""TILED is an order/overlap call; gaps are reported beside it."""
import importlib.util
from pathlib import Path

TOOL = Path(__file__).resolve().parents[1] / "tools" / "pks_piece_map.py"


def _module():
    spec = importlib.util.spec_from_file_location("ppm_464r3", TOOL)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def test_large_gap_is_still_tiled_but_gap_is_reported():
    m = _module()
    pieces = [{"ref_start": 1, "ref_end": 100}, {"ref_start": 900, "ref_end": 1000}]
    assert m.call_protein(pieces, 30)[0] == "TILED"
    assert m.reference_gaps(pieces, 1200) == [799, 200]


def test_single_piece_gaps_include_both_ends():
    m = _module()
    assert m.reference_gaps([{"ref_start": 50, "ref_end": 100}], 200) == [49, 100]
    assert m.reference_gaps([], 200) == []
