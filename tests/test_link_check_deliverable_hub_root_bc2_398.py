"""BC2 .398/.399 audit: hooks/link_check.py's deliverable-hub root discovery.

v9.7.398 fix: hardcoded scan root was '<workspace>/strain_data', which doesn't exist on the
real workspace -- main()'s own first check exited immediately on every real invocation. Fixed
by discovering the root structurally (whichever subdirectory owns WHERE_THINGS_LIVE.md).

v9.7.399 REDESIGN (Codex pool review): the v9.7.398 fix AGGREGATED findings across every
matching subdirectory plus an always-on legacy fallback, silently combining potentially
distinct indexes with no signal the scope was ambiguous. Redesigned to resolve to exactly ONE
authoritative root: an explicit $SAPOTE_DELIVERABLE_ROOT override, or (absent that) exactly one
structural match, refusing (None, warn) on zero-with-no-legacy or multiple structural matches
rather than aggregating or guessing. The legacy 'strain_data/' path is now a last-resort
fallback used ONLY when no structural match exists at all -- never combined with one.

Deliberately uses only synthetic folder/subdirectory names.
"""
from __future__ import annotations

import pathlib
import subprocess
import sys
from tests.conftest import hermetic_env  # v9.7.404 bytecode-leak fix

HOOKS_DIR = pathlib.Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS_DIR))


def _reload_hook(monkeypatch, workspace):
    monkeypatch.delenv("SAPOTE_DELIVERABLE_ROOT", raising=False)
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(workspace))
    sys.modules.pop("link_check", None)
    import link_check as lc
    return lc


def test_discovers_the_root_by_owning_where_things_live_regardless_of_its_name(tmp_path, monkeypatch):
    """The consequential case: a synthetic-named subdirectory (not 'strain_data', not any
    real private folder name) owns WHERE_THINGS_LIVE.md -- it must still be discovered as the
    single authoritative root."""
    hub_root = tmp_path / "Some Deliverable Home"
    hub_root.mkdir()
    (hub_root / "WHERE_THINGS_LIVE.md").write_text("# index\n- _registered_hub: link\n")
    (hub_root / "_registered_hub").mkdir()
    (hub_root / "_orphan_hub").mkdir()

    lc = _reload_hook(monkeypatch, tmp_path)
    assert lc.DELIVERABLE_HUB_ROOT == str(hub_root)


def test_no_hardcoded_workspace_specific_literal_in_source():
    src = (HOOKS_DIR / "link_check.py").read_text(encoding="utf-8")
    assert "AS Strain Master" not in src
    assert "strain_data" in src  # the legacy fallback path is expected to remain


def test_orphan_detection_works_end_to_end_against_the_discovered_root(tmp_path, monkeypatch):
    hub_root = tmp_path / "Some Deliverable Home"
    hub_root.mkdir()
    (hub_root / "WHERE_THINGS_LIVE.md").write_text("# index\n- _registered_hub: link\n")
    (hub_root / "_registered_hub").mkdir()
    (hub_root / "_orphan_hub").mkdir()

    hook_path = HOOKS_DIR / "link_check.py"
    proc = subprocess.run([sys.executable, str(hook_path)], capture_output=True, text=True,
                           env=hermetic_env(SAPOTE_WORKSPACE_ROOT=str(tmp_path), PATH="/usr/bin:/bin"))
    assert "_orphan_hub" in proc.stderr
    assert "_registered_hub" not in proc.stderr


def test_legacy_bare_strain_data_convention_still_works_when_no_structural_match(tmp_path, monkeypatch):
    """No regression: a bare 'strain_data/' root (the pre-existing, hardcoded convention)
    still works as a FALLBACK when nothing else owns the index."""
    legacy_root = tmp_path / "strain_data"
    legacy_root.mkdir()
    (legacy_root / "WHERE_THINGS_LIVE.md").write_text("# index\n")
    (legacy_root / "_orphan_hub").mkdir()

    lc = _reload_hook(monkeypatch, tmp_path)
    assert lc.DELIVERABLE_HUB_ROOT == str(legacy_root)


def test_two_structural_matches_refuse_rather_than_aggregate(tmp_path, monkeypatch, capsys):
    """The consequential redesign proof: two subdirectories each own a WHERE_THINGS_LIVE.md
    (a genuinely ambiguous workspace) -- must refuse (None), not silently combine or pick one."""
    for name in ("Deliverable Home A", "Deliverable Home B"):
        d = tmp_path / name
        d.mkdir()
        (d / "WHERE_THINGS_LIVE.md").write_text("# index\n")

    lc = _reload_hook(monkeypatch, tmp_path)
    assert lc.DELIVERABLE_HUB_ROOT is None
    assert "ambiguous" in capsys.readouterr().err.lower()


def test_symlink_alias_to_the_same_directory_is_not_a_second_candidate(tmp_path, monkeypatch):
    """The exact live scenario this design correction closes: a symlink pointing a second
    path name at the SAME physical directory (confirmed to exist live in the real workspace,
    e.g. a workaround symlink pointing the legacy path name at the real canonical folder)
    must NOT count as a second,
    ambiguous candidate -- it's one physical directory, reached two ways."""
    real = tmp_path / "Some Deliverable Home"
    real.mkdir()
    (real / "WHERE_THINGS_LIVE.md").write_text("# index\n")
    alias = tmp_path / "strain_data"
    alias.symlink_to(real)

    lc = _reload_hook(monkeypatch, tmp_path)
    assert lc.DELIVERABLE_HUB_ROOT == str(real), (
        f"a symlink alias to the same directory was treated as a second candidate: "
        f"{lc.DELIVERABLE_HUB_ROOT}"
    )


def test_explicit_env_var_wins_over_structural_discovery(tmp_path, monkeypatch):
    hub_root = tmp_path / "Some Deliverable Home"
    hub_root.mkdir()
    (hub_root / "WHERE_THINGS_LIVE.md").write_text("# index\n")
    explicit = tmp_path / "Explicit Override Home"
    explicit.mkdir()

    monkeypatch.setenv("SAPOTE_DELIVERABLE_ROOT", str(explicit))
    lc = _reload_hook(monkeypatch, tmp_path)
    # _reload_hook clears SAPOTE_DELIVERABLE_ROOT itself; set it again after
    monkeypatch.setenv("SAPOTE_DELIVERABLE_ROOT", str(explicit))
    sys.modules.pop("link_check", None)
    import link_check as lc2
    assert lc2.DELIVERABLE_HUB_ROOT == str(explicit)


def test_no_match_at_all_refuses_cleanly(tmp_path, monkeypatch):
    lc = _reload_hook(monkeypatch, tmp_path)
    assert lc.DELIVERABLE_HUB_ROOT is None
