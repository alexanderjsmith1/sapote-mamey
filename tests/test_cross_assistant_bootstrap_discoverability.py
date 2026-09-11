"""Two audiences and one shared coding-assistant contract."""
from pathlib import Path
import subprocess
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]


def _surfaces():
    return yaml.safe_load((ROOT / 'bootstrap_contract.yml').read_text())['bootstrap_surfaces']


def test_required_bootstrap_surfaces_exist():
    assert not [s['path'] for s in _surfaces() if s['required'] and not (ROOT / s['path']).is_file()]


def test_canonical_one_door_carries_the_full_bootstrap_guarantee():
    text = (ROOT / 'AGENTS.md').read_text()
    assert (ROOT / 'CLAUDE.md').read_text() == text
    assert 'every coding assistant' in text
    assert 'Automatic instruction-file discovery varies by assistant' in text
    assert 'Claude discovery copy' in text
    assert 'python mamey_run.py start' in text
    assert '--capped-session' in text
    assert 'CURRENT_DOCS_INDEX.md' in text


def test_start_runtime_carries_timeout_safe_first_run_and_names_the_one_door():
    result = subprocess.run([sys.executable, 'mamey_run.py', 'start', '--no-doctor'],
                            cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    assert '--capped-session' in result.stdout
    assert 'AGENTS.md' in result.stdout
    assert 'assistant-specific rules' not in result.stdout


def test_timeout_word_survives_in_the_canonical_contract():
    assert 'timeout' in (ROOT / 'AGENTS.md').read_text().lower()


def test_human_landing_routes_to_shared_contract():
    text = (ROOT / 'README.md').read_text()
    assert '[AGENTS.md](AGENTS.md)' in text
    assert 'python mamey_run.py start' in text


def test_shared_bootstrap_declares_the_contract_map():
    text = (ROOT / 'AGENTS.md').read_text()
    assert 'bootstrap_contract.yml' in text
    for surface in _surfaces():
        assert surface['path'] in text


def test_no_separate_assistant_front_doors_are_shipped():
    assert not (ROOT / 'start_here').exists()
    assert not list(ROOT.glob('*_START_HERE.md'))
    assert not list(ROOT.glob('*READ_ME_FIRST*.md'))


def test_legacy_init_command_reports_shared_contract():
    result = subprocess.run([sys.executable, 'mamey_run.py', 'chatgpt-init'],
                            cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    for rel in ['AGENTS.md', 'CLAUDE.md', 'README.md', 'bootstrap_contract.yml']:
        assert rel in result.stdout
    assert 'sha256' in result.stdout
