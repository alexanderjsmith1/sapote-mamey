"""BC2 .400 audit: hooks/save_transcript.py's chat-folder lookup (both the `.session_id` pin
resolution and the output directory) defaulted to '<ROOT>/sessions/<color>/' when
$SAPOTE_CHAT_DIR is unset. Confirmed live: SAPOTE_CHAT_DIR is unset in the real environment, no
'sessions/' directory exists anywhere under the real workspace root, and the real per-chat
convention this whole project uses lives under a differently-named subdirectory instead.

v2 (tick 24, .398 round) fixed this by discovering the chat-dir root structurally -- the first
sorted ROOT subdirectory owning a `<color>/STATE.md` -- rather than hardcoding the private
convention's folder name. v3 (this file, .400 round) redesigns the pick logic itself per
independent (Codex) pool review: "Transcript saver returns the first sorted structural match.
Require an explicit root or exactly one match; do not silently choose." v2 returned the FIRST
match found in sorted order without checking for a second, genuinely distinct match -- the same
class of silent-ambiguity gap already redesigned this round in deliverable_markdown_reminder.py
and link_check.py. v3 now refuses (returns None, warns to stderr) when two or more distinct
candidates exist, and dedups symlink aliases to the same physical directory by (st_dev, st_ino)
first -- matching the live symlink condition (`strain_data` -> `AS Strain Master`) that already
caused a real false-ambiguity bug in link_check.py's own v3 redesign this round. Checked live:
that particular symlink does NOT create ambiguity for save_transcript's own discovery (neither
`AS Strain Master/` nor `strain_data/` owns a `<color>/STATE.md` for any real color), but the
dedup is included anyway as the same defensive precedent, since it is a shared live-workspace
condition rather than something specific to one hook.

Deliberately uses only synthetic folder/color names.
"""
from __future__ import annotations

import importlib
import pathlib
import sys

HOOKS_DIR = pathlib.Path(__file__).resolve().parents[1] / "hooks"
sys.path.insert(0, str(HOOKS_DIR))


def _reload_hook(monkeypatch, root):
    monkeypatch.delenv("SAPOTE_CHAT_DIR", raising=False)
    monkeypatch.setenv("SAPOTE_ROOT", str(root))
    sys.modules.pop("save_transcript", None)
    import save_transcript as st
    return st


def test_discovers_chat_dir_by_owning_state_md_regardless_of_its_name(tmp_path, monkeypatch):
    """The consequential case: a synthetic-named subdirectory (not 'sessions', not any real
    private folder name) owns '<color>/STATE.md' -- it must be discovered as the chat dir."""
    real_home = tmp_path / "Some Chat Home"
    real_home.mkdir()
    color_dir = real_home / "Sea Green"
    color_dir.mkdir()
    (color_dir / "STATE.md").write_text("# STATE\n")

    st = _reload_hook(monkeypatch, tmp_path)
    assert st.chat_dir(tmp_path, "Sea Green") == real_home


def test_falls_back_to_legacy_sessions_when_nothing_found(tmp_path, monkeypatch):
    """No regression: when no subdirectory owns a matching STATE.md, the legacy 'sessions'
    default is still returned (same behavior as before when the real dir doesn't exist)."""
    st = _reload_hook(monkeypatch, tmp_path)
    assert st.chat_dir(tmp_path, "Sea Green") == tmp_path / "sessions"


def test_explicit_env_var_still_wins(tmp_path, monkeypatch):
    """No regression: an explicitly-set SAPOTE_CHAT_DIR always wins over discovery, even when
    a genuine structural ambiguity also exists."""
    for name in ("Home One", "Home Two"):
        d = tmp_path / name / "Sea Green"
        d.mkdir(parents=True)
        (d / "STATE.md").write_text("# STATE\n")
    monkeypatch.setenv("SAPOTE_CHAT_DIR", "custom_chats")
    sys.modules.pop("save_transcript", None)
    import save_transcript as st
    assert st.chat_dir(tmp_path, "Sea Green") == tmp_path / "custom_chats"


def test_pin_resolution_uses_the_discovered_chat_dir(tmp_path, monkeypatch):
    real_home = tmp_path / "Some Chat Home"
    color_dir = real_home / "Sea Green"
    color_dir.mkdir(parents=True)
    (color_dir / "STATE.md").write_text("# STATE\n")
    (color_dir / ".session_id").write_text("test-session-abc")

    projects = tmp_path / "projects"
    projects.mkdir()
    (projects / "test-session-abc.jsonl").write_text('{"type": "summary", "summary": "x"}\n')

    monkeypatch.setenv("CLAUDE_PROJECTS_DIR", str(projects))
    st = _reload_hook(monkeypatch, tmp_path)
    jsonl, how = st.resolve_jsonl("Sea Green", None)
    assert how == "pinned"
    assert jsonl == projects / "test-session-abc.jsonl"


