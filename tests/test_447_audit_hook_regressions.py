"""R01–R04/R07: synthetic hook payloads; never execute the command under review."""
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
OUT = '/opt/sapote_audit_outside'


def decision(hook, command, project, extra_env=None):
    env = {**os.environ, 'SAPOTE_WORKSPACE_ROOT': str(project), 'CLAUDE_PROJECT_DIR': str(project),
           **(extra_env or {})}
    result = subprocess.run(['python3' if hook.endswith('.py') else 'bash', str(ROOT/'hooks'/hook)],
                            input=json.dumps({'tool_name': 'Bash', 'tool_input': {'command': command},
                                              'cwd': str(project)}),
                            text=True, capture_output=True, cwd=project, env=env)
    assert result.returncode == 0, result.stderr
    if not result.stdout.strip():
        return False
    payload = json.loads(result.stdout)
    return payload.get('hookSpecificOutput', {}).get('permissionDecision') == 'deny'


@pytest.mark.parametrize('prefix', [
    "cat <<'END-TAG'\nnotes\nEND-TAG\n",
    'echo "<<EOF"\n',
    'printf "%s" "literal ; | <<EOF"\n',
    "cat <<'two words'\nnotes\ntwo words\n",
    'cat <<A <<"B-2"\nfirst\nA\nsecond\nB-2\n',
])
@pytest.mark.parametrize('hook, suffix', [
    ('block_seal_commands.sh', 'bash tools/release_cut.sh'),
    ('block_top_level_release_folder.sh', 'mkdir "Sapote Mamey v9.9.9"'),
    ('block_out_of_bounds_writes.py', f'touch {OUT}/file'),
])
def test_real_command_after_each_heredoc_shape_is_checked(prefix, hook, suffix, tmp_path):
    assert decision(hook, prefix+suffix, tmp_path)


@pytest.mark.parametrize('body', [
    'cat <<A <<B\nnotes\nA\nbash tools/release_cut.sh\nB\necho done',
    'cat <<-EOF\n EOF\nbash tools/release_cut.sh\n\tEOF\necho done',
    "cat <<'END-TAG'\nbash tools/release_cut.sh\nEND-TAG\necho done",
])
def test_literal_heredoc_bodies_do_not_become_commands(body, tmp_path):
    assert not decision('block_seal_commands.sh', body, tmp_path)


def test_pipeline_stages_are_not_exempted_with_the_text_stage(tmp_path):
    candidate = tmp_path/'candidate_cut_fixture'
    candidate.mkdir()
    assert decision('block_top_level_release_folder.sh', 'printf x | mkdir "Sapote Mamey v9.9.9"', tmp_path)
    assert decision('full_suite_before_package.sh', 'printf x | zip -r fixture.zip candidate_cut_fixture', tmp_path)
    assert not decision('full_suite_before_package.sh', 'printf "%s" "zip candidate_cut_fixture" > notes', tmp_path)


@pytest.mark.parametrize('command', [
    f'(cd {OUT} && touch a.txt)',
    f'OUT={OUT}; cd "$OUT" && touch a.txt',
    f'OUT={OUT}; cd "${{OUT}}" && touch a.txt',
    f'cd {OUT}; pushd "{{project}}"; popd; touch a.txt',
    f'cp --target-directory {OUT} ./local.txt',
    'cd - && touch a.txt',
    'cd "$SAPOTE_UNBOUND_FIXTURE" && touch a.txt',
    f'cd {OUT} || echo fallback; touch a.txt',
    f'cd {OUT} || pushd "{{project}}"; popd; touch a.txt',
    f'cd {OUT} || DIR=sub; cd "$DIR"; touch a.txt',
])
def test_outside_or_unbound_directory_writes_are_denied(command, tmp_path):
    command = command.replace('{project}', str(tmp_path))
    assert decision('block_out_of_bounds_writes.py', command, tmp_path, {'OLDPWD': OUT})


@pytest.mark.parametrize('command', [
    '(cd sub && touch a.txt); touch parent.txt',
    'DIR=sub; cd "$DIR" && touch a.txt',
    'pushd sub; popd; touch parent.txt',
    'cd sub; cd -; touch parent.txt',
    'cd sub || echo fallback; touch either.txt',
    'cp --target-directory sub ./local.txt',
    f'cd {OUT} || touch fallback.txt',
    f'cd {OUT} | cat; touch parent.txt',
    'echo "literal | ; > /opt/path" > notes.txt',
    "touch 'literal$NAME.txt'",
    'cd "$SAPOTE_UNBOUND_FIXTURE" && ls',
])
def test_legitimate_commands_stay_allowed(command, tmp_path):
    (tmp_path/'sub').mkdir()
    assert not decision('block_out_of_bounds_writes.py', command, tmp_path)


