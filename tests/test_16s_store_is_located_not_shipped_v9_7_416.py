"""The 16S store is a 267 MiB local asset the bundle does NOT carry — so it must be LOCATED.

`16S Database/rrna16s.sqlite` measured 279,638,016 bytes on 2026-09-08 (58,537 records resolving
to 56,117 strain identities). It cannot ship, and `OFFICIAL_DATA/ASSET_REGISTRY.tsv` already
carries it as asset `rrna16s_db` — the registry `tools/find_asset.py` reads. So the bundled tools
resolve it through that registry rather than through a path written into the source.

THE DEFECT THIS CLOSES IS NOT ONLY PORTABILITY. Every one of these tools opened the store with a
bare `sqlite3.connect(DB)`, and **`sqlite3.connect()` on a missing path CREATES an empty
database**. On any machine without the asset the sequence was: connect succeeds, the schema is
absent or empty, every query returns zero rows, and the tool prints its census —
`0 records tagged`, `no queries matched`, `0 flagged pairs resolved` — as a measurement. A missing
267 MiB asset rendered as a finding, with exit 0.

Resolution order asserted here (most specific first):
  1. `--db`                      2. `$SAPOTE_16S_SQLITE`
  3. `ASSET_REGISTRY.tsv` row `rrna16s_db`    4. `<root>/16S Database/rrna16s.sqlite`
and a refusal, naming both `find_asset.py rrna16s_db` and the builder, when none of them exists.

Hermetic: builds its own registry and its own empty store under tmp_path. No network. The real
store is never opened — the first assertion in each test that would otherwise reach it checks that
the resolved path is inside tmp_path, and fails first if it is not.
"""
from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"

STORE_READERS = ["phylo_16s_rank.py", "phylo_16s_audit_merges.py", "phylo_16s_panel.py",
                 "phylo_16s_fetch.py", "phylo_16s_esearch.py", "phylo_16s_build_db.py"]


def _load(name: str):
    path = TOOLS / name
    if not path.is_file():
        pytest.fail(f"{name} is not in tools/ — the 16S workflow was not landed in the bundle")
    spec = importlib.util.spec_from_file_location(f"_v415store_{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _registry(root: Path, rel_dir: str) -> None:
    """A minimal ASSET_REGISTRY.tsv carrying only the row under test."""
    d = root / "OFFICIAL_DATA"
    d.mkdir(parents=True, exist_ok=True)
    (d / "ASSET_REGISTRY.tsv").write_text(
        "#\tASSET_REGISTRY.tsv — canonical map of BIG / SHARED local assets.\n"
        "asset_id\tkind\tpath\tsize\tguards\tnote\n"
        f"rrna16s_db\tdatabase\t{rel_dir}\t267M\t16S|rrna16s\t16S sequence + metadata database.\n",
        encoding="utf-8")


@pytest.mark.parametrize("name", STORE_READERS)
def test_the_store_path_follows_the_environment(monkeypatch, tmp_path, name):
    """Every reader in the family, not just one — the literal was in all of them."""
    pinned = tmp_path / "pinned" / "rrna16s.sqlite"
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("SAPOTE_16S_SQLITE", str(pinned))
    mod = _load(name)
    assert mod.DB == str(pinned), (
        f"{name} resolved its store to {mod.DB!r} while $SAPOTE_16S_SQLITE named {pinned}")


def test_the_asset_registry_row_is_what_locates_an_unshipped_store(monkeypatch, tmp_path):
    """With no env pin, the registry — the same channel `tools/find_asset.py` reads — must win."""
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.delenv("SAPOTE_16S_SQLITE", raising=False)
    store_dir = tmp_path / "elsewhere" / "16S Database"
    store_dir.mkdir(parents=True)
    sqlite3.connect(store_dir / "rrna16s.sqlite").close()
    _registry(tmp_path, "elsewhere/16S Database")
    mod = _load("phylo_16s_rank.py")
    assert mod.DB == str(store_dir / "rrna16s.sqlite"), (
        f"the ASSET_REGISTRY `rrna16s_db` row was not consulted; got {mod.DB!r}. That row is the "
        f"project's own statement of where its big local data lives, and it is why a 267 MiB "
        f"asset does not have to ship for the tools that use it to.")


def test_a_missing_store_is_refused_and_never_created(monkeypatch, tmp_path):
    """sqlite3.connect() would MAKE this file, and every query would then return zero rows."""
    missing = tmp_path / "nowhere" / "rrna16s.sqlite"
    missing.parent.mkdir(parents=True)
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("SAPOTE_16S_SQLITE", str(missing))
    mod = _load("phylo_16s_audit_merges.py")
    assert str(tmp_path) in mod.DB, (
        f"{mod.DB!r} is still a workspace literal; refusing to call main() from a test, because "
        f"on the machine that literal names it would open the real 267 MiB store and run MAFFT "
        f"over every flagged pair in it.")
    with pytest.raises(SystemExit) as e:
        mod.main()
    assert not missing.exists(), (
        "an empty database was created. Its census — `0 flagged pairs resolved by alignment` — "
        "would be printed as a measurement.")
    msg = str(e.value)
    assert "find_asset.py" in msg and "rrna16s_db" in msg, (
        f"the refusal must name the registry channel so the operator can locate the asset "
        f"instead of re-deriving it; got: {msg[:240]}")
    assert "phylo_16s_build_db" in msg, "the refusal must also name the tool that BUILDS the store"


def test_the_builder_may_open_a_store_that_does_not_exist_yet(monkeypatch, tmp_path):
    """REGRESSION GUARD (passes on both trees): `phylo_16s_build_db` is the tool that CREATES the
    file, so it alone resolves with must_exist=False and must not refuse."""
    target = tmp_path / "fresh" / "rrna16s.sqlite"
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("SAPOTE_16S_SQLITE", str(target))
    mod = _load("phylo_16s_build_db.py")
    assert mod.DB == str(target)
    assert not target.exists(), "importing the builder must not create the store"


def test_the_registry_row_for_the_store_exists_in_this_workspace():
    """Advisory: if the operator's registry has drifted, say so rather than failing the suite —
    the registry is workspace data, not bundle code, and CI has none."""
    import os
    root = os.environ.get("SAPOTE_WORKSPACE_ROOT") or os.environ.get("SAPOTE_ROOT")
    if not root:
        pytest.skip("no workspace root bound; the registry is operator data, not bundle code")
    reg = Path(root) / "OFFICIAL_DATA" / "ASSET_REGISTRY.tsv"
    if not reg.is_file():
        pytest.skip(f"no ASSET_REGISTRY.tsv at {reg}")
    assert any(ln.startswith("rrna16s_db\t") for ln in reg.read_text().splitlines()), (
        "OFFICIAL_DATA/ASSET_REGISTRY.tsv has no `rrna16s_db` row, so `find_asset.py rrna16s_db` "
        "cannot locate the store the bundled tools depend on.")
