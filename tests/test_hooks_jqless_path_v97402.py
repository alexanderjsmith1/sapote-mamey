"""jq-family port regression (.402, ROSTER_402 seed #1 — Black Cherry-4).

Verified field defect (sealed v9.7.401, 2026-09-02): nine shipped hooks parsed their hook
payload with ``jq``, which is absent in clean/container shells and undocumented in
PREREQUISITES.md. Failure shapes, reproduced under a jq-less PATH:

* six hooks failed OPEN — silently disarmed, including three BLOCKING guards
  (block_heavy_compute, check_local_assets_before_download, full_suite_before_package);
* three fail-closed guards (block_seal_commands, block_sealed_tree_edits,
  block_top_level_release_folder) denied EVERY tool call with a misleading
  "GUARDRAIL INTERNAL ERROR (jq missing?)" — bricking the session instead of guarding it.

The .401 seal repaired exactly one hook (bgc_node_name_guard → python3 stdlib). This card
ports the remaining nine the same way. These tests run each REAL hook via subprocess under a
restricted PATH that genuinely lacks jq (symlink farm of only the commands the hooks need),
and assert the hook still performs its actual function.

Engineering guardrail tests only; no scientific claim.
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest
from tests.conftest import hermetic_env  # v9.7.404 bytecode-leak fix

BUNDLE = Path(__file__).resolve().parents[1]
HOOKS = BUNDLE / "hooks"

# Commands the nine hooks legitimately need (printf/cd/command are shell builtins).
NEEDED = [
    "bash", "sh", "cat", "grep", "sed", "find", "ls", "sort", "tail", "head",
    "tr", "basename", "dirname", "wc", "env", "touch",
]


@pytest.fixture()
def jqless_path(tmp_path):
    """A PATH with everything the hooks need — and no jq."""
    bin_dir = tmp_path / "jqless_bin"
    bin_dir.mkdir()
    for name in NEEDED:
        src = shutil.which(name)
        if src:
            (bin_dir / name).symlink_to(src)
    (bin_dir / "python3").symlink_to(sys.executable)
    path = str(bin_dir)
    assert shutil.which("jq", path=path) is None, "jq leaked into the restricted PATH"
    return path


def _run(hook: str, payload: dict, path: str, cwd=None, extra_env=None):
    env = hermetic_env(PATH=path, HOME=os.environ.get("HOME", "/tmp"))
    if extra_env:
        env.update(extra_env)
    bash = shutil.which("bash")
    proc = subprocess.run(
        [bash, str(HOOKS / hook)], input=json.dumps(payload), capture_output=True,
        text=True, env=env, cwd=str(cwd) if cwd else str(BUNDLE), timeout=60,
    )
    return proc


def _deny_reason(proc) -> str:
    """Parse the hook's stdout as a deny decision; fail loudly on malformed output."""
    assert proc.stdout.strip(), "expected a deny decision on stdout, got nothing"
    decision = json.loads(proc.stdout)
    out = decision["hookSpecificOutput"]
    assert out["permissionDecision"] == "deny"
    return out["permissionDecisionReason"]


# --- static: no hook may invoke jq at all -------------------------------------------------

