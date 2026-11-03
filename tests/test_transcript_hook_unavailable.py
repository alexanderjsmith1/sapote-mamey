import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

HOOKS = Path(os.environ.get('SAPOTE_TEST_HOOKS', Path(__file__).resolve().parents[1] / 'hooks'))
NAMES = ['reasoning_self_audit_stop.py', 'contradiction_and_magnitude_stop.py']


def invoke(hook, payload, tmp_path):
    env = os.environ.copy()
    env.update(TMPDIR=str(tmp_path), PYTHONDONTWRITEBYTECODE='1')
    env.pop('PYTHONPYCACHEPREFIX', None)
    return subprocess.run([sys.executable, '-B', str(HOOKS / hook)], input=json.dumps(payload), text=True, capture_output=True, env=env, check=True)


@pytest.mark.parametrize('hook', NAMES)
@pytest.mark.parametrize('kind', ['missing', 'directory'])
def test_explicit_unavailable_is_reported_without_path(hook, kind, tmp_path):
    path = tmp_path / 'PRIVATE_SENTINEL'
    if kind == 'directory':
        path.mkdir()
    result = invoke(hook, {'transcript_path': str(path)}, tmp_path)
    payload = json.loads(result.stdout)
    assert 'transcript unavailable' in payload['systemMessage']
    assert 'PRIVATE_SENTINEL' not in result.stdout
    assert 'decision' not in payload


@pytest.mark.parametrize('hook', NAMES)
@pytest.mark.parametrize('kind', ['absent', 'empty', 'benign'])
def test_optional_and_non_risky_inputs_remain_quiet(hook, kind, tmp_path):
    payload = {}
    if kind != 'absent':
        path = tmp_path / 'transcript.jsonl'
        path.write_text('' if kind == 'empty' else json.dumps({'type': 'assistant', 'message': {'content': 'Hello'}}) + '\n')
        payload['transcript_path'] = str(path)
    result = invoke(hook, payload, tmp_path)
    assert result.stdout == ''


@pytest.mark.parametrize('hook', NAMES)
def test_existing_block_is_preserved(hook, tmp_path):
    path = tmp_path / 'transcript.jsonl'
    records = [{'type':'user','message':{'content':'1 per minute'}}, {'type':'assistant','message':{'content':[{'type':'text','text':'Confirmed 7 per minute'}]}}]
    path.write_text(''.join(json.dumps(r) + '\n' for r in records))
    result = invoke(hook, {'transcript_path':str(path)}, tmp_path)
    payload = json.loads(result.stdout)
    assert payload['decision'] == 'block'
    assert 'systemMessage' not in payload
