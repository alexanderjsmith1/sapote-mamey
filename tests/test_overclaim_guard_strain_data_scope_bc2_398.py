"""BC2 .400 audit: hooks/overclaim_guard.py's REPORT-scope check hardcoded this specific
deployment's private folder name ('as strain master') as a raw substring test, alongside a
second raw substring test for 'strain_data' -- neither generalizes to a differently-named or
differently-laid-out workspace, and substring containment can match inside an unrelated,
longer path segment rather than a genuine directory component.

v9.7.400 REDESIGN (Codex pool review): "still contains workspace-specific 'as strain master'
matching and substring scope inference. Replace it with generic configured report roots or
exact path components." Replaced with in_report_scope(): the engine's own documented, portable
'strain_data' directory-name convention, checked as an exact path component; OR the
structurally-discovered deliverable-hub root -- the SAME resolver link_check.py's own v3
redesign this round uses (deliverable_hub_root(), imported defensively), so one
$SAPOTE_DELIVERABLE_ROOT setting configures both hooks -- also checked as an exact path
component, never raw substring. This is the 4th and last of the Codex-flagged "silent guess /
hardcoded scope" hooks this round, after deliverable_markdown_reminder.py, link_check.py, and
save_transcript.py.

Reproduces behavior directly via subprocess against the real hook script (no test-only
reimplementation of its logic), matching the project's own hook-testing convention in
tests/test_hooks_workspace_portability.py.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parents[1] / "hooks"
HOOK = HOOKS_DIR / "overclaim_guard.py"

EGREGIOUS_CONTENT = "This BGC produces Novobiocin in the fermenter."
QUALIFIED_CONTENT = "This BGC is a class-level candidate resembling the novobiocin family."


def _run_hook(file_path, content, env_extra=None, hook_path=None):
    payload = json.dumps({
        "tool_name": "Write",
        "tool_input": {"file_path": file_path, "content": content},
    })
    env = dict(os.environ)
    # Isolate from whatever the real invoking shell/session has set, and from the real live
    # workspace's own structural discovery (a real deliverable-hub root with a
    # WHERE_THINGS_LIVE.md exists on this machine outside the test sandbox) -- tests must not
    # depend on it.
    for k in ("SAPOTE_DELIVERABLE_ROOT", "SAPOTE_WORKSPACE_ROOT", "CLAUDE_PROJECT_DIR"):
        env.pop(k, None)
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, str(hook_path or HOOK)],
        input=payload, capture_output=True, text=True, env=env,
    )
    return proc.stdout.strip(), proc.returncode


def test_hook_present():
    assert HOOK.is_file(), "hooks/overclaim_guard.py not found"


def test_blocks_under_the_strain_data_path_component():
    """No regression: the engine's own documented 'strain_data/' convention still blocks,
    unchanged from before -- now checked as a real path component."""
    out, rc = _run_hook("strain_data/AS-001/report.md", EGREGIOUS_CONTENT)
    assert rc == 0  # hook itself always exits 0; blocking is signalled via the JSON payload
    assert out, "expected a permissionDecision:deny payload for a strain_data/ report path"
    decision = json.loads(out)
    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_custom_env_deliverable_root_widens_scope_not_hardcoded(tmp_path):
    """The actual fix: no deployment-specific name is hardcoded in source any more. An
    explicitly-configured $SAPOTE_DELIVERABLE_ROOT with an arbitrary, synthetic name (NOT the
    real deployment's folder name) is honored as an in-scope path component."""
    root = tmp_path / "Some Synthetic Report Home"
    root.mkdir()
    out, rc = _run_hook(
        "Some Synthetic Report Home/AS-001/report.md",
        EGREGIOUS_CONTENT,
        env_extra={"SAPOTE_DELIVERABLE_ROOT": str(root)},
    )
    assert rc == 0
    assert out, "expected the configured deliverable root to be honored as in-scope"
    decision = json.loads(out)
    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_substring_collision_no_longer_falsely_in_scope():
    """The v3 regression this redesign closes: a path segment that merely CONTAINS
    'strain_data' as a substring (not the real directory component) must NOT be treated as
    in-scope any more -- exact path components, not substring containment. (This direction is
    a correctness narrowing of a previously over-broad false-positive match, not a coverage
    loss for any genuine strain_data/ report path.)"""
    out, rc = _run_hook("not_a_strain_data_directory_at_all/report.md", EGREGIOUS_CONTENT)
    assert rc == 0
    assert out == ""


def test_out_of_scope_path_still_passes():
    """No over-widening: a report with no matching scope token anywhere in its path is still
    out of scope and must pass through untouched (empty stdout)."""
    out, rc = _run_hook("some_other_folder/notes.md", EGREGIOUS_CONTENT)
    assert rc == 0
    assert out == ""


def test_qualified_language_still_passes_in_scope():
    """No over-blocking: a properly qualified claim in an in-scope file still passes."""
    out, rc = _run_hook("strain_data/AS-001/report.md", QUALIFIED_CONTENT)
    assert rc == 0
    assert out == ""


def test_env_override_works_even_if_link_check_sibling_predates_the_shared_helper(tmp_path):
    """Independent-applicability check, caught by direct verification while staging this card:
    this hook's own patch and link_check.py's own v3 redesign are two separate,
    independently-appliable cards in the same pool. If ONLY this card is applied, the sibling
    link_check.py on disk is still the OLDER version that has no deliverable_hub_root() to
    import at all -- $SAPOTE_DELIVERABLE_ROOT must still work via this hook's own direct env
    check, not solely through the (in that scenario, unavailable) imported helper."""
    isolated_hooks = tmp_path / "hooks"
    isolated_hooks.mkdir()
    isolated_hook = isolated_hooks / "overclaim_guard.py"
    shutil.copy(HOOK, isolated_hook)
    # an old-style link_check.py sibling WITHOUT deliverable_hub_root() -- the import fails,
    # but the env-var path must not depend on it succeeding.
    (isolated_hooks / "link_check.py").write_text("# old link_check.py, no shared helper\n")

    root = tmp_path / "Some Synthetic Report Home"
    root.mkdir()
    out, rc = _run_hook(
        "Some Synthetic Report Home/AS-001/report.md",
        EGREGIOUS_CONTENT,
        env_extra={"SAPOTE_DELIVERABLE_ROOT": str(root)},
        hook_path=isolated_hook,
    )
    assert rc == 0
    assert out, "expected the env override to work even with an old-style link_check.py sibling"
    decision = json.loads(out)
    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_degrades_gracefully_when_link_check_sibling_is_missing(tmp_path):
    """Fail-OPEN discipline, unchanged: this hook's own contract is 'any parse error /
    unexpected shape exits 0'. If the sibling link_check.py it now imports
    deliverable_hub_root() from is absent entirely (a partial or differently-laid-out
    deployment), the hook must not crash -- it degrades to the unchanged bare 'strain_data'
    path-component check, which must still correctly block."""
    isolated_hooks = tmp_path / "hooks"
    isolated_hooks.mkdir()
    isolated_hook = isolated_hooks / "overclaim_guard.py"
    shutil.copy(HOOK, isolated_hook)
    # deliberately do NOT copy link_check.py into this isolated dir
    assert not (isolated_hooks / "link_check.py").exists()
    out, rc = _run_hook(
        "strain_data/AS-001/report.md", EGREGIOUS_CONTENT, hook_path=isolated_hook,
    )
    assert rc == 0
    assert out, "expected strain_data/ scope to still block even with link_check.py absent"
    decision = json.loads(out)
    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"
