"""Sparse class tables do not prove that absent combinations were measured zero."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('plot_examples_under_test', ROOT / 'tools/plot_examples.py')
plot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plot)


def test_missing_pair_is_masked_even_when_other_class_was_reported():
    grid = plot._heatmap_grid([
        {'strain': 'X', 'product_class': 'NRPS', 'n_bgcs': '2'},
        {'strain': 'Y', 'product_class': 'NRPS', 'n_bgcs': '0'},
        {'strain': 'Y', 'product_class': 'RiPP', 'n_bgcs': '3'},
    ], ['X', 'Y'], ['NRPS', 'RiPP'])
    assert grid.mask.tolist() == [[False, False], [True, False]]
    assert int(grid[0, 1]) == 0
    assert int(grid[1, 1]) == 3


def test_duplicate_pairs_are_refused():
    import pytest
    row = {'strain': 'X', 'product_class': 'NRPS', 'n_bgcs': '1'}
    with pytest.raises(ValueError, match='duplicate class/strain'):
        plot._heatmap_grid([row, row], ['X'], ['NRPS'])
