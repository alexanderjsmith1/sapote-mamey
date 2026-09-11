"""Regressions for five defects measured in the optional hooks shipped with v9.7.415.

Every test below fails on the pristine .415 tree and passes with the BLIZZARD_BLUE-416 fixes.
The existing suite (tests/test_optional_hooks_v97415.py) passes on both, because each of its
fixtures configures the happy path: it never runs the no_stop_short backstop past its release,
never leaves SAPOTE_TASK_STATE_ROOT unset, never varies the session_id between baseline and
check, and never puts a backtick in the transcript text.
"""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOKS = ROOT / 'hooks'


def _run(name, tmp_path, payload=None, extra=(), env_extra=None):
    env = dict(os.environ, SAPOTE_WORKSPACE_ROOT=str(tmp_path), CLAUDE_PROJECT_DIR=str(tmp_path),
               TMPDIR=str(tmp_path))
    env.update(env_extra or {})
    command = ['bash' if name.endswith('.sh') else sys.executable, str(HOOKS / name), *extra]
    return subprocess.run(command, input=json.dumps(payload or {}), text=True,
                          capture_output=True, cwd=tmp_path, env=env, timeout=60)


def _load(name):
    spec = importlib.util.spec_from_file_location(f'_hook_{name}', HOOKS / f'{name}.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _transcript(path, records):
    path.write_text('\n'.join(json.dumps(r) for r in records) + '\n')
    return path


def _asst(text):
    return dict(type='assistant', message=dict(content=[dict(type='text', text=text)]))


# --- D1: the no_stop_short backstop released once and immediately re-armed ------------------

def test_no_stop_short_release_persists_for_an_unchanged_contract(tmp_path):
    """Deleting the counter on release restarted it, giving a permanent 5-block/1-release cycle."""
    state = tmp_path / '.claude/state'
    state.mkdir(parents=True)
    (state / 'TASK_CONTRACT.md').write_text('- [ ] finish the audit\n')

    codes = [_run('no_stop_short.py', tmp_path).returncode for _ in range(12)]
    assert 2 in codes, 'the contract has an open item; it must block at least once'
    first_release = codes.index(0)
    assert all(c == 0 for c in codes[first_release:]), (
        f'once released the backstop must stay released for the same contract text; got {codes}')


def test_no_stop_short_rearms_when_the_contract_is_edited(tmp_path):
    """The release is keyed to the contract text, so real progress must arm the block again."""
    state = tmp_path / '.claude/state'
    state.mkdir(parents=True)
    contract = state / 'TASK_CONTRACT.md'
    contract.write_text('- [ ] finish the audit\n')
    for _ in range(8):
        _run('no_stop_short.py', tmp_path)
    assert _run('no_stop_short.py', tmp_path).returncode == 0, 'precondition: released'

    contract.write_text('- [ ] finish the audit\n- [ ] and reconcile the counts\n')
    assert _run('no_stop_short.py', tmp_path).returncode == 2

    contract.write_text('- [x] finish the audit\n- [x] and reconcile the counts\n')
    assert _run('no_stop_short.py', tmp_path).returncode == 0


# --- D2: both transcript hooks read the entire .jsonl on every Stop -------------------------

def test_self_audit_reads_only_the_transcript_tail(tmp_path):
    """A bounded window is the whole point: 309 MB transcripts exist in an active workspace."""
    mod = _load('reasoning_self_audit_stop')
    path = _transcript(tmp_path / 't.jsonl',
                       [_asst('early filler ' + 'x' * 4000)] * 4 + [_asst('the last reply')])
    recs = mod.tail_records(str(path), ('assistant',), cap=2048)
    texts = [''.join(p.get('text', '') for p in r.get('message', {}).get('content', []))
             for r in recs]
    assert any('the last reply' in t for t in texts)
    assert not any('early filler' in t for t in texts), (
        'a 2 KB window must not reach records tens of KB earlier in the file')
    assert mod.last_assistant_text(str(path)) == 'the last reply'


def test_contradiction_hook_reads_only_the_transcript_tail(tmp_path):
    mod = _load('contradiction_and_magnitude_stop')
    path = _transcript(tmp_path / 't.jsonl',
                       [_asst('early filler ' + 'y' * 4000)] * 4 +
                       [dict(type='user', message=dict(content='1 protein a minute')),
                        _asst('Confirmed 7 proteins per minute')])
    recs = mod._tail_records(str(path), ('user', 'assistant'), cap=2048)
    blob = json.dumps(recs)
    assert 'Confirmed 7 proteins per minute' in blob and '1 protein a minute' in blob
    assert 'early filler' not in blob

    user_txt, asst_txt = mod._last_messages(str(path))
    assert user_txt == '1 protein a minute' and asst_txt == 'Confirmed 7 proteins per minute'


def test_transcript_hooks_still_block_on_a_small_transcript(tmp_path):
    """The tail window must not change the verdict on an ordinary transcript."""
    path = _transcript(tmp_path / 't.jsonl',
                       [dict(type='user', message=dict(content='1 protein a minute')),
                        _asst('Confirmed 7 proteins per minute')])
    for name in ('reasoning_self_audit_stop.py', 'contradiction_and_magnitude_stop.py'):
        result = _run(name, tmp_path, dict(transcript_path=str(path)))
        assert json.loads(result.stdout)['decision'] == 'block', name


# --- D3: any backticked token counted as a receipt and silenced the self-audit --------------

@pytest.mark.parametrize('text', [
    'Confirmed: there is no such file anywhere in the tree. I used `--strict` for this.',
    'I verified exactly 40 regions are present; run it with `-v`.',
    'There are no remaining failures — all 12 pass under `pytest`.',
])
def test_self_audit_preserves_permissive_backtick_policy(tmp_path, text):
    path = _transcript(tmp_path / 't.jsonl', [_asst(text)])
    result = _run('reasoning_self_audit_stop.py', tmp_path, dict(transcript_path=str(path)))
    assert not result.stdout.strip(), 'receipt policy tightening was not selected'


@pytest.mark.parametrize('text', [
    'Confirmed: there is no such file — checked `mamey/cli.py` line by line.',
    'Verified exactly 40 regions, see `OFFICIAL_DATA/ASSET_REGISTRY.tsv`.',
    'There are no orphans left; the sweep reported `147/147` clean.',
    'Confirmed against sha `73e608ac8357aaf3`.',
])
def test_self_audit_stays_silent_when_the_backtick_carries_evidence(tmp_path, text):
    path = _transcript(tmp_path / 't.jsonl', [_asst(text)])
    result = _run('reasoning_self_audit_stop.py', tmp_path, dict(transcript_path=str(path)))
    assert not result.stdout.strip(), f'a cited path/count/digest IS a receipt: {text!r}'


# --- D4: state_save_reminder went silent when its root did not exist ------------------------

def test_state_reminder_reports_a_missing_state_root(tmp_path):
    """`task_state/` is a generic default; a workspace that names the directory anything else got
    permanent silence, which reads as 'everyone is current'."""
    result = _run('state_save_reminder.py', tmp_path)
    assert result.returncode == 0, 'a reminder must never wedge a Stop'
    assert 'task_state' in result.stderr and 'SAPOTE_TASK_STATE_ROOT' in result.stderr


def test_state_reminder_debounces_the_misconfiguration_warning(tmp_path):
    assert _run('state_save_reminder.py', tmp_path).stderr.strip()
    assert not _run('state_save_reminder.py', tmp_path).stderr.strip(), 'must not nag every Stop'


def test_state_reminder_is_silent_when_the_root_exists_and_is_current(tmp_path):
    root = tmp_path / 'task_state' / 'session'
    root.mkdir(parents=True)
    (root / 'STATE.md').write_text('checkpoint')
    assert not _run('state_save_reminder.py', tmp_path).stderr.strip()


# --- D5: c10_tool_drift failed open silently, and wrote project state to fail open ----------

def test_c10_check_without_a_baseline_creates_no_project_state(tmp_path):
    (tmp_path / 'tools').mkdir()
    (tmp_path / 'tools' / 'a.py').write_text('print(1)\n')
    _run('c10_tool_drift.py', tmp_path, dict(session_id='abc'), ('--mode', 'check'))
    assert not (tmp_path / 'SAPOTE_CONTROL').exists(), (
        'a check that has nothing to compare must not create state in the project')


def test_c10_says_it_is_unarmed_when_the_session_id_does_not_match(tmp_path):
    """A Stop payload with no session_id looked for baseline__shared.json, never found it, and
    passed over every real tools/ modification without a word."""
    (tmp_path / 'tools').mkdir()
    target = tmp_path / 'tools' / 'a.py'
    target.write_text('print(1)\n')
    _run('c10_tool_drift.py', tmp_path, dict(session_id='abc'), ('--mode', 'baseline'))
    target.write_text('print(2)\n')

    matched = _run('c10_tool_drift.py', tmp_path, dict(session_id='abc'), ('--mode', 'check'))
    assert 'MODIFIED: tools/a.py' in matched.stderr, 'precondition: it detects drift when armed'

    unarmed = _run('c10_tool_drift.py', tmp_path, {}, ('--mode', 'check'))
    assert unarmed.returncode == 0
    assert 'unarmed' in unarmed.stderr.lower(), 'silence here is indistinguishable from "no drift"'


def test_c10_is_silent_when_no_session_ever_took_a_baseline(tmp_path):
    """A session that predates the hook has nothing to say — that silence is correct."""
    (tmp_path / 'tools').mkdir()
    (tmp_path / 'tools' / 'a.py').write_text('print(1)\n')
    result = _run('c10_tool_drift.py', tmp_path, dict(session_id='abc'), ('--mode', 'check'))
    assert result.returncode == 0 and not result.stderr.strip()

@pytest.mark.parametrize('module,function', [('reasoning_self_audit_stop','tail_records'),('contradiction_and_magnitude_stop','_tail_records')])
def test_tail_honors_exact_byte_cap(monkeypatch,module,function):
    import io
    mod=_load(module)
    blob=b'x'*10000+b'\n'+json.dumps(_asst('latest')).encode()+b'\n'
    read_sizes=[]
    class Tracking(io.BytesIO):
        def read(self,n=-1):
            out=super().read(n);read_sizes.append(len(out));return out
    monkeypatch.setattr(mod.os.path,'getsize',lambda path:len(blob))
    monkeypatch.setattr(mod,'open',lambda *a,**k:Tracking(blob),raising=False)
    records=getattr(mod,function)('fixture',('assistant',),cap=2048)
    assert sum(read_sizes)<=2048
    assert records[-1]['type']=='assistant'

@pytest.mark.parametrize('module,function', [('reasoning_self_audit_stop','tail_records'),('contradiction_and_magnitude_stop','_tail_records')])
def test_tool_only_tail_does_not_hide_prior_text(tmp_path,module,function):
    mod=_load(module)
    path=_transcript(tmp_path/'long.jsonl',[_asst('retained text'),
        dict(type='assistant',message=dict(content=[dict(type='tool_use',input='x'*(2*1024*1024))]))])
    records=getattr(mod,function)(str(path),('assistant',))
    assert any('retained text' in json.dumps(record) for record in records)
