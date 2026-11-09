# Synthetic regression inputs only.
"""Wet-lab priorities are NOT_EVALUATED when their input is missing, and an xlsx write error is reported.

Before: a missing boundary, bldA tier or similarity/RiQ input gave LOW, a measured-looking state; a
non-numeric RiQ crashed the run; and any spreadsheet error printed "xlsx skipped" as if openpyxl
were absent.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
_spec = importlib.util.spec_from_file_location("build_wetlab_matrix_464r3b", ROOT / "tools" / "build_wetlab_matrix.py")
wl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wl)

OBS = "KNOWNCLUSTERBLAST_OBSERVED"


def test_missing_inputs_give_not_evaluated_not_low():
    seq, act, iso, der = wl.action_scores({}, 0, None)
    assert (seq, act, der) == ("NOT_EVALUATED", "NOT_EVALUATED", "NOT_EVALUATED")
    assert iso == "LOW"  # the score itself is computed


def test_non_actinomycete_bldA_is_not_evaluated():
    assert wl.action_scores({"edge_status": "Interior"}, 0, "NOT_APPLICABLE")[1] == "NOT_EVALUATED"


def test_read_inputs_that_miss_the_rule_are_low():
    b = {"edge_status": "Interior", "kcb_similarity_pct": 10, "kcb_evidence_state": OBS, "riq_score": 0.2}
    assert wl.action_scores(b, 0, "T1") == ("LOW", "LOW", "LOW", "LOW")


def test_non_numeric_riq_is_missing_not_a_crash():
    base, terms, notes = wl.score_bgc({"edge_status": "Interior", "riq_score": "n.t."}, "T1")
    assert not any("RiQ" in t for t, _, _ in terms)
    assert any("RiQ: unreadable" in n for n in notes)
    assert wl.action_scores({"edge_status": "Interior", "riq_score": "n.t."}, base, "T1")[3] == "NOT_EVALUATED"


def test_xlsx_write_error_is_reported_and_fails(tmp_path, monkeypatch, capsys):
    pytest.importorskip("openpyxl")
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain_id": "SYN", "bgcs": [
        {"bgc_id": "BGC001", "edge_status": "Interior", "products": ["NRPS"]}]}), encoding="utf-8")

    def boom(*a, **k):
        raise PermissionError("read-only")

    monkeypatch.setattr(wl, "atomic_save", boom)
    monkeypatch.setattr(sys, "argv", ["x", "--package-dir", str(pkg), "--out-dir", str(tmp_path / "out")])
    with pytest.raises(SystemExit) as exc:
        wl.main()
    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "xlsx FAILED: PermissionError" in out and "skipped" not in out
    assert (tmp_path / "out" / "SYN_WetLab_Decision_Matrix.csv").is_file()
