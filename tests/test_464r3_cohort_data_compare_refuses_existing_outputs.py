"""compare_catalog refuses to replace an earlier comparison in the same --outdir."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from mamey.cohort_proteins import build_catalog, compare_catalog

_spec = importlib.util.spec_from_file_location(
    "_cohort_fixture_464r3c", Path(__file__).resolve().parent / "test_cohort_proteins_v9_7_377.py")
_fx = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_fx)

CORE = "MKTAYIAKQRQISFVKSHFSRQDILDLWIYHTQGYFP"


def _setup(tmp_path: Path):
    a = tmp_path / "a"
    pkg = _fx._write_package(a, "STRAIN_Q", "NODE_1", "region001", "BGC001", [("q1", "core synthase", CORE)])
    _fx._write_package(a, "STRAIN_R", "NODE_2", "region002", "BGC002", [("r1", "core synthase", CORE[:-1] + "A")])
    database = tmp_path / "catalog.sqlite"
    build_catalog([("COHORT_A", a)], database)
    return database, pkg


def test_second_run_into_same_outdir_is_refused_and_keeps_first(tmp_path):
    database, pkg = _setup(tmp_path)
    out = tmp_path / "out"
    first = compare_catalog(database, pkg, "BGC001", out)
    receipt = Path(first["receipt_path"])
    receipt.write_text("edited by the user\n", encoding="utf-8")
    before = {p.name: p.read_bytes() for p in out.iterdir()}
    with pytest.raises(ValueError):
        compare_catalog(database, pkg, "BGC001", out)
    assert {p.name: p.read_bytes() for p in out.iterdir()} == before


def test_receipt_hashes_name_the_published_paths(tmp_path):
    database, pkg = _setup(tmp_path)
    out = tmp_path / "out"
    (out).mkdir()
    (out / "unrelated.txt").write_text("other work", encoding="utf-8")
    result = compare_catalog(database, pkg, "BGC001", out)
    saved = json.loads(Path(result["receipt_path"]).read_text(encoding="utf-8"))
    assert len(saved["artifacts"]) == 3
    for path in saved["artifacts"]:
        assert Path(path).parent == out.resolve() and Path(path).is_file()
    assert (out / "unrelated.txt").read_text(encoding="utf-8") == "other work"
    assert sorted(p.name for p in out.iterdir() if p.name != "unrelated.txt") == sorted(
        p.name for p in out.iterdir() if "__" in p.name)
