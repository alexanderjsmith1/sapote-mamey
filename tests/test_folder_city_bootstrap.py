"""Relocated bootstrap behavior through public command and hook entry points."""
from pathlib import Path
import json
import os
import subprocess
import sys

import pytest
import yaml
from tests.conftest import hermetic_env

ROOT = Path(__file__).resolve().parents[1]
CHATGPT = 'AGENTS.md'
CLAUDE = 'CLAUDE.md'


@pytest.mark.parametrize('layout', ['direct', 'nested', 'versioned'])
def test_session_hook_reports_executable_root_and_actual_docs(tmp_path, layout):
    bundle = tmp_path if layout == 'direct' else tmp_path / 'sapote-mamey-v9.7.999-CODE-test'
    if layout == 'nested':
        bundle = bundle / 'source'
    bundle.mkdir(parents=True, exist_ok=True)
    for name in ['pyproject.toml', 'mamey_run.py', 'bootstrap_contract.yml', 'CURRENT_DOCS_INDEX.md']:
        (bundle / name).write_text('fixture\n')
    for rel in [CHATGPT, CLAUDE]:
        p = bundle / (Path(rel).name if layout == 'legacy' else rel)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('fixture\n')
    # A newer unselected candidate must not override the versioned bundle.
    if layout != 'direct':
        (tmp_path / 'sapote-mamey-v9.7.1000-CANDIDATE').mkdir()
    proc = subprocess.run(
        ['bash', str(ROOT / 'hooks/sapote_session_start.sh')], text=True, capture_output=True,
        env=hermetic_env(PATH=os.environ['PATH'], SAPOTE_WORKSPACE_ROOT=tmp_path), check=True,
    )
    message = json.loads(proc.stdout)['hookSpecificOutput']['additionalContext']
    assert f'current bundle root is [{bundle}]' in message
    assert 'CURRENT_DOCS_INDEX' in message
    for rel in [CHATGPT, CLAUDE]:
        assert (Path(rel).name if layout == 'legacy' else rel) in message


def test_relocated_handoff_can_activate_safe_mode():
    from mamey.llm_handoff import build_handoff_receipt
    receipt = build_handoff_receipt(ROOT, chatgpt_safe_mode_requested=True)
    assert receipt.status == 'PASS'
    assert receipt.chatgpt_safe_mode_active
    assert CHATGPT in {f['path'] for f in receipt.instruction_files}


def test_generated_full_file_targets_follow_contract(tmp_path):
    """Changing an output in the contract relocates generation without a renderer edit."""
    import shutil
    for rel in ['bootstrap_contract.yml', 'pyproject.toml', 'BUILD_STAMP.txt',
                CHATGPT, 'AGENTS.md']:
        target = tmp_path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, target)
    contract_path = tmp_path / 'bootstrap_contract.yml'
    contract = yaml.safe_load(contract_path.read_text())
    target = 'relocated/generated_alias.md'
    contract['generated_markdown']['agent_discovery_alias']['target'] = target
    contract_path.write_text(yaml.safe_dump(contract, sort_keys=False))
    command = [sys.executable, str(ROOT / 'tools/render_bootstrap_contract.py'), '--root', str(tmp_path)]
    subprocess.run(command + ['--apply'], check=True, capture_output=True, text=True)
    assert (tmp_path / target).is_file()
    assert not (tmp_path / 'CLAUDE.md').exists()
    assert (tmp_path / target).read_bytes() == (tmp_path / 'AGENTS.md').read_bytes()
