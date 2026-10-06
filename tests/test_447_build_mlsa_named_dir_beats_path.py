"""tools/build_mlsa.py resolve_bin: a binary in --bin-dir / MAMEY_PHYLO_BIN beats any alias on PATH.

fresh-clone audit, 2026-10-01 (D5): with Debian's /usr/bin/iqtree2 installed, resolve_bin checked PATH for
iqtree3 and iqtree2 before reaching --bin-dir/iqtree, so the user's binary (and the fail-closed tests' stub) was never
used and three tests failed on any machine with IQ-TREE installed.
"""
import importlib.util
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("build_mlsa", ROOT / "tools/build_mlsa.py")
bm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bm)


def _exe(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/sh\nexit 0\n")
    path.chmod(0o755)
    return path


def test_named_dir_iqtree_beats_an_iqtree2_on_path(tmp_path, monkeypatch):
    mine = _exe(tmp_path / "mine" / "iqtree")
    _exe(tmp_path / "system" / "iqtree2")
    monkeypatch.setenv("PATH", str(tmp_path / "system") + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.delenv("MAMEY_PHYLO_BIN", raising=False)
    monkeypatch.delenv("PHYLO_BIN", raising=False)
    assert bm.resolve_bin("iqtree", str(tmp_path / "mine")) == str(mine)


def test_env_dir_beats_path_too(tmp_path, monkeypatch):
    mine = _exe(tmp_path / "envbin" / "iqtree")
    _exe(tmp_path / "system" / "iqtree3")
    monkeypatch.setenv("PATH", str(tmp_path / "system") + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.setenv("MAMEY_PHYLO_BIN", str(tmp_path / "envbin"))
    assert bm.resolve_bin("iqtree") == str(mine)


def test_path_is_still_the_fallback(tmp_path, monkeypatch):
    system = _exe(tmp_path / "system" / "iqtree2")
    monkeypatch.setenv("PATH", str(tmp_path / "system"))
    monkeypatch.delenv("MAMEY_PHYLO_BIN", raising=False)
    monkeypatch.delenv("PHYLO_BIN", raising=False)
    assert bm.resolve_bin("iqtree", str(tmp_path / "empty")) == str(system)
