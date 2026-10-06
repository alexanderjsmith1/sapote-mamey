"""Synthetic receipt behavior. No release or real candidate suite is run here."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('full_suite_receipt', ROOT/'tools/full_suite_receipt.py')
receipt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(receipt)


def synthetic_receipt(root):
    """Construct verifier fixtures, not evidence of a suite on a real candidate."""
    (root/'_CANDIDATE_NOTES').mkdir(exist_ok=True)
    (root/receipt.LOG).write_bytes(b'synthetic suite fixture\n')
    digest = receipt.tree_hash(root)
    value = {'schema': receipt.SCHEMA, 'command':[sys.executable,*receipt.COMMAND_TAIL],
             'cwd':str(root.resolve()), 'exit_code':0, 'tree_before':digest,
             'tree_after':digest, 'log_sha256':receipt.sha((root/receipt.LOG).read_bytes()),
             'pytest_addopts':'', 'pytest_plugins':'', 'python_dont_write_bytecode':'1', 'pythonpath':'.'}
    (root/receipt.MARKER).write_text(json.dumps(value))
    return value


@pytest.mark.parametrize('path', ['module.py','guard.sh','config.json','README.md','pyproject.toml'])
@pytest.mark.parametrize('change', ['edit','add','delete'])
def test_all_declared_content_changes_invalidate_even_with_restored_mtime(tmp_path,path,change):
    p = tmp_path/path
    if change != 'add': p.write_text('before')
    synthetic_receipt(tmp_path)
    receipt.check(tmp_path)
    if change == 'delete': p.unlink()
    else:
        old = p.stat() if p.exists() else None
        p.write_text('after')
        if old: os.utime(p, ns=(old.st_atime_ns,old.st_mtime_ns))
    with pytest.raises(ValueError,match='bytes changed'):
        receipt.check(tmp_path)


@pytest.mark.parametrize('value', ['', 'green', '[]', '{}'])
def test_legacy_or_malformed_marker_refused(tmp_path,value):
    (tmp_path/'_CANDIDATE_NOTES').mkdir()
    (tmp_path/receipt.MARKER).write_text(value)
    with pytest.raises(ValueError): receipt.check(tmp_path)


@pytest.mark.parametrize('field,value', [
    ('command',['python','-m','pytest','tests/','-q']),
    ('command',['python','-m','pytest','-q','-k','one']),
    ('command',['python','-m','pytest','-q']),
    ('schema','sapote.full-suite-receipt.v1'),
    ('python_dont_write_bytecode','0'), ('pythonpath','external'),
    ('exit_code',1), ('exit_code',False), ('tree_before','changed'),
    ('cwd','/different/tree'), ('log_sha256','changed'),
    ('pytest_addopts','-k one'), ('pytest_plugins','external_plugin'),
])
def test_selected_failed_or_mismatched_receipt_refused(tmp_path,field,value):
    row=synthetic_receipt(tmp_path);row[field]=value
    (tmp_path/receipt.MARKER).write_text(json.dumps(row))
    with pytest.raises(ValueError):receipt.check(tmp_path)


def test_caches_do_not_invalidate_receipt(tmp_path):
    synthetic_receipt(tmp_path)
    (tmp_path/'__pycache__').mkdir();(tmp_path/'__pycache__/module.pyc').write_bytes(b'cache')
    (tmp_path/'.pytest_cache').mkdir();(tmp_path/'.pytest_cache/state').write_text('cache')
    receipt.check(tmp_path)


def test_changed_symlink_target_and_external_link_refused(tmp_path):
    (tmp_path/'a').write_text('a');(tmp_path/'b').write_text('b')
    link=tmp_path/'link';link.symlink_to('a');synthetic_receipt(tmp_path)
    link.unlink();link.symlink_to('b')
    with pytest.raises(ValueError):receipt.check(tmp_path)
    link.unlink();link.symlink_to('/etc')
    with pytest.raises(ValueError,match='external symlink'):receipt.tree_hash(tmp_path)


def test_failed_or_mutating_run_cannot_keep_previous_green(tmp_path,monkeypatch):
    synthetic_receipt(tmp_path)
    monkeypatch.delenv('PYTEST_ADDOPTS',raising=False);monkeypatch.delenv('PYTEST_PLUGINS',raising=False)
    def failed(command,**kwargs):
        assert command[1:]==receipt.COMMAND_TAIL;
        assert kwargs['env']['PYTHONDONTWRITEBYTECODE']=='1';
        assert kwargs['env']['PYTHONPATH']=='.';kwargs['stdout'].write(b'failed\n')
        return subprocess.CompletedProcess(command,1)
    monkeypatch.setattr(receipt.subprocess,'run',failed)
    assert receipt.run(tmp_path)==1
    assert not (tmp_path/receipt.MARKER).exists()
    synthetic_receipt(tmp_path)
    def mutating(command,**kwargs):
        (tmp_path/'modified.sh').write_text('changed');return subprocess.CompletedProcess(command,0)
    monkeypatch.setattr(receipt.subprocess,'run',mutating)
    with pytest.raises(ValueError,match='changed inventoried'):receipt.run(tmp_path)
    assert not (tmp_path/receipt.MARKER).exists()


def test_recorder_runs_configured_directories_and_binds_real_log(tmp_path,monkeypatch):
    """A tiny actual suite checks collection scope; no project jobs are invoked."""
    monkeypatch.delenv('PYTEST_ADDOPTS',raising=False);monkeypatch.delenv('PYTEST_PLUGINS',raising=False)
    synthetic_options(tmp_path)
    (tmp_path/'pyproject.toml').write_text('[tool.pytest.ini_options]\ntestpaths=["tests","tools","deliverable_tools"]\n')
    for directory in ['tests','tools','deliverable_tools']:
        (tmp_path/directory).mkdir();(tmp_path/directory/f'test_{directory}.py').write_text('def test_fixture():\n    assert True\n')
    assert receipt.run(tmp_path)==0
    row=receipt.check(tmp_path)
    assert row['command']==[sys.executable,*receipt.COMMAND_TAIL]
    assert b'3 passed' in (tmp_path/receipt.LOG).read_bytes()


def hook_decision(project,command):
    result=subprocess.run(['bash',str(ROOT/'hooks/full_suite_before_package.sh')],
        input=json.dumps({'tool_name':'Bash','tool_input':{'command':command},'cwd':str(project)}),
        text=True,capture_output=True,cwd=project,
        env={**os.environ,'SAPOTE_WORKSPACE_ROOT':str(project),'CLAUDE_PROJECT_DIR':str(project)})
    assert result.returncode==0,result.stderr
    return json.loads(result.stdout) if result.stdout.strip() else {}


def test_hook_checks_receipt_and_preserves_nonpackaging_controls(tmp_path):
    candidate=tmp_path/'candidate_cut_fixture';(candidate/'tools').mkdir(parents=True)
    shutil.copy2(ROOT/'tools/full_suite_receipt.py',candidate/'tools/full_suite_receipt.py')
    synthetic_receipt(candidate)
    command='zip -r fixture.zip candidate_cut_fixture'
    assert not hook_decision(tmp_path,command)
    (candidate/'changed.sh').write_text('changed')
    output=hook_decision(tmp_path,command)
    assert output['hookSpecificOutput']['permissionDecision']=='deny'
    assert 'configured FULL-suite receipt' in output['hookSpecificOutput']['permissionDecisionReason']
    assert not hook_decision(tmp_path,'printf "%s" "zip candidate_cut_fixture"')



def test_link_to_excluded_content_refused(tmp_path):
    (tmp_path/'__pycache__').mkdir()
    (tmp_path/'__pycache__/fixture.json').write_text('input')
    (tmp_path/'active.json').symlink_to('__pycache__/fixture.json')
    with pytest.raises(ValueError,match='excluded'):receipt.tree_hash(tmp_path)


def test_mode_change_invalidates(tmp_path):
    script=tmp_path/'guard.sh';script.write_text('echo ok');script.chmod(0o755)
    synthetic_receipt(tmp_path);script.chmod(0o644)
    with pytest.raises(ValueError,match='bytes changed'):receipt.check(tmp_path)


def test_directory_walk_error_refuses_certification(tmp_path,monkeypatch):
    def failed_walk(root,**kwargs):
        kwargs['onerror'](PermissionError('synthetic unreadable subtree'))
        yield str(root), [], []
    monkeypatch.setattr(receipt.os,'walk',failed_walk)
    with pytest.raises(PermissionError):receipt.tree_hash(tmp_path)


def test_two_held_candidates_emit_one_valid_denial_object(tmp_path):
    for name in ['candidate_cut_first','candidate_cut_second']:(tmp_path/name).mkdir()
    output=hook_decision(tmp_path,'zip -r fixture.zip candidate_cut_first candidate_cut_second')
    assert output['hookSpecificOutput']['permissionDecision']=='deny'


def synthetic_options(root):
    """Register complete-profile flags for tiny synthetic projects only."""
    (root/'conftest.py').write_text('''import pytest

def pytest_addoption(parser):
    parser.addoption("--run-slow", action="store_true")
    parser.addoption("--run-network", action="store_true")

def pytest_collection_modifyitems(config, items):
    for item in items:
        for marker, option in (("slow", "--run-slow"), ("network", "--run-network")):
            if marker in item.keywords and not config.getoption(option):
                item.add_marker(pytest.mark.skip(reason="synthetic omitted partition"))
''')


def tiny_partition_suite(root, failing_marker=None):
    synthetic_options(root)
    (root/'pyproject.toml').write_text('[tool.pytest.ini_options]\nmarkers=["slow: synthetic", "network: synthetic, no network access"]\n')
    (root/'test_scope.py').write_text('import os\nimport pytest\n\n'
        'def test_fast():\n    assert os.environ["PYTHONDONTWRITEBYTECODE"] == "1"\n'
        '    assert os.environ["PYTHONPATH"] == "."\n\n'
        '@pytest.mark.slow\ndef test_slow():\n    assert '+str(failing_marker != 'slow')+'\n\n'
        '@pytest.mark.network\ndef test_network_marker_only():\n    assert '+str(failing_marker != 'network')+'\n')


@pytest.mark.parametrize('marker', ['slow','network'])
def test_complete_profile_failure_cannot_green_a_default_skipped_partition(tmp_path, monkeypatch, marker):
    monkeypatch.delenv('PYTEST_ADDOPTS',raising=False)
    monkeypatch.delenv('PYTEST_PLUGINS',raising=False)
    tiny_partition_suite(tmp_path, failing_marker=marker)
    assert receipt.run(tmp_path) == 1
    assert not (tmp_path/receipt.MARKER).exists()
    log=(tmp_path/receipt.LOG).read_bytes()
    assert b'1 failed, 2 passed' in log and b' skipped' not in log


def test_canonical_pass_covers_both_partitions_without_caches_or_bytecode(tmp_path, monkeypatch):
    monkeypatch.delenv('PYTEST_ADDOPTS',raising=False)
    monkeypatch.delenv('PYTEST_PLUGINS',raising=False)
    monkeypatch.setenv('PYTHONDONTWRITEBYTECODE','0')
    monkeypatch.setenv('PYTHONPATH','untrusted-parent-path')
    tiny_partition_suite(tmp_path)
    assert receipt.run(tmp_path) == 0
    row=receipt.check(tmp_path)
    assert row['command'] == [sys.executable,*receipt.COMMAND_TAIL]
    assert row['python_dont_write_bytecode'] == '1' and row['pythonpath'] == '.'
    assert b'3 passed' in (tmp_path/receipt.LOG).read_bytes()
    assert not (tmp_path/'.pytest_cache').exists()
    assert not list(tmp_path.rglob('*.pyc'))


@pytest.mark.parametrize('change', ['legacy_schema','default_command'])
def test_hook_refuses_old_candidate_protocol_before_candidate_checker(tmp_path, change):
    candidate=tmp_path/'candidate_cut_legacy';(candidate/'tools').mkdir(parents=True)
    # Synthetic older checker accepts anything and records whether it was invoked.
    # A v1/default-only candidate must be held without trusting this checker.
    (candidate/'tools/full_suite_receipt.py').write_text(
        'from pathlib import Path\nPath(__file__).parents[1].joinpath("checker_called").write_text("called")\n')
    row=synthetic_receipt(candidate)
    if change=='legacy_schema':row['schema']='sapote.full-suite-receipt.v1'
    else:row['command']=[sys.executable,'-m','pytest','-q']
    (candidate/receipt.MARKER).write_text(json.dumps(row))
    out=hook_decision(tmp_path,'zip -r fixture.zip candidate_cut_legacy')
    assert out['hookSpecificOutput']['permissionDecision']=='deny'
    assert 'minimum receipt protocol' in out['hookSpecificOutput']['permissionDecisionReason']
    assert not (candidate/'checker_called').exists()


def test_recorder_profile_matches_both_canonical_cut_entrypoints():
    spec=importlib.util.spec_from_file_location('external_receipt',ROOT/'tools/verify_external_validation_receipt.py')
    external=importlib.util.module_from_spec(spec);spec.loader.exec_module(external)
    assert receipt.COMMAND_TAIL == external.COMMAND_TAIL
    assert 'python3 '+' '.join(receipt.COMMAND_TAIL) in (ROOT/'tools/release_cut.sh').read_text()
