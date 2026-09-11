"""Shared bootstrap generation and automatic-discovery alias policy."""
from pathlib import Path
import importlib.util
import shutil
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]


def _contract():
    return yaml.safe_load((ROOT / 'bootstrap_contract.yml').read_text())


def _renderer():
    spec = importlib.util.spec_from_file_location('shared_bootstrap_renderer', ROOT / 'tools/render_bootstrap_contract.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixture(tmp_path):
    for rel in ['AGENTS.md', 'CLAUDE.md', 'README.md', 'bootstrap_contract.yml', 'pyproject.toml',
                'BUILD_STAMP.txt', 'docs/BOOTSTRAP_FILE_AUDIT.md']:
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / rel, p)
    return tmp_path


def test_contract_declares_one_shared_agent_authority():
    contract = _contract()
    assert contract['challenge_response']['canonical_instruction_file'] == 'AGENTS.md'
    authorities = [s['path'] for s in contract['bootstrap_surfaces'] if s['scanner_authority']]
    assert authorities == ['AGENTS.md']
    assert {s['role'] for s in contract['bootstrap_surfaces']} == {
        'canonical_agent_contract', 'agent_discovery_alias', 'human_landing_page', 'generated_bootstrap_map'}


def test_discovery_alias_is_generated_and_byte_identical():
    alias = _contract()['generated_markdown']['agent_discovery_alias']
    assert alias == {'target': 'CLAUDE.md', 'source': 'AGENTS.md', 'replacement_marker': 'full_file'}
    assert (ROOT / 'AGENTS.md').read_bytes() == (ROOT / 'CLAUDE.md').read_bytes()


def test_generated_bootstrap_docs_are_current():
    result = subprocess.run([sys.executable, 'tools/render_bootstrap_contract.py', '--check'],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"status": "PASS"' in result.stdout


def test_known_gotchas_are_generated_from_registry():
    text = (ROOT / 'AGENTS.md').read_text()
    assert 'BEGIN GENERATED: known_gotchas_section' in text
    for g in _contract()['known_gotchas']:
        if g['status'] == 'active':
            assert g['id'] in text


def test_missing_shared_contract_fails_closed(tmp_path):
    tree = _fixture(tmp_path)
    (tree / 'AGENTS.md').unlink()
    assert _renderer().check(tree)


def test_divergent_discovery_alias_fails_then_regenerates(tmp_path):
    tree = _fixture(tmp_path)
    (tree / 'CLAUDE.md').write_text('different operating rules\n')
    renderer = _renderer()
    assert any('CLAUDE.md' in error for error in renderer.check(tree))
    renderer.apply(tree)
    assert renderer.check(tree) == []
    assert renderer.apply(tree) == []
