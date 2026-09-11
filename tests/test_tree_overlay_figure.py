"""Tests for tools/tree_overlay_figure.py — the one-tree/many-overlay-matrices figure generator.

Renders need matplotlib + Bio (present in the workspace figure env, skipped where absent), so the
render tests importorskip; the binding/validation HOLDs are the contract that matters most and are
asserted directly.
"""
from __future__ import annotations

import importlib.util
import json
import os

import pytest

pytest.importorskip("matplotlib")
pytest.importorskip("Bio")

_TOOL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "tools", "tree_overlay_figure.py")


def _load():
    spec = importlib.util.spec_from_file_location("_tree_overlay_figure", _TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


TREE = "((A_study:0.1,B_study:0.12)95/98:0.05,(C_ref:0.11,D_ref:0.1)90/91:0.04,OG_x_OUTGROUP:0.3);"
FOOTER = ("Class-level antiSMASH inventory (capacity, not function); grey = not profiled; "
          "similarity is not identity; judgment deferred.")


def _stage(tmp_path, *, crosswalk_rows, matrix_rows, matrix_header, overlays=None, footer=FOOTER):
    (tmp_path / "t.nwk").write_text(TREE)
    with open(tmp_path / "cw.tsv", "w") as fh:
        fh.write("newick_label\tdisplay_label\trole\n")
        for r in crosswalk_rows:
            fh.write("\t".join(r) + "\n")
    with open(tmp_path / "m.tsv", "w") as fh:
        fh.write("\t".join(matrix_header) + "\n")
        for r in matrix_rows:
            fh.write("\t".join(str(x) for x in r) + "\n")
    cfg = {"tree": "t.nwk", "outgroup_substring": "OUTGROUP", "crosswalk": "cw.tsv",
           "out_dir": "out", "out_stem": "T", "figure_title": "t", "tree_caption": "c",
           "claim_footer": footer,
           "overlays": overlays or [{"id": "m", "title": "M", "matrix": "m.tsv"}]}
    (tmp_path / "c.json").write_text(json.dumps(cfg))
    return tmp_path / "c.json"


_FULL_CW = [("A_study", "A", "STUDY"), ("B_study", "B", "STUDY"),
            ("C_ref", "C", "REFERENCE"), ("D_ref", "D", "REFERENCE"),
            ("OG_x_OUTGROUP", "OG", "OUTGROUP")]


def test_builds_one_figure_per_overlay(tmp_path):
    mod = _load()
    cfg = _stage(tmp_path,
                 crosswalk_rows=_FULL_CW,
                 matrix_header=["tip", "PKS", "NRPS"],
                 matrix_rows=[["A_study", 3, 5], ["B_study", 1, 2]],
                 overlays=[{"id": "cls", "title": "classes", "matrix": "m.tsv"},
                           {"id": "cls2", "title": "again", "matrix": "m.tsv", "colormap": "PuRd"}])
    receipts = mod.build(cfg)
    assert len(receipts) == 2
    for r in receipts:
        assert r["n_tips"] == 5 and r["n_profiled"] == 2 and r["n_unprofiled"] == 3
        for out in r["outputs"]:
            assert (tmp_path / "out" / out).is_file()


def test_missing_crosswalk_row_is_a_hard_hold(tmp_path):
    """A tree tip with no crosswalk row must HOLD — never a silent drop (the gossypii trap)."""
    mod = _load()
    cfg = _stage(tmp_path,
                 crosswalk_rows=_FULL_CW[:-1],   # drop the outgroup row
                 matrix_header=["tip", "PKS"], matrix_rows=[["A_study", 3]])
    with pytest.raises(mod.OverlayHold) as e:
        mod.build(cfg)
    assert "no crosswalk row" in str(e.value)


def test_unprofiled_tip_is_kept_as_not_profiled_by_default(tmp_path):
    mod = _load()
    cfg = _stage(tmp_path, crosswalk_rows=_FULL_CW,
                 matrix_header=["tip", "PKS"], matrix_rows=[["A_study", 3]])
    r = mod.build(cfg)[0]
    assert r["n_profiled"] == 1 and r["n_unprofiled"] == 4


def test_omit_unprofiled_flag(tmp_path):
    mod = _load()
    cfg = _stage(tmp_path, crosswalk_rows=_FULL_CW,
                 matrix_header=["tip", "PKS"], matrix_rows=[["A_study", 3], ["B_study", 4]],
                 overlays=[{"id": "m", "title": "M", "matrix": "m.tsv", "omit_unprofiled": True}])
    r = mod.build(cfg)[0]
    assert r["n_profiled"] == 2  # still reports profiled honestly; drawing drops the rest


def test_blank_footer_is_rejected(tmp_path):
    mod = _load()
    cfg = _stage(tmp_path, crosswalk_rows=_FULL_CW,
                 matrix_header=["tip", "PKS"], matrix_rows=[["A_study", 3]], footer="short")
    with pytest.raises(mod.OverlayHold):
        mod.build(cfg)


def test_invalid_role_is_rejected(tmp_path):
    mod = _load()
    bad = [("A_study", "A", "BOGUS")] + _FULL_CW[1:]
    cfg = _stage(tmp_path, crosswalk_rows=bad,
                 matrix_header=["tip", "PKS"], matrix_rows=[["A_study", 3]])
    with pytest.raises(mod.OverlayHold):
        mod.build(cfg)
