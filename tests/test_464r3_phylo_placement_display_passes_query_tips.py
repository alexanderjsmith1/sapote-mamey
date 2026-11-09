"""placement_display --query-tips: the exact query list reaches the builder command and the
in-process role checks; a name that is not a tip of the admitted tree is refused before the builder.
Reuses the restored-graft fixture; the builder boundary is intercepted, so nothing is rendered."""
from pathlib import Path
from types import SimpleNamespace

import pytest

pytest.importorskip("Bio.Phylo")
from tools import placement_display as display
from .test_m5_restored_graft_receipt import produce


def _args(run, out, *extra):
    return [str(run), "--name", "synthetic", "--group", "Example", "--host-table", str(run / "host.tsv"),
            "--ref-source-db", str(run / "sources.sqlite"), "--out", str(out), "--outgroup-substr", "OG", *extra]


def _setup(tmp_path, monkeypatch):
    run, report, sources, calls, admitted = produce(tmp_path, monkeypatch, default=True)
    (run / "host.tsv").write_text("strain\taccession\n")
    (run / "sources.sqlite").write_text("synthetic metadata boundary only")
    builder = SimpleNamespace(_is_query=lambda name: name in (builder._QUERY_TIPS or ()), _QUERY_TIPS=None,
                              _ref_accession=lambda name: name, _asid=lambda name: name,
                              reference_genera=lambda *a: {"Example"})
    original_load = display._load
    monkeypatch.setattr(display, "_load", lambda name: builder if name == "build_placement_ggtree_inputs" else original_load(name))
    monkeypatch.setattr(display, "_reference_organisms", lambda *a: {})
    invoked = []

    def boundary(argv, env=None):
        invoked.append(argv)
        raise ValueError("INTENTIONAL_BUILD_BOUNDARY_STOP")
    monkeypatch.setattr(display, "_run", boundary)
    return run, builder, invoked


def test_query_tips_reach_the_builder_command(tmp_path, monkeypatch):
    run, builder, invoked = _setup(tmp_path, monkeypatch)
    qt = tmp_path / "queries.txt"
    qt.write_text("QUERY\n")
    assert display.main(_args(run, tmp_path / "display", "--query-tips", str(qt))) == 2
    assert len(invoked) == 1
    argv = invoked[0]
    assert argv[argv.index("--query-tips") + 1] == str(qt.resolve())
    assert builder._QUERY_TIPS == frozenset({"QUERY"})


def test_unknown_query_tip_is_refused_before_the_builder(tmp_path, monkeypatch, caplog):
    run, builder, invoked = _setup(tmp_path, monkeypatch)
    qt = tmp_path / "queries.txt"
    qt.write_text("NOT_A_TIP\n")
    assert display.main(_args(run, tmp_path / "display", "--query-tips", str(qt))) == 2
    assert invoked == []
    assert not (tmp_path / "display").exists()
    assert "QUERY_TIPS_NOT_IN_TREE" in caplog.text
