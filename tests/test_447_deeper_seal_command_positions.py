"""Command-position guards: only hook JSON executes; payload shell text is never run."""
import json
import os
from pathlib import Path
import shlex
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]


def deny(hook, command, project):
    env = {**os.environ, 'SAPOTE_WORKSPACE_ROOT':str(project), 'CLAUDE_PROJECT_DIR':str(project)}
    result = subprocess.run(['bash', str(ROOT/'hooks'/hook)], input=json.dumps(
        {'tool_name':'Bash','tool_input':{'command':command},'cwd':str(project)}),
        capture_output=True,text=True,cwd=project,env=env)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout) if result.stdout.strip() else {}
    return output.get('hookSpecificOutput',{}).get('permissionDecision') == 'deny'


@pytest.mark.parametrize('command', [
    'bash "tools/release_cut.sh"',
    '"bash" "tools/release_cut.sh"',
    "bash 'tools/make_public_tier.sh'",
    'bash -- "tools/release_cut.sh"',
    '"./tools/release_cut.sh"',
    "./tools/'release_cut.sh'",
    'source "tools/release_cut.sh"',
    '. -- "tools/release_cut.sh"',
    'source -- "tools/release_cut.sh"',
    'FLAG=1 command bash "tools/release_cut.sh"',
    'env FLAG=1 bash "tools/release_cut.sh"',
    'sudo -u nobody -- bash "tools/release_cut.sh"',
    'nice -n 5 nohup bash "tools/release_cut.sh"',
    'exec -a harmless "tools/release_cut.sh"',
    'bash -c \'bash "tools/release_cut.sh"\'',
    'bash -lc \'"./tools/release_cut.sh"\'',
    'eval \'bash "tools/release_cut.sh"\'',
    'eval bash tools/release_cut.sh',
    'if true; then "bash" "tools/release_cut.sh"; fi',
    'echo notes > notes.txt; bash "tools/release_cut.sh"',
])
def test_seal_paths_at_execution_positions_are_denied(command,tmp_path):
    assert deny('block_seal_commands.sh',command,tmp_path)


@pytest.mark.parametrize('command', [
    'printf "%s" "bash tools/release_cut.sh"',
    '"printf" "%s" "bash tools/release_cut.sh"',
    'printf "%s" "bash tools/release_cut.sh" > notes.txt',
    'echo "source tools/release_cut.sh"',
    'grep -n "bash tools/release_cut.sh" README.md',
    'ls "tools/release_cut.sh"',
    'cat "tools/release_cut.sh"',
    'python3 -c \'print("bash tools/release_cut.sh")\'',
    'bash -c \'printf "%s" "bash tools/release_cut.sh"\'',
    'eval \'printf "%s" "bash tools/release_cut.sh"\'',
    'command -v tools/release_cut.sh',
    'bash --help tools/release_cut.sh',
    'bash --version tools/release_cut.sh',
    'exec -a release_cut.sh printf harmless',
    'sudo -u release_cut.sh printf harmless',
    'env ROLE=release_cut.sh printf harmless',
])
def test_seal_mentions_remain_readable(command,tmp_path):
    assert not deny('block_seal_commands.sh',command,tmp_path)


@pytest.mark.parametrize('command', [
    '"mkdir" "Sapote Mamey v9.9.9"',
    'env FLAG=1 mkdir "Sapote Mamey v9.9.9"',
    'sudo -n mkdir "Sapote Mamey v9.9.9"',
    'bash -c \'mkdir "Sapote Mamey v9.9.9"\'',
    'eval \'mkdir "Sapote Mamey v9.9.9"\'',
    'printf x | "mkdir" "Sapote Mamey v9.9.9"',
    'cat > notes.txt <<EOF\nmkdir "Sapote Mamey v9.9.9"\nEOF\nmkdir "Sapote Mamey v9.9.9"',
])
def test_actual_release_folder_creation_is_denied(command,tmp_path):
    assert deny('block_top_level_release_folder.sh',command,tmp_path)


@pytest.mark.parametrize('command', [
    'printf "%s" \'mkdir "Sapote Mamey v9.9.9"\'',
    '"printf" "%s" \'mkdir "Sapote Mamey v9.9.9"\'',
    'grep -n \'mkdir "Sapote Mamey v9.9.9"\' README.md',
    'bash -c \'printf "%s" "mkdir Sapote Mamey v9.9.9"\'',
    'eval \'printf "%s" "mkdir Sapote Mamey v9.9.9"\'',
    'mkdir "candidate_cut_fixture/Sapote Mamey v9.9.9"',
    'mkdir "Patches for next cut Sapote Mamey (v9.9.9)/Sapote Mamey v9.9.9"',
    'cp "Sapote Mamey v9.9.9/input.txt" "candidate_cut_fixture/copied.txt"',
])
def test_release_folder_mentions_and_candidate_routes_are_allowed(command,tmp_path):
    sealed = tmp_path/'Sapote Mamey v9.9.9'; sealed.mkdir()
    (sealed/'input.txt').write_text('fixture')
    # A new release directory does not exist; only the explicit read-source fixture does.
    if command.startswith('cp '):
        assert not deny('block_top_level_release_folder.sh',command,tmp_path)
    else:
        assert not deny('block_top_level_release_folder.sh',command.replace('v9.9.9','v9.9.8'),tmp_path)


