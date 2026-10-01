"""445: phylo_place must not create strain_data/ at the workspace root.

With no --refpkg, build-ref (and `all`) wrote the reference package to
`<workspace>/strain_data/_PLACEMENT/<group>/refpkg`, a stray top-level folder, even when --outdir named a
different home. The refpkg now goes to `<outdir>/refpkg` when --outdir is given, else to the tree home
`<workspace>/trees/_PLACEMENT/<group>/refpkg`. `mafft` is stubbed away so build-ref stops right
after it creates its output folder; no aligner or tree builder runs.
"""
import argparse
import importlib.util as ilu
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _tool(monkeypatch, ws):
    monkeypatch.delenv("SAPOTE_TREE_HOME", raising=False)
    spec = ilu.spec_from_file_location("phylo_place_445", ROOT / "tools" / "phylo_place.py")
    pp = ilu.module_from_spec(spec); spec.loader.exec_module(pp)
    monkeypatch.setattr(pp, "ROOT", str(ws))
    monkeypatch.setattr(pp, "_which", lambda *a, **k: None)   # stop at "mafft not found"
    return pp


def _args(tmp_path, **kw):
    ref = tmp_path / "ref.fasta"; ref.write_text(">TST-1\nACGTACGTACGTACGT\n>TST-2\nACGTACGTACGTACGA\n")
    base = dict(ref_fasta=str(ref), group="rare_genera", refpkg=None, outdir=None, approved_by="test",
                threads="1", bootstrap=1, add_outgroup="", outgroup_scope="genus")
    base.update(kw); return argparse.Namespace(**base)


def test_build_ref_with_outdir_writes_refpkg_under_outdir(tmp_path, monkeypatch):
    ws = tmp_path / "ws"; ws.mkdir(); out = tmp_path / "scratch" / "place"
    pp = _tool(monkeypatch, ws)
    with pytest.raises(SystemExit):
        pp.cmd_build_ref(_args(tmp_path, outdir=str(out)))
    assert not (ws / "strain_data").exists(), "refpkg must not create strain_data/ at the workspace root"
    assert (out / "refpkg").is_dir()


def test_build_ref_without_outdir_uses_the_tree_home(tmp_path, monkeypatch):
    ws = tmp_path / "ws"; ws.mkdir()
    pp = _tool(monkeypatch, ws)
    with pytest.raises(SystemExit):
        pp.cmd_build_ref(_args(tmp_path))
    assert not (ws / "strain_data").exists()
    assert (ws / "trees" / "_PLACEMENT" / "rare_genera" / "refpkg").is_dir()


def test_all_keeps_the_refpkg_beside_its_placements(tmp_path, monkeypatch):
    ws = tmp_path / "ws"; ws.mkdir(); out = tmp_path / "scratch" / "place"
    pp = _tool(monkeypatch, ws)
    with pytest.raises(SystemExit):
        pp.cmd_all(_args(tmp_path, outdir=str(out), query=str(tmp_path / "q.fasta")))
    assert not (ws / "strain_data").exists()
    assert (out / "refpkg").is_dir()


def test_explicit_refpkg_still_wins(tmp_path, monkeypatch):
    ws = tmp_path / "ws"; ws.mkdir(); mine = tmp_path / "my_refpkg"
    pp = _tool(monkeypatch, ws)
    with pytest.raises(SystemExit):
        pp.cmd_build_ref(_args(tmp_path, refpkg=str(mine), outdir=str(tmp_path / "elsewhere")))
    assert mine.is_dir() and not (ws / "strain_data").exists()
    assert not (tmp_path / "elsewhere" / "refpkg").exists()
