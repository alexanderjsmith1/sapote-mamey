"""CLAUDE_409_onboarding_funnel_guard — the one-door invariant, guarded.

`development/LLM_ONBOARDING_AUDIT.md` names the core defect: an operating LLM meets many
"read me first / start here" doors at the bundle root and, with no first-glance arbiter,
opens none and runs from priors. The CLAUDE_409_onboarding_one_door lane funnels every door
to one instruction — run ``python mamey_run.py start`` — and makes `AGENTS.md` the canonical
contract. Nothing else asserts that the funnel still holds, so it can silently regress the
moment a new door is added or an old one is edited. This module is that deterministic,
offline guard. It encodes the same invariant the one-door lane establishes, so the two
co-exist: these tests FAIL on the pristine 11-door tree (most doors lack the directive) and
PASS once the funnel is in place.

The check logic lives in `tools/check_onboarding_funnel.py` (one source of truth, also
runnable as a CLI); this module drives it against the bundle it ships in.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load_guard():
    path = ROOT / "tools" / "check_onboarding_funnel.py"
    spec = importlib.util.spec_from_file_location("check_onboarding_funnel", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GUARD = _load_guard()


def test_directive_string_is_canonical():
    # The whole funnel points at this exact idiom (the runner that pins the local package).
    assert GUARD.DIRECTIVE == "python mamey_run.py start"


def test_every_root_door_funnels_to_start():
    """Invariant (1): each agent-facing root door carries the directive or an AGENTS.md
    redirect near its top. Fails-before on the pristine multi-door tree; passes-after on the
    one-door layout."""
    failures, checked, _exempt = GUARD.check_doors(ROOT)
    assert checked, "no root doors were discovered — the glob set is wrong"
    assert not failures, (
        "the one-door onboarding funnel has regressed:\n  " + "\n  ".join(failures)
    )


def test_agents_and_claude_are_byte_identical():
    """Invariant (2): one door, two names."""
    assert not GUARD.check_twin(ROOT)


def test_subsystem_door_is_intentionally_exempt():
    # Document the one carve-out so a future reader does not "fix" it into the run funnel.
    # (Named without the word "fig-ure" on purpose: conftest's fast-partition would otherwise
    # misread this as a slow render test and auto-deselect the guard.)
    _f, _checked, exempt = GUARD.check_doors(ROOT)
    assert (ROOT / "docs/FIGURES_START_HERE.md").is_file()
    assert "docs/FIGURES_START_HERE.md" not in _checked
    assert not any(p.name == Path("docs/FIGURES_START_HERE.md").name for p in GUARD.discover_doors(ROOT))


def test_start_exists_and_exits_zero():
    """Invariant (3): the runtime door exists and runs offline. `--no-doctor` keeps it fast
    and free of environment/network dependence."""
    runner = ROOT / "mamey_run.py"
    assert runner.exists(), "mamey_run.py (the runtime door) is missing"
    out = subprocess.run(
        [sys.executable, str(runner), "start", "--no-doctor"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=180,
    )
    assert out.returncode == 0, out.stderr[-500:]
    assert "python mamey_run.py" in out.stdout, "start must print the canonical idiom"
