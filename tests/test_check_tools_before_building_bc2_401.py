"""BC2 .401 audit: hooks/check_tools_before_building.py — advisory PreToolUse hook, Alex-assigned
(ROSTER_401_SEEDS.md item 2, from VGP's 2026-09-02 self-audit, "audit control #1, the
highest-value change"): before a Write creates a brand-new `.py` file outside this bundle's own
`tools/`/`mamey/`, surface any shipped tool sharing a name concept, so a script isn't
independently re-derived when the engine already ships one.

Grounded in a real, confirmed incident: VGP independently re-derived `rggmci.py`,
`rggmci_cohort_rollup.py`, `build_reconstruction.py`, and `cohort_leads_ledger.py` -- verified
here directly that all four ship in the sealed bundle this hook would have warned against.

Reproduces behavior directly via subprocess against the real hook script (no logic
reimplementation), matching the project's own hook-testing convention
(`tests/test_hooks_workspace_portability.py`).
"""
from __future__ import annotations

import json
import subprocess
import sys
import pathlib

HOOKS_DIR = pathlib.Path(__file__).resolve().parents[1] / "hooks"
HOOK = HOOKS_DIR / "check_tools_before_building.py"
BUNDLE_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _run(tool_name: str, file_path: str, **extra_input) -> tuple[dict | None, int]:
    payload = json.dumps({
        "tool_name": tool_name,
        "tool_input": {"file_path": file_path, **extra_input},
    })
    proc = subprocess.run([sys.executable, str(HOOK)], input=payload,
                           capture_output=True, text=True)
    out = proc.stdout.strip()
    return (json.loads(out) if out else None), proc.returncode


def test_hook_present():
    assert HOOK.is_file(), "hooks/check_tools_before_building.py not found"


# -- the real E1 incident this hook exists to catch -------------------------------------------

def test_e1_examples_actually_ship_in_the_bundle():
    """Grounding check: the four files VGP independently re-derived must genuinely exist in
    this bundle, or the whole premise of this hook is unfounded."""
    assert (BUNDLE_ROOT / "mamey" / "rggmci.py").is_file()
    assert (BUNDLE_ROOT / "tools" / "rggmci_cohort_rollup.py").is_file()
    assert (BUNDLE_ROOT / "tools" / "build_reconstruction.py").is_file()
    assert (BUNDLE_ROOT / "mamey" / "cohort_leads_ledger.py").is_file()


def test_rederiving_cohort_leads_ledger_fires_the_advisory(tmp_path):
    out, rc = _run("Write", str(tmp_path / "cohort_leads_ledger.py"), content="# new")
    assert rc == 0
    assert out is not None, "expected an advisory for a real E1-shaped duplicate"
    hso = out["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "allow", "must never deny -- advisory only"
    assert "cohort_leads_ledger" in hso["permissionDecisionReason"]


def test_the_exact_match_is_not_buried_by_truncation(tmp_path):
    """The actual regression this hook's own build caught live against the real bundle: a
    plain alphabetical sort put the real near-duplicate ('cohort_leads_ledger') past the
    preview's truncation point, behind generic same-prefix noise. The exact/closest match
    must always be the first name shown."""
    out, rc = _run("Write", str(tmp_path / "cohort_leads_ledger.py"), content="# new")
    reason = out["hookSpecificOutput"]["permissionDecisionReason"]
    after_colon = reason.split(": ", 2)[-1]
    first_listed = after_colon.split(",")[0].strip()
    assert first_listed == "cohort_leads_ledger", (
        f"expected the exact-stem match first in the preview, got {first_listed!r}"
    )


def test_rederiving_rggmci_cohort_rollup_fires(tmp_path):
    out, rc = _run("Write", str(tmp_path / "rggmci_cohort_rollup.py"), content="# new")
    assert out is not None
    assert "rggmci" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_rederiving_build_reconstruction_fires(tmp_path):
    out, rc = _run("Write", str(tmp_path / "build_reconstruction.py"), content="# new")
    assert out is not None


def test_rederiving_rggmci_fires(tmp_path):
    out, rc = _run("Write", str(tmp_path / "rggmci.py"), content="# new")
    assert out is not None


# -- negative controls: must stay silent -----------------------------------------------------

def test_genuinely_novel_unrelated_filename_stays_silent(tmp_path):
    out, rc = _run("Write", str(tmp_path / "xkq_zephyr_glimmer.py"), content="# new")
    assert rc == 0
    assert out is None, "no concept overlap -- must be silent, not a false positive"


def test_editing_an_already_existing_file_stays_silent(tmp_path):
    """Not a NEW file -- an edit/overwrite of something already there. The hook's whole point
    is catching re-derivation before it starts, not nagging on every subsequent edit."""
    existing = tmp_path / "existing_cohort_thing.py"
    existing.write_text("x")
    out, rc = _run("Write", str(existing), content="y")
    assert out is None


def test_non_python_file_stays_silent(tmp_path):
    out, rc = _run("Write", str(tmp_path / "cohort_leads_ledger.md"), content="x")
    assert out is None


def test_edit_tool_stays_silent_even_on_a_matching_name(tmp_path):
    """Edit/MultiEdit require an existing file by construction -- they can never create the
    brand-new file this hook cares about, so they're out of scope entirely."""
    payload = json.dumps({
        "tool_name": "Edit",
        "tool_input": {"file_path": str(tmp_path / "cohort_leads_ledger.py"),
                       "old_string": "a", "new_string": "b"},
    })
    proc = subprocess.run([sys.executable, str(HOOK)], input=payload,
                           capture_output=True, text=True)
    assert proc.stdout.strip() == ""


def test_writing_inside_tools_dir_itself_stays_silent(tmp_path, monkeypatch):
    """A new module added directly inside tools/ or mamey/ is already covered by
    tools/check_module_accretion.py (mamey/) and ordinary review -- this hook's gap is
    standalone scripts built OUTSIDE those directories."""
    out, rc = _run("Write", str(BUNDLE_ROOT / "tools" / "cohort_leads_ledger_test_probe.py"),
                   content="x")
    assert out is None


def test_malformed_json_input_fails_open():
    proc = subprocess.run([sys.executable, str(HOOK)], input="not json{{{",
                           capture_output=True, text=True)
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


def test_missing_tool_input_fails_open():
    proc = subprocess.run([sys.executable, str(HOOK)], input='{"tool_name": "Write"}',
                           capture_output=True, text=True)
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


def test_wrong_tool_name_stays_silent(tmp_path):
    out, rc = _run("Bash", str(tmp_path / "cohort_leads_ledger.py"), command="ls")
    assert out is None
