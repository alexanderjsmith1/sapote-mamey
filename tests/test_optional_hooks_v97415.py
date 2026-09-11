"""Optional hooks run only when invoked; generic isolated fixtures exercise their guards."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / 'hooks'
NAMES = ('require_phylo_workflow.sh', 'block_blastp_overconcurrency.sh', 'c10_tool_drift.py',
         'reasoning_self_audit_stop.py', 'state_save_reminder.py',
         'contradiction_and_magnitude_stop.py', 'no_stop_short.py', 'recommendation_contract.py')


def _run(name, tmp_path, payload=None, extra=(), env_extra=None):
    env = dict(os.environ, SAPOTE_WORKSPACE_ROOT=str(tmp_path), CLAUDE_PROJECT_DIR=str(tmp_path),
               TMPDIR=str(tmp_path))
    env.update(env_extra or {})
    command = ['bash' if name.endswith('.sh') else sys.executable, str(HOOKS / name), *extra]
    return subprocess.run(command, input=json.dumps(payload or {}), text=True,
                          capture_output=True, cwd=tmp_path, env=env, timeout=20)


@pytest.mark.parametrize('name', NAMES)
def test_empty_hook_payload_does_not_block_or_install_settings(tmp_path, name):
    result = _run(name, tmp_path)
    assert result.returncode == 0, result.stderr
    assert not (tmp_path / '.claude/settings.json').exists()


def test_phylo_hook_uses_local_checker_and_quoted_tree_path(tmp_path):
    tools = tmp_path / 'tools';tools.mkdir()
    checker = tools / 'tree_sanity_check.py'
    checker.write_text('import sys\nraise SystemExit(0)\n')
    tree = tmp_path / 'tree with spaces.nwk';tree.write_text('(A:1,B:1);')
    payload = dict(tool_input=dict(command=f'render_clean_tree "{tree}"'))
    assert _run('require_phylo_workflow.sh', tmp_path, payload).returncode == 0
    checker.write_text('import sys\nprint("PASS-looking text")\nraise SystemExit(3)\n')
    result = _run('require_phylo_workflow.sh', tmp_path, payload)
    assert result.returncode == 2 and 'BLOCKED' in result.stderr
    checker.unlink()
    assert _run('require_phylo_workflow.sh', tmp_path, payload).returncode == 2


def test_tool_drift_baseline_reports_modification(tmp_path):
    tools = tmp_path / 'tools';tools.mkdir();target = tools / 'example.py';target.write_text('first')
    payload = dict(session_id='synthetic-session')
    assert _run('c10_tool_drift.py', tmp_path, payload, ('--mode', 'baseline')).returncode == 0
    target.write_text('second')
    result = _run('c10_tool_drift.py', tmp_path, payload, ('--mode', 'check'))
    assert 'MODIFIED: tools/example.py' in result.stderr


def test_open_task_contract_blocks_but_completed_contract_allows(tmp_path):
    state = tmp_path / '.claude/state';state.mkdir(parents=True)
    contract = state / 'TASK_CONTRACT.md';contract.write_text('- [ ] run unique fixture checks\n')
    assert _run('no_stop_short.py', tmp_path).returncode == 2
    contract.write_text('- [x] run unique fixture checks\n')
    assert _run('no_stop_short.py', tmp_path).returncode == 0


def test_state_reminder_uses_configurable_generic_root(tmp_path):
    state = tmp_path / 'custom states/session';state.mkdir(parents=True)
    file = state / 'STATE.md';file.write_text('checkpoint')
    import time
    old = time.time() - 3 * 3600;os.utime(file, (old, old))
    result = _run('state_save_reminder.py', tmp_path,
                  env_extra={'SAPOTE_TASK_STATE_ROOT': str(state.parent)})
    assert 'session' in result.stderr and 'STATE-SAVE CADENCE' in result.stderr


def test_reasoning_and_numeric_hooks_expose_review_requests(tmp_path):
    transcript = tmp_path / 'transcript.jsonl'
    transcript.write_text('\n'.join(json.dumps(r) for r in [
        dict(type='user', message=dict(content='1 protein a minute')),
        dict(type='assistant', message=dict(content=[dict(type='text', text='Confirmed 7 proteins per minute')]))
    ]))
    for name in ('reasoning_self_audit_stop.py', 'contradiction_and_magnitude_stop.py'):
        result = _run(name, tmp_path, dict(transcript_path=str(transcript)))
        assert json.loads(result.stdout)['decision'] == 'block'
        # Same text is debounced so the optional check cannot trap a stop loop.
        assert not _run(name, tmp_path, dict(transcript_path=str(transcript))).stdout
