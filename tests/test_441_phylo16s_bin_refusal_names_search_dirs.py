"""v9.7.441 card 283f1f96: when a placement binary is absent, tools/_phylo16s._bin names every
location it looked in and the root it resolved, instead of telling the operator to install software."""
import importlib.util, pathlib, sys
import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load():
    spec = importlib.util.spec_from_file_location("_phylo16s", ROOT / "tools" / "_phylo16s.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def test_refusal_lists_search_locations(tmp_path, monkeypatch):
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.delenv("MAFFT_BIN", raising=False); monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    m = _load()
    with pytest.raises(SystemExit) as e:
        m.mafft_bin()
    msg = str(e.value)
    assert "Looked in" in msg and "PATH" in msg
    assert str(tmp_path / "miniconda3/envs/placement/bin/mafft") in msg
    assert f"resolves to {tmp_path}" in msg


def test_found_in_workspace_env_dir(tmp_path, monkeypatch):
    b = tmp_path / "miniconda3/envs/placement/bin"; b.mkdir(parents=True); (b / "mafft").write_text("#!/bin/sh\n")
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path)); monkeypatch.delenv("MAFFT_BIN", raising=False)
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    assert _load().mafft_bin() == str(b / "mafft")
