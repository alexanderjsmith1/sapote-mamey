"""Regressions for the BLASTp concurrency gate shipped with v9.7.415.

Both defects push the same way — MORE concurrent NCBI submitters than the governed ceiling, which is
the exact failure the hook's own deny text cites (2026-08-21: 43 lanes, ~90 minutes throttled).

`ps` is stubbed on PATH so the live-lane count is deterministic and nothing is ever launched.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / 'hooks' / 'block_blastp_overconcurrency.sh'

TWO_PLAIN = ['python3 /T/nr_rid_runner.py run --lane 1',
             'python3 /T/nr_rid_runner.py run --lane 2']
TWO_NOHUP = ['nohup python3 /T/nr_rid_runner.py run --lane 1',
             'nohup python3 /T/nr_rid_runner.py run --lane 2']
TWO_ENV = ['env python3 /T/nr_rid_runner.py run --lane 1',
           '/bin/sh -c python3 /T/nr_rid_runner.py run --lane 2']
NONE_LIVE = []


def _verdict(tmp_path, live_lines, command, cap='2'):
    stub = tmp_path / 'stub'
    stub.mkdir(exist_ok=True)
    body = '\n'.join(['COMMAND', *live_lines])
    (stub / 'ps').write_text("#!/bin/sh\ncat <<'LINES'\n" + body + "\nLINES\n")
    (stub / 'ps').chmod(0o755)
    env = dict(os.environ, PATH=f"{stub}{os.pathsep}{os.environ['PATH']}",
               SAPOTE_BLASTP_MAX_LANES=cap)
    r = subprocess.run(['bash', str(HOOK)], text=True, capture_output=True, timeout=60,
                       env=env, cwd=tmp_path,
                       input=json.dumps({'tool_input': {'command': command}}))
    assert r.returncode == 0, r.stderr
    if not r.stdout.strip():
        return 'ALLOW'
    return json.loads(r.stdout)['hookSpecificOutput']['permissionDecision'].upper()


# --- E1: an inspection WORD anywhere in the command exempted a real launch -------------------

@pytest.mark.parametrize('command', [
    'python3 nr_rid_runner.py run --lane 3 | grep RID',
    'python3 nr_rid_runner.py run --lane 3 && cat out.log',
    'python3 nr_rid_runner.py run --lane 3 | tail -f',
    'python3 nr_rid_runner.py run --lane 3 > log && head -5 log',
])
def test_a_launch_is_not_exempt_because_it_pipes_into_an_inspection_tool(tmp_path, command):
    """Piping a launch's output through grep does not make it an inspection command."""
    assert _verdict(tmp_path, TWO_PLAIN, command) == 'DENY'


@pytest.mark.parametrize('command', [
    'ps -eo command | grep nr_rid_runner.py run',
    "pkill -f 'nr_rid_runner.py run'",
    "tail -f blastp.log | grep 'nr_rid_runner.py run'",
    "grep -c 'nr_rid_runner.py run' fleet.log",
])
def test_real_inspection_commands_still_pass(tmp_path, command):
    """The exemption must survive: these look at the fleet, they do not add to it."""
    assert _verdict(tmp_path, TWO_PLAIN, command) == 'ALLOW'


def test_a_leading_env_assignment_does_not_disguise_a_launch(tmp_path):
    assert _verdict(tmp_path, TWO_PLAIN,
                    'SAPOTE_BLASTP_MAX_LANES=2 python3 nr_rid_runner.py run --lane 3') == 'DENY'


@pytest.mark.parametrize('command', [
    'cat log && python3 nr_rid_runner.py run --lane 3',
    'grep RID log; python3 nr_rid_runner.py run --lane 3',
    'cat "$(python3 nr_rid_runner.py run --lane 3)"',
])
def test_inspection_prefix_does_not_hide_a_later_launch(tmp_path, command):
    assert _verdict(tmp_path, TWO_PLAIN, command) == 'DENY'


# --- E2: the live-lane count only saw runners launched as a bare `python` --------------------

@pytest.mark.parametrize('live', [TWO_NOHUP, TWO_ENV,
                                  ['caffeinate -i python3 /T/nr_rid_runner.py run --lane 1',
                                   '/T/nr_rid_runner.py run --lane 2']])
def test_live_lanes_are_counted_through_ordinary_wrappers(tmp_path, live):
    """nohup / env / caffeinate / a shebang launch are all normal ways to start a lane."""
    assert _verdict(tmp_path, live, 'python3 nr_rid_runner.py run --lane 3') == 'DENY'


def test_a_bare_python_launch_is_still_counted(tmp_path):
    assert _verdict(tmp_path, TWO_PLAIN, 'python3 nr_rid_runner.py run --lane 3') == 'DENY'


# --- the gate must not become a wall --------------------------------------------------------

def test_the_first_lane_passes_when_nothing_is_live(tmp_path):
    assert _verdict(tmp_path, NONE_LIVE, 'python3 nr_rid_runner.py run --lane 1') == 'ALLOW'


def test_a_staggered_second_lane_passes_under_the_cap(tmp_path):
    assert _verdict(tmp_path, ['python3 /T/nr_rid_runner.py run --lane 1'],
                    'sleep 90 && python3 nr_rid_runner.py run --lane 2', cap='4') == 'ALLOW'


def test_an_unstaggered_second_lane_is_denied(tmp_path):
    assert _verdict(tmp_path, ['python3 /T/nr_rid_runner.py run --lane 1'],
                    'python3 nr_rid_runner.py run --lane 2', cap='4') == 'DENY'


def test_a_command_that_is_not_a_runner_launch_is_ignored(tmp_path):
    assert _verdict(tmp_path, TWO_PLAIN, 'python3 some_other_tool.py --go') == 'ALLOW'
