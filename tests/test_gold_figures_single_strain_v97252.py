"""v9.7.252 (P8) — a single-strain gold run emitted 2 figures instead of 21.

`_emit_gold_figures` called `cohort_figures.generate()` without `series=`, and the default is `"F"`.
So the G-series (8 panels) and D-series (11) were never requested. The capability existed; nothing
invoked it — the same shape as `--from-precompute`, `--hits`, `--strict-paths`, and `DEFAULT_BATCH`.

`_run_all_g` then ran batches 3-4 unconditionally. Those index a correlation matrix with
`~np.eye(...)`; at n=1 the off-diagonal is an EMPTY slice, so the cross-strain similarity and
product-class co-occurrence panels are meaningless (NaN) — they need >=2 strains. Guarded.
"""
import inspect
import pathlib
import sys

import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mamey import cohort_figures as cf
from mamey import cli as _cli


def test_gold_run_requests_every_series():
    src = inspect.getsource(_cli)
    i = src.find("_gen_single_figs(")
    assert i != -1, "the gold-figure call site moved"
    call = src[i:i + 260]
    assert 'series="all"' in call, "gold runs must request F + G + D, not the series='F' default"


def test_generate_defaults_to_F_so_the_explicit_argument_matters():
    assert inspect.signature(cf.generate).parameters["series"].default == "F"


def test_run_all_g_skips_cross_strain_batches_on_a_single_strain(monkeypatch):
    called = []
    monkeypatch.setattr(cf, "BATCHES", {b: (lambda *a, _b=b, **k: called.append(_b)) for b in (1, 2, 3, 4)})
    monkeypatch.setattr(cf, "GNUM", [0])
    monkeypatch.setattr(cf.glob, "glob", lambda *a, **k: [])
    cf._run_all_g({}, ["AS-696"], "/tmp")
    assert called == [1, 2], "batches 3-4 have no cross-strain data at n=1"


def test_run_all_g_runs_every_batch_for_two_or_more_strains(monkeypatch):
    called = []
    monkeypatch.setattr(cf, "BATCHES", {b: (lambda *a, _b=b, **k: called.append(_b)) for b in (1, 2, 3, 4)})
    monkeypatch.setattr(cf, "GNUM", [0])
    monkeypatch.setattr(cf.glob, "glob", lambda *a, **k: [])
    cf._run_all_g({}, ["AS-696", "AS-421"], "/tmp")
    assert called == [1, 2, 3, 4], "multi-strain behaviour must be unchanged"


def test_single_strain_offdiagonal_is_empty_which_is_why_the_guard_exists():
    m = np.array([[1.0]])
    assert m[~np.eye(1, dtype=bool)].size == 0