@pytest.mark.parametrize("command", ["cd nonexistent; touch ../outside", "cd nonexistent && echo ready; touch ../outside"])
def test_failed_directory_change_retains_original_directory(command):
    import importlib.util
    spec = importlib.util.spec_from_file_location("audit_write_guard", ROOT/"hooks"/"block_out_of_bounds_writes.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    targets = module.bash_write_targets(command, cwd="/opt/sapote_virtual_project")
    assert "/opt/outside" in [os.path.realpath(path) for path in targets]


@pytest.mark.parametrize('command', [
    f'cd {OUT} && touch "$PWD/a.txt"',
    f'cd {OUT}; pushd "{{project}}"; popd; touch "$PWD/a.txt"',
    f'cd {OUT}; cd "$SAPOTE_UNBOUND_FIXTURE" && touch "$PWD/a.txt"',
    f'OLDPWD={OUT}; cd - && touch "$PWD/a.txt"',
    f'export OLDPWD={OUT}; cd - && touch a.txt',
    f'CDPATH={OUT}; cd sub && touch a.txt',
    f'export CDPATH={OUT}; cd sub && touch a.txt',
    f'CDPATH={OUT} cd sub && touch a.txt',
    f'HOME={OUT}; touch ~/.claude/a.txt',
    f'export HOME={OUT}; touch ~/.claude/a.txt',
    f'export DEST={OUT}; touch "$DEST/a.txt"',
    f'readonly DEST={OUT}; DEST="{{project}}"; touch "$DEST/a.txt"',
    f'declare -x DEST={OUT}; touch "$DEST/a.txt"',
    f'typeset DEST={OUT}; touch "$DEST/a.txt"',
    f'export DEST={OUT}; unset DEST; touch "$DEST/a.txt"',
    f'export TARGET={OUT}; declare -n DEST=TARGET; touch "$DEST/a.txt"',
    f'CDPATH="$SAPOTE_UNBOUND_FIXTURE"; cd sub && touch a.txt',
])
def test_directory_and_variable_followup_denies_outside_or_unresolved_writes(command, tmp_path):
    (tmp_path/'sub').mkdir()
    assert decision('block_out_of_bounds_writes.py', command.replace('{project}', str(tmp_path)), tmp_path,
                    {'PWD': str(tmp_path), 'OLDPWD': str(tmp_path), 'DEST': str(tmp_path)})


@pytest.mark.parametrize('command', [
    f'cd {OUT} && touch "$OLDPWD/local.txt"',
    f'(cd {OUT} && ls); touch "$PWD/local.txt"',
    'pushd sub; popd; touch "$PWD/local.txt"',
    'cd sub; touch "$OLDPWD/local.txt"',
    'cd sub || echo fallback; touch local.txt',
    "mkdir '~'",
    r'mkdir \~',
    'mkdir "~"',
    "DEST='~'; mkdir \"$DEST\"",
    'HOME="{project}"; touch ~/local.txt',
    'export HOME="{project}"; touch ~/local.txt',
    'export DEST="{project}"; touch "$DEST/local.txt"',
    'readonly DEST="{project}"; touch "$DEST/local.txt"',
    'declare -x DEST="{project}"; touch "$DEST/local.txt"',
    'typeset DEST="{project}"; touch "$DEST/local.txt"',
    'CDPATH="{project}"; cd sub && touch local.txt',
    f'CDPATH={OUT}; cd ./sub && touch local.txt',
    f'CDPATH={OUT}; unset CDPATH; cd sub && touch local.txt',
    f'(export DEST={OUT}); touch "$DEST/local.txt"',
])
def test_directory_and_variable_followup_preserves_legitimate_controls(command, tmp_path):
    (tmp_path/'sub').mkdir()
    assert not decision('block_out_of_bounds_writes.py', command.replace('{project}', str(tmp_path)), tmp_path,
                        {'PWD': str(tmp_path), 'OLDPWD': str(tmp_path), 'DEST': str(tmp_path)})


def test_payload_cwd_replaces_inherited_hook_pwd(tmp_path):
    assert not decision('block_out_of_bounds_writes.py', 'touch "$PWD/local.txt"', tmp_path,
                        {'PWD': OUT})


def test_inherited_cdpath_is_considered(tmp_path):
    (tmp_path/'sub').mkdir()
    assert decision('block_out_of_bounds_writes.py', 'cd sub && touch local.txt', tmp_path,
                    {'CDPATH': OUT, 'PWD': str(tmp_path)})


def test_ambiguous_conditional_pwd_is_held_instead_of_guessed(tmp_path):
    (tmp_path/'sub').mkdir()
    assert decision('block_out_of_bounds_writes.py', 'cd sub || echo fallback; touch "$PWD/local.txt"',
                    tmp_path, {'PWD': str(tmp_path)})


@pytest.mark.parametrize('command, deny', [
    (f'HOME={OUT}; CDPATH=.:~; cd sub && touch local.txt', True),
    ('HOME="{project}"; CDPATH=.:~; cd sub && touch local.txt', False),
    (f'DEST="{{project}}/one {OUT}/two"; touch $DEST', True),
    ('DEST="{project}/literal name"; touch "$DEST"', False),
    ('DEST="{project}/*"; touch $DEST', True),
    ('CDPATH="{project}"; (unset CDPATH); cd sub && touch local.txt', False),
])
def test_scalar_assignment_expansion_edges_are_bound_or_held(command, deny, tmp_path):
    (tmp_path/'sub').mkdir()
    assert decision('block_out_of_bounds_writes.py', command.replace('{project}', str(tmp_path)), tmp_path,
                    {'PWD': str(tmp_path)}) is deny
