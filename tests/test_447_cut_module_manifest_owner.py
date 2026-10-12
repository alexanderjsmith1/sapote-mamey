"""Execute only the actual cut's owner-refresh fragment with mocked Python calls.

No full cut, source synchronization or metadata writers run. Every owner command is
intercepted by the shell function; only synthetic invocation logs are written.
"""
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROPOSED = ROOT / 'tools/release_cut.sh'


def source_refresh_fragment(source):
    first = source.index('say "atomically bump')
    last = source.index('say "gate: version sync"', first)
    return source[first:last]


def execute_owner_fragment(tmp_path, *, writer_present=True, writer_fails=False, inventory_fails=None):
    (tmp_path/'tools').mkdir()
    if writer_present:
        (tmp_path/'tools/check_module_accretion.py').write_text('# mocked owner, never executed\n')
    script = tmp_path/'owner_phase_mock.sh'
    body = source_refresh_fragment(PROPOSED.read_text())
    script.write_text('''#!/usr/bin/env bash
set -euo pipefail
cd -- "$1"
VER=fixture STAMP=fixture
say(){ printf '%s\n' "$*"; }
die(){ printf 'ABORT: %s\n' "$*" >&2; exit 1; }
python3(){
  # NUL framing preserves argv boundaries, including the spaces in python -c.
  printf '%s\\0' "$#" "$@" >> invocation.log
  if [[ "$1" == tools/gen_tools_inventory.py ]]; then
    if [[ "${INVENTORY_FAIL:-}" == ordinary && "$#" == 1 ]] ||
       [[ "${INVENTORY_FAIL:-}" == maintenance && "${2:-}" == --maintenance ]]; then
      printf 'mock inventory refused\n' >&2
      return 2
    fi
  fi
  if [[ "$1" == tools/check_module_accretion.py ]]; then
    [[ -f "$1" ]] || { printf 'mock missing owner\n' >&2; return 2; }
    [[ "${WRITER_FAIL:-0}" == 0 ]] || { printf 'mock owner refused incomplete scan\n' >&2; return 2; }
    [[ "$2" == --write ]] || return 2
  fi
  return 0
}
'''+body+'''
# This stub is only an ordering witness, not the real checksum generator.
refresh_source_integrity(){ printf '1\\0source_integrity\\0' >> invocation.log; }
refresh_source_integrity
printf 'synthetic phase completed\n'
''')
    import os
    environment = dict(os.environ, WRITER_FAIL='1' if writer_fails else '0',
                       INVENTORY_FAIL=inventory_fails or '')
    result = subprocess.run(['bash',str(script),str(tmp_path)],env=environment,text=True,capture_output=True)
    fields = (tmp_path/'invocation.log').read_bytes().split(b'\0')
    assert fields.pop() == b'', 'unterminated invocation log'
    calls = []
    while fields:
        argc = int(fields.pop(0))
        assert argc > 0 and len(fields) >= argc, 'incomplete invocation log'
        calls.append([field.decode('utf-8') for field in fields[:argc]])
        del fields[:argc]
    return result, calls


def test_module_owner_invoked_after_other_source_generators_before_integrity(tmp_path):
    result, calls = execute_owner_fragment(tmp_path)
    assert result.returncode == 0
    assert calls == [
        ['tools/rewrite_release_identity.py', 'fixture', 'fixture', '--root', '.'],
        ['tools/sync_version.py'],
        ['-c', "import sys; sys.path.insert(0,'tools'); import sync_version as sv; sv.sync_build_stamp_patch(check=False)"],
        ['tools/render_bootstrap_contract.py', '--apply'],
        ['tools/gen_command_catalog.py'],
        ['tools/generate_deliverables_menu.py', '--apply'],
        ['tools/gen_tools_inventory.py'],
        ['tools/gen_tools_inventory.py', '--maintenance'],
        ['tools/check_module_accretion.py', '--write'],
        ['source_integrity'],
    ]
    assert 'synthetic phase completed' in result.stdout


@pytest.mark.parametrize('present,fails',[(False,False),(True,True)])
def test_missing_or_refusing_owner_aborts_before_integrity(tmp_path,present,fails):
    result,calls = execute_owner_fragment(tmp_path,writer_present=present,writer_fails=fails)
    assert result.returncode != 0
    assert calls[-1] == ['tools/check_module_accretion.py', '--write']
    assert ['source_integrity'] not in calls
    assert 'module inventory refresh failed.' in result.stderr
    assert 'synthetic phase completed' not in result.stdout


@pytest.mark.parametrize('inventory_fails', ['ordinary', 'maintenance'])
def test_refusing_inventory_aborts_before_module_owner_and_integrity(tmp_path, inventory_fails):
    result, calls = execute_owner_fragment(tmp_path, inventory_fails=inventory_fails)
    assert result.returncode != 0
    inventory_call = ['tools/gen_tools_inventory.py']
    if inventory_fails == 'maintenance':
        inventory_call.append('--maintenance')
    assert calls[-1] == inventory_call
    assert ['tools/check_module_accretion.py', '--write'] not in calls
    assert ['source_integrity'] not in calls
    assert 'mock inventory refused' in result.stderr
    assert 'synthetic phase completed' not in result.stdout


def test_authored_head_accepts_owner_selected_final_build_without_writing(tmp_path):
    import importlib.util
    import shutil
    spec = importlib.util.spec_from_file_location('cut_identity_owner_control', ROOT/'tools/rewrite_release_identity.py')
    owner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(owner)
    names = ['pyproject.toml', 'BUILD_STAMP.txt', 'TIER_MANIFEST.txt', 'CHANGELOG.md']
    for name in names:
        shutil.copy2(ROOT/name, tmp_path/name)
    before = {name:(tmp_path/name).read_bytes() for name in names}
    proposed = owner.desired_files(tmp_path, '9.7.447', '20261004v97447b')
    head, remaining = proposed[tmp_path/'CHANGELOG.md'].split('\n', 1)
    assert 'build 20261004v97447b' in head
    assert 'unsealed cut candidate' in head
    assert remaining == before['CHANGELOG.md'].decode().split('\n', 1)[1]
    assert 'build=20261004v97447b' in proposed[tmp_path/'BUILD_STAMP.txt']
    assert {name:(tmp_path/name).read_bytes() for name in names} == before