@pytest.mark.parametrize('command', [
    '"zip" -r fixture.zip candidate_cut_fixture',
    'env FLAG=1 zip -r fixture.zip candidate_cut_fixture',
    'command zip -r fixture.zip candidate_cut_fixture',
    'nice -n 5 zip -r fixture.zip candidate_cut_fixture',
    'sudo -n zip -r fixture.zip candidate_cut_fixture',
    'bash -c \'zip -r fixture.zip candidate_cut_fixture\'',
    'eval \'zip -r fixture.zip candidate_cut_fixture\'',
    'tar -cf fixture.tar candidate_cut_fixture',
    '"tar" cf fixture.tar candidate_cut_fixture',
    'tar -xf candidate_cut_fixture.zip; zip -r fixture.zip candidate_cut_fixture',
    'zip -r fixture.zip candidate_cut_fixture; tar -xf candidate_cut_fixture.zip',
    'printf x | zip -r fixture.zip candidate_cut_fixture',
    'cat > notes.txt <<EOF\nzip -r fixture.zip candidate_cut_fixture\nEOF\nzip -r fixture.zip candidate_cut_fixture',
])
def test_actual_package_creation_needs_marker(command,tmp_path):
    (tmp_path/'candidate_cut_fixture').mkdir()
    assert deny('full_suite_before_package.sh',command,tmp_path)


@pytest.mark.parametrize('command', [
    'printf "%s" "zip -r fixture.zip candidate_cut_fixture"',
    '"printf" "%s" "zip -r fixture.zip candidate_cut_fixture"',
    'grep -n "zip -r fixture.zip candidate_cut_fixture" README.md',
    'bash -c \'printf "%s" "zip -r fixture.zip candidate_cut_fixture"\'',
    'eval \'printf "%s" "zip -r fixture.zip candidate_cut_fixture"\'',
    'tar -xf candidate_cut_fixture.zip',
    'tar xf candidate_cut_fixture.zip',
    'tar -tf candidate_cut_fixture.tar',
    'tar --list --file candidate_cut_fixture.tar',
    'unzip candidate_cut_fixture.zip',
    'ditto -x -k candidate_cut_fixture.zip output',
])
def test_package_mentions_and_extraction_stages_are_allowed(command,tmp_path):
    (tmp_path/'candidate_cut_fixture').mkdir()
    assert not deny('full_suite_before_package.sh',command,tmp_path)


def fixture_suite_receipt(candidate):
    # Synthetic verifier fixture; never evidence of a real candidate suite.
    import importlib.util
    import shutil
    tool = ROOT/'tools/full_suite_receipt.py'
    (candidate/'tools').mkdir(exist_ok=True)
    shutil.copy2(tool, candidate/'tools/full_suite_receipt.py')
    spec = importlib.util.spec_from_file_location('fixture_receipt', tool)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    (candidate/'_CANDIDATE_NOTES/.fullsuite.log').write_text('synthetic receipt fixture')
    fingerprint = module.tree_hash(candidate)
    marker = {'schema':module.SCHEMA,'command':['python3',*module.COMMAND_TAIL],
              'cwd':str(candidate.resolve()),'exit_code':0,'tree_before':fingerprint,
              'tree_after':fingerprint,'log_sha256':module.sha((candidate/module.LOG).read_bytes()),
              'pytest_addopts':'','pytest_plugins':'', 'python_dont_write_bytecode':'1', 'pythonpath':'.'}
    (candidate/module.MARKER).write_text(json.dumps(marker))


def test_bound_fixture_receipt_still_allows_quoted_package_command(tmp_path):
    candidate=tmp_path/'candidate_cut_fixture'; candidate.mkdir()
    notes=candidate/'_CANDIDATE_NOTES'; notes.mkdir()
    fixture_suite_receipt(candidate)
    assert not deny('full_suite_before_package.sh','"zip" -r fixture.zip candidate_cut_fixture',tmp_path)


def test_green_candidate_does_not_exempt_second_unmarked_package(tmp_path):
    green=tmp_path/'candidate_cut_green'; green.mkdir()
    notes=green/'_CANDIDATE_NOTES'; notes.mkdir()
    fixture_suite_receipt(green)
    (tmp_path/'candidate_cut_held').mkdir()
    assert deny('full_suite_before_package.sh','zip -r green.zip candidate_cut_green; zip -r held.zip candidate_cut_held',tmp_path)


@pytest.mark.parametrize('hook,forbidden', [
    ('block_seal_commands.sh','bash "tools/release_cut.sh"'),
    ('block_top_level_release_folder.sh','mkdir "Sapote Mamey v9.9.9"'),
    ('full_suite_before_package.sh','zip -r fixture.zip candidate_cut_fixture'),
])
@pytest.mark.parametrize('heredoc', [
    "cat <<'END-TAG'\n{forbidden}\nEND-TAG\nprintf done",
    'cat <<A <<"B-2"\nfirst\nA\n{forbidden}\nB-2\nprintf done',
    'cat <<-EOF\n EOF\n{forbidden}\n\tEOF\nprintf done',
])
def test_actual_heredoc_bodies_remain_data(hook,forbidden,heredoc,tmp_path):
    (tmp_path/'candidate_cut_fixture').mkdir()
    assert not deny(hook,heredoc.format(forbidden=forbidden),tmp_path)


@pytest.mark.parametrize('hook,forbidden', [
    ('block_seal_commands.sh','bash "tools/release_cut.sh"'),
    ('block_top_level_release_folder.sh','mkdir "Sapote Mamey v9.9.9"'),
    ('full_suite_before_package.sh','zip -r fixture.zip candidate_cut_fixture'),
])
def test_nested_literal_execution_is_inspected_and_has_finite_depth(hook,forbidden,tmp_path):
    (tmp_path/'candidate_cut_fixture').mkdir()
    nested=forbidden
    for _ in range(3): nested='bash -c '+shlex.quote(nested)
    assert deny(hook,nested,tmp_path)
    nested='printf harmless'
    for _ in range(7): nested='bash -c '+shlex.quote(nested)
    assert deny(hook,nested,tmp_path)
    assert deny(hook,'bash -c "$UNBOUND_CODE"',tmp_path)
