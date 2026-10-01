"""DIAMOND sensitivity and the core-only identity floor for tools/gap_directed_rescue.py.

Alex, 2026-09-30, on an AS nucleoside cluster with no KnownClusterBlast hit: "it isn't fragmented but it is real with low
homology". Against its closest MIBiG cluster, DIAMOND's default (fast) mode found 4 of 12 genes; --sensitive and
--ultra-sensitive found 6, the two extra at 28-32% identity. One of those sits under the 30% floor, so inside the core a
25% match now counts when its e-value is 1e-10 or better.
"""
import importlib.util
import sys
import types
from pathlib import Path

import pytest

from mamey import diamond_align as da

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
spec = importlib.util.spec_from_file_location("split_gene_check_helpers", ROOT / "tests/test_445_gap_rescue_split_gene_check.py")
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)


def test_the_cli_path_passes_the_requested_mode_and_keeps_the_default_unchanged(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(da.shutil, "which", lambda exe: "/usr/bin/diamond")
    monkeypatch.setattr(da.subprocess, "run", lambda argv, **kw: calls.append(argv))
    q, r = tmp_path / "q.faa", tmp_path / "r.faa"
    q.write_text(">a\nMA\n"); r.write_text(">b\nMA\n")
    da._align_fasta_cli(str(q), str(r), 1, 0.0, 0.0, "ultra-sensitive")
    assert "--ultra-sensitive" in calls[-1]
    da._align_fasta_cli(str(q), str(r), 1, 0.0, 0.0)
    assert not any(a.endswith("sensitive") for a in calls[-1])


def test_the_binding_path_passes_the_mode(monkeypatch):
    seen = []
    fake = types.ModuleType("diamond4py.libdiamond")
    monkeypatch.setattr(fake, "main", lambda *args: seen.append(args), raising=False)
    monkeypatch.setitem(sys.modules, "diamond4py", types.ModuleType("diamond4py"))
    monkeypatch.setitem(sys.modules, "diamond4py.libdiamond", fake)
    da._run_diamond_blastp_raw("db", "q.faa", "out.tsv", 1, "sensitive")
    assert "--sensitive" in seen[-1]


def test_an_unknown_mode_is_refused_before_any_work():
    with pytest.raises(ValueError):
        da.align_fasta("missing.faa", "missing.faa", sensitivity="turbo")


def test_the_tool_asks_for_ultra_sensitive_by_default(monkeypatch):
    got = {}
    monkeypatch.setattr(da, "align_fasta", lambda q, r, **kw: got.update(kw) or {"ok": True, "hits": []})
    helpers.gdr.run_diamond([{"id": "g001", "aa": "MA"}], {"q000001": {"aa": "MA"}}, 1)
    assert got["sensitivity"] == "ultra-sensitive"


@pytest.mark.parametrize("pident, evalue, expected", [
    (27.0, 1e-20, "PRESENT_IN_CORE"),       # weak but strong alignment, inside the core: counts
    (27.0, 1e-5, "MISSING_NOT_FOUND"),      # weak and weak: does not
    (31.0, 1e-5, "PRESENT_IN_CORE"),        # the 30% floor is unchanged
])
def test_a_weak_match_counts_inside_the_core_only_with_a_strong_evalue(tmp_path, pident, evalue, expected):
    rows = helpers.BASE + [("g003", "q000003", pident, 90, 150, 1, 280, evalue)]
    table, _, _, _ = helpers._run(tmp_path, rows)
    assert table["r3"]["status"] == expected


def test_a_weak_match_outside_the_core_is_not_a_find(tmp_path):
    rows = helpers.BASE + [("g003", "q000007", 27.0, 90, 150, 1, 280, 1e-30)]
    table, _, _, _ = helpers._run(tmp_path, rows)
    assert table["r3"]["status"] == "MISSING_NOT_FOUND"


def test_without_an_evalue_column_the_30_percent_floor_holds_in_the_core(tmp_path):
    rows = helpers.BASE + [("g003", "q000003", 27.0, 90, 150, 1, 280)]
    table, _, _, _ = helpers._run(tmp_path, rows)
    assert table["r3"]["status"] == "MISSING_NOT_FOUND"
