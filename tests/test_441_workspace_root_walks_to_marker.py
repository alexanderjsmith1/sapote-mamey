"""v9.7.441 card 283f1f96: workspace_root() climbs from a CODE bundle nested inside its workspace to
the nearest parent holding a workspace marker (miniconda3/, blast_dbs/, Tools/databases/); OFFICIAL_DATA is NOT a marker because the bundle ships one. With no
marker anywhere the historical cwd fallback is byte-identical; an env var still wins."""
from pathlib import Path
import mamey.workspace_root as WR


def test_walks_up_to_marker(tmp_path, monkeypatch):
    ws = tmp_path / "workspace"; (ws / "blast_dbs").mkdir(parents=True)
    bundle = ws / "sapote-mamey-vX-CODE"; bundle.mkdir()
    monkeypatch.delenv("SAPOTE_WORKSPACE_ROOT", raising=False); monkeypatch.delenv("SAPOTE_ROOT", raising=False)
    monkeypatch.chdir(bundle)
    assert WR.workspace_root().resolve() == ws.resolve()


def test_no_marker_keeps_cwd(tmp_path, monkeypatch):
    d = tmp_path / "plain"; d.mkdir()
    monkeypatch.delenv("SAPOTE_WORKSPACE_ROOT", raising=False); monkeypatch.delenv("SAPOTE_ROOT", raising=False)
    monkeypatch.chdir(d)
    assert WR.workspace_root().resolve() == d.resolve()


def test_env_var_still_wins(tmp_path, monkeypatch):
    ws = tmp_path / "ws"; (ws / "miniconda3").mkdir(parents=True)
    other = tmp_path / "elsewhere"; other.mkdir()
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(other)); monkeypatch.chdir(ws)
    assert WR.workspace_root() == Path(str(other))


def test_bundle_official_data_does_not_stop_the_walk(tmp_path, monkeypatch):
    ws = tmp_path / "workspace"; (ws / "miniconda3").mkdir(parents=True)
    bundle = ws / "bundle"; (bundle / "OFFICIAL_DATA").mkdir(parents=True)   # bundles ship their own OFFICIAL_DATA
    monkeypatch.delenv("SAPOTE_WORKSPACE_ROOT", raising=False); monkeypatch.delenv("SAPOTE_ROOT", raising=False)
    monkeypatch.chdir(bundle)
    assert WR.workspace_root().resolve() == ws.resolve()