def test_two_genuinely_distinct_candidates_refuse_rather_than_pick_first_sorted(
    tmp_path, monkeypatch, capsys
):
    """The v3 regression this redesign closes: v2 silently returned the FIRST match in sorted
    order. Two real, physically distinct candidates must now refuse (None + stderr warning),
    not silently pick whichever sorts first."""
    for name in ("Alpha Home", "Zeta Home"):
        d = tmp_path / name / "Sea Green"
        d.mkdir(parents=True)
        (d / "STATE.md").write_text("# STATE\n")

    st = _reload_hook(monkeypatch, tmp_path)
    assert st.chat_dir(tmp_path, "Sea Green") is None
    err = capsys.readouterr().err
    assert "ambiguous" in err.lower()
    assert "Alpha Home" in err and "Zeta Home" in err


def test_symlink_alias_to_the_same_directory_is_not_a_second_candidate(tmp_path, monkeypatch):
    """A symlink aliasing the SAME physical directory (the live condition already caught in
    link_check.py's own v3 redesign this round: strain_data -> AS Strain Master) must be
    deduped by (st_dev, st_ino), not counted as a second, distinct candidate."""
    real_home = tmp_path / "Some Chat Home"
    color_dir = real_home / "Sea Green"
    color_dir.mkdir(parents=True)
    (color_dir / "STATE.md").write_text("# STATE\n")

    alias = tmp_path / "alias_to_home"
    alias.symlink_to(real_home)

    st = _reload_hook(monkeypatch, tmp_path)
    assert st.chat_dir(tmp_path, "Sea Green") == real_home


def test_resolve_jsonl_falls_back_to_newest_on_ambiguity_rather_than_crashing(
    tmp_path, monkeypatch
):
    """resolve_jsonl must not crash (e.g. AttributeError on None) when chat_dir refuses --
    it degrades to the existing 'newest(fallback)' path, same as when no pin exists at all."""
    for name in ("Alpha Home", "Zeta Home"):
        d = tmp_path / name / "Sea Green"
        d.mkdir(parents=True)
        (d / "STATE.md").write_text("# STATE\n")

    projects = tmp_path / "projects"
    projects.mkdir()
    only = projects / "only-session.jsonl"
    only.write_text('{"type": "summary", "summary": "x"}\n')

    monkeypatch.setenv("CLAUDE_PROJECTS_DIR", str(projects))
    st = _reload_hook(monkeypatch, tmp_path)
    jsonl, how = st.resolve_jsonl("Sea Green", None)
    assert how == "newest(fallback)"
    assert jsonl == only


def test_main_refuses_rather_than_writing_to_the_wrong_place_on_ambiguity(
    tmp_path, monkeypatch, capsys
):
    """main() writes real output files -- unlike the advisory-only hooks, it must refuse
    outright (exit 1) rather than silently writing transcripts into a fallback location when
    the chat dir is genuinely ambiguous."""
    for name in ("Alpha Home", "Zeta Home"):
        d = tmp_path / name / "Sea Green"
        d.mkdir(parents=True)
        (d / "STATE.md").write_text("# STATE\n")

    projects = tmp_path / "projects"
    projects.mkdir()
    (projects / "only-session.jsonl").write_text('{"type": "summary", "summary": "x"}\n')

    monkeypatch.setenv("CLAUDE_PROJECTS_DIR", str(projects))
    monkeypatch.setenv("SAPOTE_ROOT", str(tmp_path))
    monkeypatch.delenv("SAPOTE_CHAT_DIR", raising=False)
    sys.modules.pop("save_transcript", None)
    import save_transcript as st
    importlib.reload(st)

    monkeypatch.setattr(sys, "argv", ["save_transcript.py", "--color", "Sea Green"])
    rc = st.main()
    assert rc == 1
    err = capsys.readouterr().err
    assert "cannot determine chat dir" in err
    assert not (tmp_path / "Alpha Home" / "Sea Green" / "TRANSCRIPTS").exists()
    assert not (tmp_path / "Zeta Home" / "Sea Green" / "TRANSCRIPTS").exists()
