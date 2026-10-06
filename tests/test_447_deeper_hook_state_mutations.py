"""Bounded variable/cwd repair probes: payloads are data, never shell execution."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
HOOK = Path(os.environ.get('SAPOTE_DEEPER_STATE_HOOK', str(ROOT/'hooks/block_out_of_bounds_writes.py')))
OUT = '/opt/sapote_state_mutation_outside'


def denied(command, project, extra_env=None):
    env = {**os.environ, 'SAPOTE_WORKSPACE_ROOT': str(project), 'CLAUDE_PROJECT_DIR': str(project),
           'PWD': str(project), 'DEST': str(project), 'TARGET': str(project),
           'REPLY': str(project), 'MAPFILE': str(project), **(extra_env or {})}
    env.pop('CDPATH', None)
    result = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(
        {'tool_name':'Bash', 'tool_input':{'command': command}, 'cwd':str(project)}),
        capture_output=True, text=True, cwd=project, env=env)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout) if result.stdout.strip() else {}
    return payload.get('hookSpecificOutput', {}).get('permissionDecision') == 'deny'


@pytest.mark.parametrize('mutation, name', [
    (f'printf -v DEST {OUT}', 'DEST'),
    (f'printf -vDEST {OUT}', 'DEST'),
    (f'printf -v "DEST[0]" {OUT}', 'DEST'),
    (f'command printf -v DEST {OUT}', 'DEST'),
    (f'builtin printf -v DEST {OUT}', 'DEST'),
    (f'read -r DEST <<< {OUT}', 'DEST'),
    (f'read DEST <<< {OUT}', 'DEST'),
    (f'read <<< {OUT}', 'REPLY'),
    (f'read -ra DEST <<< {OUT}', 'DEST'),
    (f'read -a DEST <<< {OUT}', 'DEST'),
    (f'read -p "prompt" -r DEST <<< {OUT}', 'DEST'),
    (f'read -n2 DEST <<< {OUT}', 'DEST'),
    (f'mapfile -t DEST <<< {OUT}', 'DEST'),
    (f'mapfile -t <<< {OUT}', 'MAPFILE'),
    (f'readarray -t DEST <<< {OUT}', 'DEST'),
    (f'DEST[0]={OUT}', 'DEST'),
    ('DEST+=/..', 'DEST'),
    ('DEST[0]+=/..', 'DEST'),
    (f'declare -n REF=TARGET; REF={OUT}', 'TARGET'),
    (f'TARGET_NAME=TARGET; declare -n REF="$TARGET_NAME"; REF={OUT}', 'TARGET'),
    (f'declare -n REF=TARGET; read REF <<< {OUT}', 'TARGET'),
    (f'declare -n REF=TARGET; printf -v REF {OUT}', 'TARGET'),
    (f'declare -i DEST; DEST={OUT}', 'DEST'),
    (f'declare -a DEST; DEST[0]={OUT}', 'DEST'),
])
def test_mutated_or_unmodeled_variable_cannot_keep_stale_inside_path(mutation, name, tmp_path):
    assert denied(f'{mutation}; touch "${name}/a.txt"', tmp_path)


@pytest.mark.parametrize('command', [
    f'printf -v DEST {OUT}; printf "%s" "$DEST"',
    f'read -r DEST <<< {OUT}; printf "%s" "$DEST"',
    f'mapfile -t DEST <<< {OUT}; printf "%s" "$DEST"',
    f'DEST[0]={OUT}; printf "%s" "$DEST"',
    f'read -r DEST <<< {OUT}; touch ./local.txt',
    f'printf -v DEST {OUT}; touch ./local.txt',
    f'read -p DEST ACTUAL <<< {OUT}; touch "$DEST/a.txt"',
    f'printf -- "-v DEST {OUT}"; touch "$DEST/a.txt"',
    f'env declare DEST={OUT}; touch "$DEST/a.txt"',
    f'env export DEST={OUT}; touch "$DEST/a.txt"',
    'env unset DEST; touch "$DEST/a.txt"',
    f'env printf -v DEST {OUT}; touch "$DEST/a.txt"',
    f'nohup declare DEST={OUT}; touch "$DEST/a.txt"',
    f'nice -n 2 declare DEST={OUT}; touch "$DEST/a.txt"',
    'declare -n REF=TARGET; touch "$TARGET/a.txt"',
    'command -v printf; touch "$DEST/a.txt"',
    f'env -C {OUT} true; touch ./local.txt',
    f'pushd -n {OUT}; touch ./local.txt',
])
def test_read_or_scope_controls_keep_parent_paths(tmp_path, command):
    assert not denied(command, tmp_path)


def test_multiple_read_destinations_invalidate_only_destinations(tmp_path):
    assert denied(f'read OTHER DEST <<< "literal {OUT}"; touch "$DEST/a.txt"', tmp_path)
    assert not denied(f'read OTHER MORE <<< "literal {OUT}"; touch "$DEST/a.txt"', tmp_path)


def test_external_wrapper_write_still_uses_its_chdir(tmp_path):
    assert denied(f'env -C {OUT} touch a.txt', tmp_path)


def test_unsupported_directory_stack_options_do_not_become_paths(tmp_path):
    assert denied(f'pushd -n {OUT}; popd; touch a.txt', tmp_path)
    assert denied(f'pushd {OUT}; pushd "{tmp_path}"; pushd +1; touch a.txt', tmp_path)


def test_variable_mutation_is_scoped_to_subshell(tmp_path):
    assert not denied(f'(printf -v DEST {OUT}); touch "$DEST/a.txt"', tmp_path)
    assert not denied(f'(read DEST <<< {OUT}); touch "$DEST/a.txt"', tmp_path)
    assert not denied(f'(declare -n REF=TARGET; REF={OUT}); touch "$TARGET/a.txt"', tmp_path)


def _module():
    spec = importlib.util.spec_from_file_location('deeper_state_hook', HOOK)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('prefix, physical', [('', False), ('-L ', False), ('-P ', True), ('-LP ', True), ('-PL ', False)])
def test_cd_logical_parent_is_distinct_from_physical_symlink_parent(tmp_path, prefix, physical):
    project = tmp_path/'project'; project.mkdir()
    inner = project/'inner'; inner.mkdir()
    link = tmp_path/'link'; link.symlink_to(inner, target_is_directory=True)
    module = _module()
    targets = module.bash_write_targets(f'cd {prefix}"{link}/.." && touch a.txt', cwd=str(project))
    expected = project/'a.txt' if physical else tmp_path/'a.txt'
    assert [Path(module._real(t)) for t in targets] == [expected]
    assert module._under_allowed(str(expected), [str(project)]) is physical


@pytest.mark.parametrize('mode, physical', [('-P', True), ('+P', False), ('-o physical', True), ('+o physical', False), ('-- -o physical', False)])
def test_shell_physical_mode_is_tracked_without_positional_option_confusion(tmp_path, mode, physical):
    project = tmp_path/'project'; project.mkdir()
    inner = project/'inner'; inner.mkdir()
    link = tmp_path/'link'; link.symlink_to(inner, target_is_directory=True)
    module = _module()
    targets = module.bash_write_targets(f'set {mode}; cd "{link}/.." && touch a.txt', cwd=str(project))
    expected = project/'a.txt' if physical else tmp_path/'a.txt'
    assert [Path(module._real(t)) for t in targets] == [expected]


def test_successive_logical_cd_preserves_lexical_pwd(tmp_path):
    project = tmp_path/'project'; project.mkdir()
    inner = project/'inner'; inner.mkdir()
    link = tmp_path/'link'; link.symlink_to(inner, target_is_directory=True)
    module = _module()
    targets = module.bash_write_targets(f'cd "{link}"; cd ..; touch a.txt', cwd=str(project))
    assert [Path(module._real(t)) for t in targets] == [tmp_path/'a.txt']


def test_mapfile_callback_has_unresolved_parent_state(tmp_path):
    assert denied('mapfile -C callback -c 1 DEST; touch local.txt', tmp_path)
    assert not denied('mapfile -C callback -c 1 DEST; ls', tmp_path)


def test_mutated_implicit_directory_variables_cannot_keep_stale_bindings(tmp_path):
    assert denied(f'printf -v HOME {OUT}; touch ~/.claude/a.txt', tmp_path)
    assert denied(f'read CDPATH <<< {OUT}; cd sub && touch a.txt', tmp_path)