def test_no_shipped_hook_invokes_jq():
    offenders = []
    for p in sorted(HOOKS.glob("*.sh")):
        text = p.read_text(errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            code = line.split("#", 1)[0]  # comments may mention jq historically
            if "$(jq" in code or "| jq" in code or "jq -" in code:
                offenders.append(f"{p.name}:{i}: {line.strip()[:80]}")
    assert not offenders, "hook(s) still invoke jq:\n" + "\n".join(offenders)


# --- the three formerly fail-open BLOCKING guards must still block without jq -------------

def test_block_heavy_compute_still_denies_detach_without_jq(jqless_path):
    proc = _run("block_heavy_compute.sh",
                {"tool_input": {"command": "nohup python3 heavy_scan.py"}}, jqless_path)
    reason = _deny_reason(proc)
    assert "detach" in reason or "background" in reason


def test_check_local_assets_still_denies_redownload_without_jq(jqless_path, tmp_path):
    root = tmp_path / "ws"
    (root / "Tools").mkdir(parents=True)
    finder = root / "Tools" / "find_asset.py"
    finder.write_text(
        "import sys\nsys.stderr.write('Pfam-A.hmm already at BigSCAPE/')\nsys.exit(3)\n"
    )
    proc = _run("check_local_assets_before_download.sh",
                {"tool_input": {"command": "wget https://x.example/Pfam-A.hmm.gz"}},
                jqless_path, extra_env={"CLAUDE_PROJECT_DIR": str(root)})
    reason = _deny_reason(proc)
    assert "ALREADY LOCAL" in reason


def test_full_suite_gate_still_denies_unmarked_candidate_without_jq(jqless_path, tmp_path):
    root = tmp_path / "ws"
    cand = root / "Patches for next cut Sapote Mamey (v9.9.9)" / "candidate_cut_jqtest"
    cand.mkdir(parents=True)
    proc = _run("full_suite_before_package.sh",
                {"tool_input": {"command": "zip -r out.zip candidate_cut_jqtest"}},
                jqless_path, extra_env={"SAPOTE_WORKSPACE_ROOT": str(root)})
    reason = _deny_reason(proc)
    assert "FULL-suite" in reason


# --- the three fail-closed guards: still deny the right thing, and ONLY the right thing ---

def test_block_seal_commands_denies_seal_run_without_jq(jqless_path):
    proc = _run("block_seal_commands.sh",
                {"tool_input": {"command": "bash release_cut.sh"}}, jqless_path)
    reason = _deny_reason(proc)
    assert "seal" in reason.lower()
    assert "INTERNAL ERROR" not in reason


def test_block_sealed_tree_edits_denies_sealed_write_without_jq(jqless_path):
    proc = _run("block_sealed_tree_edits.sh",
                {"tool_input": {"file_path":
                 "/x/sapote-mamey-v9.7.401-CODE-20260902v97401a/mamey/cli.py"}}, jqless_path)
    reason = _deny_reason(proc)
    assert "SEALED cut tree" in reason
    assert "INTERNAL ERROR" not in reason


def test_block_top_level_release_folder_denies_mimic_without_jq(jqless_path, tmp_path):
    proc = _run("block_top_level_release_folder.sh",
                {"tool_input": {"command": 'mkdir "Sapote Mamey v9.9.9"'}},
                jqless_path, cwd=tmp_path)
    reason = _deny_reason(proc)
    assert "top-level" in reason
    assert "INTERNAL ERROR" not in reason


@pytest.mark.parametrize("hook,payload", [
    ("block_seal_commands.sh", {"tool_input": {"command": "ls -la"}}),
    ("block_sealed_tree_edits.sh", {"tool_input": {"file_path": "/tmp/notes.txt"}}),
    ("block_top_level_release_folder.sh", {"tool_input": {"command": "ls -la"}}),
])
def test_fail_closed_guards_do_not_brick_benign_calls_without_jq(jqless_path, hook, payload):
    """Pre-port, jq-absence made these deny EVERYTHING with a misleading internal error."""
    proc = _run(hook, payload, jqless_path)
    assert proc.returncode == 0
    assert proc.stdout.strip() == "", (
        f"{hook} denied a benign call under a jq-less PATH: {proc.stdout[:200]}"
    )


# --- the three advisory hooks must still warn without jq ----------------------------------

def test_bundle_staging_reminder_still_reminds_without_jq(jqless_path, tmp_path):
    root = tmp_path / "ws"
    (root / ".claude" / "hooks").mkdir(parents=True)
    fp = root / ".claude" / "hooks" / "my_new_guard.sh"
    fp.write_text("#!/bin/bash\n")
    proc = _run("bundle_staging_reminder.sh", {"tool_input": {"file_path": str(fp)}},
                jqless_path, extra_env={"CLAUDE_PROJECT_DIR": str(root)})
    assert "REMINDER" in proc.stdout


def test_md_link_check_still_warns_without_jq(jqless_path, tmp_path):
    root = tmp_path / "ws"
    (root / "Tools").mkdir(parents=True)
    (root / "Tools" / "check_md_links.py").write_text(
        "print('broken: [x](missing%20file.md)')\n"
    )
    md = root / "note.md"
    md.write_text("[x](missing%20file.md)\n")
    proc = _run("md_link_check.sh", {"tool_input": {"file_path": str(md)}},
                jqless_path, extra_env={"SAPOTE_WORKSPACE_ROOT": str(root)})
    assert proc.returncode == 2
    assert "MD-LINK" in proc.stderr


def test_patch_hygiene_warn_still_warns_without_jq(jqless_path, tmp_path):
    queue = tmp_path / "Patches for next cut Sapote Mamey (v9.9.9)"
    card = queue / "CARD_JQTEST"
    card.mkdir(parents=True)
    (card / "PATCH_CARD.md").write_text("# card\n")
    (queue / ".DS_Store").write_bytes(b"\x00")
    proc = _run("patch_hygiene_warn.sh",
                {"tool_input": {"file_path": str(card / "PATCH_CARD.md")}}, jqless_path)
    assert "PATCH-PACKET HYGIENE WARNING" in proc.stdout


# --- and with jq PRESENT on a normal PATH, behavior is unchanged (spot check) -------------

def test_normal_path_spot_check_deny_and_benign():
    path = os.environ.get("PATH", "")
    proc = _run("block_seal_commands.sh",
                {"tool_input": {"command": "bash release_cut.sh"}}, path)
    assert "seal" in _deny_reason(proc).lower()
    proc = _run("block_heavy_compute.sh",
                {"tool_input": {"command": "ls -la"}}, path)
    assert proc.stdout.strip() == "" and proc.returncode == 0
