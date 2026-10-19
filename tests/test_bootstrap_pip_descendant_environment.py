"""Exercise bootstrap and a harmless child shim; never invoke pip or a backend."""
from pathlib import Path
import json
import os
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("offline,core_only", [(True, False), (True, True), (False, False)])
def test_pip_descendant_environment_and_explicit_options(tmp_path, offline, core_only):
    wheels = tmp_path / "local wheels with spaces"
    wheels.mkdir()
    log = tmp_path / "shim.jsonl"
    shim = tmp_path / "fake python"
    shim.write_text("#!" + sys.executable + "\n" + '''import json, os, subprocess, sys
a = sys.argv[1:]
if a == ['--version']:
    print('Python 3.13.13')
if a[:2] == ['-m', 'pip']:
    child = subprocess.run([sys.executable, '-B', '-c',
        "import json,os; print(json.dumps({k:v for k,v in os.environ.items() if k.startswith('PIP_')}))"],
        capture_output=True, text=True, check=True)
    with open(os.environ['BOOTSTRAP_SHIM_LOG'], 'a') as stream:
        stream.write(json.dumps({'args': a, 'child_environment': json.loads(child.stdout)}) + '\\n')
    if '.[all]' in a and os.environ['FAKE_CORE_ONLY'] == '1':
        sys.exit(1)
''')
    shim.chmod(0o755)
    ambient = {
        'PIP_FIND_LINKS': 'https://example.invalid/synthetic-links',
        'PIP_INDEX_URL': 'https://example.invalid/synthetic-index',
        'PIP_EXTRA_INDEX_URL': 'https://example.invalid/synthetic-extra',
        'PIP_TRUSTED_HOST': 'example.invalid',
        'PIP_CONFIG_FILE': str(tmp_path / 'unused-pip.conf'),
        'PIP_FUTURE_OPTION': 'synthetic-unknown-option',
        'PIP_ARGS': 'synthetic-exported-name-collision',
        'PIP_COMMAND': 'synthetic-exported-name-collision',
    }
    # Retain only our invented pip values, so no ambient credentials enter a log.
    env = {k: v for k, v in os.environ.items() if not k.startswith('PIP_')}
    env.update(ambient, PYTHON=str(shim), BOOTSTRAP_SHIM_LOG=str(log),
               FAKE_CORE_ONLY=str(int(core_only)), PYTHONDONTWRITEBYTECODE='1')
    argv = ['bash', str(ROOT / 'bootstrap.sh')]
    if offline:
        argv += ['--wheels', str(wheels)]
    result = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    calls = [json.loads(line) for line in log.read_text().splitlines()]
    probes = [call for call in calls if '--version' in call['args']]
    assert len(probes) == 1
    assert ('--isolated' in probes[0]['args']) == offline
    if offline:
        assert probes[0]['child_environment'] == {'PIP_CONFIG_FILE': os.devnull}
    calls = [call for call in calls if 'install' in call['args']]
    assert len(calls) == (3 if core_only else 2)
    for call in calls:
        assert call['args'][:2] == ['-m', 'pip']
        assert '--upgrade' in call['args']  # Local PIP_ARGS array survived sanitation.
        assert str(ROOT / 'wheels') in call['args']
        if offline:
            assert call['child_environment'] == {'PIP_CONFIG_FILE': os.devnull}
            assert '--isolated' in call['args'] and '--no-index' in call['args']
            assert str(wheels) in call['args']
        else:
            for key, value in ambient.items():
                if key not in {'PIP_ARGS', 'PIP_COMMAND'}:
                    assert call['child_environment'].get(key) == value
            assert '--isolated' not in call['args'] and '--no-index' not in call['args']
    if core_only:
        assert 'bootstrap done: CORE_ONLY' in result.stdout
