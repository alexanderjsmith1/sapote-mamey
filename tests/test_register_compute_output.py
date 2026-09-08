"""Tests for the formal register-after-running step (recompute-gate root-cause fix).

Every test uses a throwaway tmp root — the live OFFICIAL_DATA/ASSET_REGISTRY.tsv is never touched.
"""
import importlib.util
from pathlib import Path

import pytest

# load the tool by path so the test runs whether it ships as tools/register_compute_output.py or staged
_SPEC_CANDIDATES = [
    Path(__file__).resolve().parent / "tools_register_compute_output.py",
    Path(__file__).resolve().parents[1] / "tools" / "register_compute_output.py",
]


def _load():
    for p in _SPEC_CANDIDATES:
        if p.exists():
            spec = importlib.util.spec_from_file_location("register_compute_output", p)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    pytest.skip("register_compute_output.py not found")


def _mk_root(tmp_path: Path) -> Path:
    (tmp_path / "OFFICIAL_DATA").mkdir(parents=True)
    reg = tmp_path / "OFFICIAL_DATA" / "ASSET_REGISTRY.tsv"
    reg.write_text("asset_id\ttype\tpath\tsize\tguard_tokens\tdescription\n", encoding="utf-8")
    (tmp_path / "BigSCAPE").mkdir()
    return tmp_path


def test_registers_a_new_result(tmp_path):
    mod = _load()
    root = _mk_root(tmp_path)
    status, _ = mod.register_result("BigSCAPE", "bigscape_gcf_results", "computed_result",
                                    "bigscape -|run_bigscape", "COMPUTED RESULTS - DO NOT RE-RUN", root=root)
    assert status == "registered"
    txt = (root / "OFFICIAL_DATA" / "ASSET_REGISTRY.tsv").read_text()
    assert "bigscape_gcf_results" in txt
    assert txt.count("bigscape_gcf_results") == 1


def test_idempotent_on_same_id(tmp_path):
    mod = _load()
    root = _mk_root(tmp_path)
    mod.register_result("BigSCAPE", "bigscape_gcf_results", "computed_result", "t", "d", root=root)
    status, msg = mod.register_result("BigSCAPE", "bigscape_gcf_results", "computed_result", "t", "d", root=root)
    assert status == "exists_id"
    # no duplicate row written
    txt = (root / "OFFICIAL_DATA" / "ASSET_REGISTRY.tsv").read_text()
    assert txt.count("bigscape_gcf_results") == 1


def test_idempotent_on_same_path_different_id(tmp_path):
    mod = _load()
    root = _mk_root(tmp_path)
    mod.register_result("BigSCAPE", "first_id", "computed_result", "t", "d", root=root)
    status, _ = mod.register_result("BigSCAPE", "second_id", "computed_result", "t", "d", root=root)
    assert status == "exists_path"
    txt = (root / "OFFICIAL_DATA" / "ASSET_REGISTRY.tsv").read_text()
    assert "second_id" not in txt  # path already claimed -> no-op, no clobber


def test_row_is_tab_shaped_with_six_columns(tmp_path):
    mod = _load()
    root = _mk_root(tmp_path)
    mod.register_result("BigSCAPE", "x", "computed_result", "a|b", "desc with spaces", root=root)
    last = (root / "OFFICIAL_DATA" / "ASSET_REGISTRY.tsv").read_text().splitlines()[-1]
    assert len(last.split("\t")) == 6


def test_tabs_and_newlines_in_desc_are_sanitized(tmp_path):
    mod = _load()
    root = _mk_root(tmp_path)
    mod.register_result("BigSCAPE", "x", "computed_result", "tok", "line1\twith tab\nand newline", root=root)
    lines = [ln for ln in (root / "OFFICIAL_DATA" / "ASSET_REGISTRY.tsv").read_text().splitlines() if ln.strip()]
    # exactly header + one data row; the desc did not split into extra columns/rows
    assert len(lines) == 2
    assert len(lines[1].split("\t")) == 6
