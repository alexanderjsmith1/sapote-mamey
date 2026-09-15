"""Fixtures for tools/silent_exit_audit.py.

Each fixture is a shape the tool got wrong at some point during its own construction, so this file
is the record of what it learned as much as a contract.
"""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools' / 'silent_exit_audit.py'


def _load():
    spec = importlib.util.spec_from_file_location('silent_exit_audit', TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _scan(tmp_path, source):
    p = tmp_path / 'h.py'
    p.write_text(source)
    return {(r['line'], r['cls']) for r in _load().scan_file(str(p))}


def _classes(tmp_path, source):
    return {c for _, c in _scan(tmp_path, source)}


def test_the_target_shape_is_flagged_review(tmp_path):
    """The defect this tool exists for: a configured path is absent, so the guard says nothing."""
    got = _scan(tmp_path, '''
import os, sys
def main():
    root = os.environ.get("ROOT") or "task_state"
    if not os.path.isdir(root):
        return 0
    print("something")
    return 0
''')
    assert (6, 'REVIEW') in got


def test_a_failure_status_is_not_a_success_exit(tmp_path):
    """`return 1` matched `v.value in (0, True, ...)` because `True == 1` in Python.

    That one comparison inflated the first engine-wide run from 12 REVIEW rows to 39.
    """
    assert not _scan(tmp_path, '''
import os
def main():
    if not os.path.exists("x"):
        return 1
    return 0
''')


@pytest.mark.parametrize('emitter', ['print("no root")', 'emit("no root")',
                                     'sys.stderr.write("no root")'])
def test_a_branch_that_speaks_is_not_silent(tmp_path, emitter):
    """`emit()` is this codebase's own console helper; omitting it read every mamey/cli.py error
    path as silence."""
    assert not _scan(tmp_path, f'''
import os, sys
def emit(*a, **k): pass
def main():
    if not os.path.exists("x"):
        {emitter}
        return 1
    return 0
''')


def test_a_mode_selector_is_dispatch_not_a_swallowed_verdict(tmp_path):
    assert 'DISPATCH' in _classes(tmp_path, '''
def main():
    mode = "check"
    if mode == "baseline":
        return 0
    return 0
''')


def test_a_helper_returning_none_is_not_a_verdict(tmp_path):
    """`_identify()` returning None means "I could not tell" — the caller still decides."""
    assert not _scan(tmp_path, '''
import os
def _identify(p):
    if not os.path.exists(p):
        return None
    return "x"
''')


def test_a_positive_existence_test_is_not_the_hazard(tmp_path):
    assert 'REVIEW' not in _classes(tmp_path, '''
import os
def main():
    if os.path.exists("x"):
        return 0
    return 0
''')


def test_an_exception_handler_is_fail_open_not_review(tmp_path):
    assert 'FAIL_OPEN' in _classes(tmp_path, '''
import json, sys
def main():
    try:
        json.load(sys.stdin)
    except Exception:
        return 0
    return 0
''')


# The two branches found by hand in the .415 hooks, frozen verbatim. Asserting against the LIVE
# hooks/ tree would have been self-defeating: the moment BLIZZARD_BLUE-416 lands, both branches emit
# a warning and correctly stop being REVIEW, and this test would fail for the right reason — which
# is exactly how a regression test stops testing.
_FROZEN_D4 = """
import os, sys, time
def main():
    base = os.environ.get("SAPOTE_WORKSPACE_ROOT") or os.getcwd()
    colours = os.environ.get("SAPOTE_TASK_STATE_ROOT") or os.path.join(base, "task_state")
    if not os.path.isdir(colours):
        return 0
    print("stale states", file=sys.stderr)
    return 0
"""

_FROZEN_D5 = """
import os, json
def main():
    bpath = os.path.join("SAPOTE_CONTROL", "tool_drift", "baseline__shared.json")
    if not os.path.isfile(bpath):
        return 0
    print("drift")
    return 0
"""


@pytest.mark.parametrize('source,name', [(_FROZEN_D4, 'state_save_reminder'),
                                         (_FROZEN_D5, 'c10_tool_drift')])
def test_recall_on_the_two_branches_found_by_hand(tmp_path, source, name):
    """Recall check: the tool must find, unaided, the shape a human found in these two hooks."""
    assert 'REVIEW' in _classes(tmp_path, source), name


def test_the_branch_stops_being_review_once_it_speaks(tmp_path):
    """And the fix must clear it — otherwise the tool would nag forever at a repaired guard."""
    fixed = _FROZEN_D4.replace("    if not os.path.isdir(colours):\n        return 0",
                               '    if not os.path.isdir(colours):\n'
                               '        print("no state root at " + colours, file=sys.stderr)\n'
                               '        return 0')
    assert 'REVIEW' not in _classes(tmp_path, fixed)


# --- v9.7.420: a speaking branch masked its silent sibling ---------------------------------

def test_a_silent_else_is_not_masked_by_a_speaking_if(tmp_path):
    """Reported by the .420 candidate review: "mutually exclusive stdout branch masks silence".

    `body` and `orelse` were folded into one list, so if EITHER branch emitted, every line in BOTH
    was marked as emitting. The shape below is the `state_save_reminder` defect written as if/else
    instead of an early return — the exact thing this tool exists to find — and it yielded ZERO rows.
    """
    got = _scan(tmp_path, '''
import os
def main():
    root = os.environ.get("ROOT") or "task_state"
    if os.path.isdir(root):
        print("found", root)
    else:
        return 0
    return 0
''')
    assert any(cls == 'REVIEW' for _, cls in got), (
        "a silent else-branch under a speaking if-branch must still be reported")


def test_the_speaking_branch_itself_is_still_not_reported(tmp_path):
    """The fix must not invert: a branch that emits before returning is not silent."""
    got = _scan(tmp_path, '''
import os
def main():
    if os.path.isdir("x"):
        print("found")
        return 0
    return 1
''')
    assert not any(cls == 'REVIEW' for _, cls in got)


def test_both_branches_silent_still_reports(tmp_path):
    got = _scan(tmp_path, '''
import os
def main():
    if os.path.isdir("x"):
        return 0
    else:
        return 0
''')
    assert sum(1 for _, cls in got if cls in ('REVIEW', 'UNCLASSIFIED', 'DISPATCH')) >= 1
