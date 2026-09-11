"""The legacy contract freshness gate now reads the shared assistant contract."""
from pathlib import Path
import re
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
START = ROOT / 'AGENTS.md'


def _versions():
    p = tomllib.loads((ROOT / 'pyproject.toml').read_text())
    return p['project']['version'], p['tool']['sapote']['bundle_version']


def test_shared_contract_exists_at_root():
    assert START.is_file()


def test_initiation_prompt_version_matches_pyproject():
    engine, bundle = _versions()
    assert f'v{bundle} / {engine}' in START.read_text()


def test_build_stamp_matches():
    build = re.search(r'build=(\S+)', (ROOT / 'BUILD_STAMP.txt').read_text()).group(1)
    assert build in START.read_text()


def test_has_shared_initiation_prompt_block():
    text = START.read_text()
    assert 'SHARED ASSISTANT CONTRACT' in text
    assert 'CHATGPT MODE ACTIVE' not in text


def test_legacy_receipt_marker_is_preserved_as_metadata():
    from mamey.llm_handoff import HANDSHAKE
    text = START.read_text()
    assert HANDSHAKE in text
    assert 'compatibility metadata' in text


def test_reports_current_file_hash():
    import hashlib
    result = subprocess.run([sys.executable, 'mamey_run.py', 'chatgpt-init'],
                            cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0
    assert hashlib.sha256(START.read_bytes()).hexdigest() in result.stdout


def test_gotcha_section_header_version_matches_pyproject():
    engine, bundle = _versions()
    match = re.search(r'##\s*3\s*·\s*Known gotchas.*\((.+?)\)', START.read_text())
    assert match and f'v{bundle} / {engine}' in match.group(1)


def test_every_assistant_uses_the_same_named_profile_and_identity_safeguards():
    text = START.read_text()
    for token in ['strain / full node-or-contig / region / BGC alias', 'verify-modeb', 'verify-guide',
                  'emit-modeb-template', 'PASS_STRUCTURE', 'LLM_COMPANION_TOOL_PROTOCOL.md']:
        assert token in text
