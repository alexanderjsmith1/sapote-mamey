"""BC2 .398/.399 audit: hooks/deliverable_markdown_reminder.py::newest_patch_folder().

v9.7.398 fix: only matched the two LEGACY patch-folder naming conventions, missing the
current one entirely, resolving to a ~14-patch-version-stale folder on the real workspace.

v9.7.399 REDESIGN (Codex pool review): the v9.7.398 fix picked the candidate with the newest
FILESYSTEM MTIME -- not authority, since an unrelated filesystem operation (backup, sync,
touch, editor save) can make an older folder look newest with no signal anything went wrong.
Redesigned to use two real sources of authority instead: an explicit $SAPOTE_PATCH_FOLDER
override, or (absent that) the single highest VERSION NUMBER embedded in each candidate
folder's own name -- a folder's structural identity, not a filesystem accident. Refuses
(returns None, warns) rather than guessing when two candidates tie at the same highest
version or when no candidate has a parseable version at all.

Uses only synthetic folder names (no real version numbers or workspace-specific literals).
"""
from __future__ import annotations

import os
import pathlib
import sys
import time

HOOKS_DIR = pathlib.Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS_DIR))


def _reload_hook(monkeypatch, base):
    """The hook module computes BASE at import time from an env var; reload after setting it."""
    monkeypatch.delenv("SAPOTE_PATCH_FOLDER", raising=False)
    monkeypatch.setenv("SAPOTE_WORKSPACE_ROOT", str(base))
    sys.modules.pop("deliverable_markdown_reminder", None)
    import deliverable_markdown_reminder as dmr
    return dmr


def test_recognizes_the_current_naming_convention(tmp_path, monkeypatch):
    current = tmp_path / "Patches for Sapote Mamey Synthetic (v0.0.1)"
    current.mkdir()
    dmr = _reload_hook(monkeypatch, tmp_path)
    assert dmr.newest_patch_folder() == str(current)


def test_still_recognizes_the_legacy_next_cut_convention(tmp_path, monkeypatch):
    """No regression: the old 'Patches for next cut Sapote Mamey*' shape still resolves."""
    legacy = tmp_path / "Patches for next cut Sapote Mamey Synthetic (v0.0.1)"
    legacy.mkdir()
    dmr = _reload_hook(monkeypatch, tmp_path)
    assert dmr.newest_patch_folder() == str(legacy)


def test_still_recognizes_the_legacy_cuts_for_convention(tmp_path, monkeypatch):
    """No regression: the old 'Cuts for Next Patch of Sapote Mamey*' shape still resolves."""
    legacy = tmp_path / "Cuts for Next Patch of Sapote Mamey Synthetic v0.0.1"
    legacy.mkdir()
    dmr = _reload_hook(monkeypatch, tmp_path)
    assert dmr.newest_patch_folder() == str(legacy)


def test_picks_the_highest_version_across_all_conventions(tmp_path, monkeypatch):
    """The consequential case: an old-convention folder and a current-convention folder both
    exist (the real, ongoing situation in this workspace) -- the one with the HIGHER embedded
    version number wins, regardless of which naming convention it uses."""
    old = tmp_path / "Patches for next cut Sapote Mamey Synthetic (v0.0.1)"
    old.mkdir()
    current = tmp_path / "Patches for Sapote Mamey Synthetic (v0.0.9)"
    current.mkdir()

    dmr = _reload_hook(monkeypatch, tmp_path)
    assert dmr.newest_patch_folder() == str(current)


def test_mtime_is_correctly_ignored_now(tmp_path, monkeypatch):
    """The regression this redesign specifically closes: a LOWER-versioned folder given a
    NEWER mtime (a stray touch, a backup restore) must NOT win -- version, not mtime, is
    authority."""
    higher_version_older_mtime = tmp_path / "Patches for Sapote Mamey Synthetic (v0.0.9)"
    higher_version_older_mtime.mkdir()
    os.utime(higher_version_older_mtime, (time.time() - 3600, time.time() - 3600))

    lower_version_newer_mtime = tmp_path / "Patches for Sapote Mamey Synthetic (v0.0.1)"
    lower_version_newer_mtime.mkdir()  # freshly created -> newest mtime, but lower version

    dmr = _reload_hook(monkeypatch, tmp_path)
    assert dmr.newest_patch_folder() == str(higher_version_older_mtime), (
        "a lower-versioned folder with a newer mtime must not win over a higher-versioned one"
    )


def test_explicit_env_var_wins_over_discovery(tmp_path, monkeypatch):
    (tmp_path / "Patches for Sapote Mamey Synthetic (v0.0.9)").mkdir()
    explicit = tmp_path / "Some Explicit Override Folder"
    explicit.mkdir()

    dmr = _reload_hook(monkeypatch, tmp_path)
    monkeypatch.setenv("SAPOTE_PATCH_FOLDER", str(explicit))
    assert dmr.newest_patch_folder() == str(explicit)


def test_ambiguous_tie_refuses_rather_than_guessing(tmp_path, monkeypatch, capsys):
    """Two candidates at the same highest version (e.g. a Claude-owned and a Codex-owned pool
    at the same cut) -- must refuse (None), not silently pick one."""
    a = tmp_path / "Patches for Sapote Mamey Claude (v0.0.9)"
    a.mkdir()
    b = tmp_path / "Patches for Sapote Mamey Codex (v0.0.9)"
    b.mkdir()

    dmr = _reload_hook(monkeypatch, tmp_path)
    result = dmr.newest_patch_folder()
    assert result is None, f"expected a refusal on a version tie, got: {result}"
    assert "ambiguous" in capsys.readouterr().err.lower()


def test_no_parseable_version_refuses_rather_than_guessing(tmp_path, monkeypatch):
    """A candidate with no parseable version number at all can't be structurally ordered --
    must refuse, not fall back to mtime."""
    unversioned = tmp_path / "Patches for Sapote Mamey with no version at all"
    unversioned.mkdir()

    dmr = _reload_hook(monkeypatch, tmp_path)
    assert dmr.newest_patch_folder() is None
