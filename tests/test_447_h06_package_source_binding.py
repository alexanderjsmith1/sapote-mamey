"""H06 decision tests only: archive payload strings are never executed."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(os.environ.get('SAPOTE_H06_TEST_ROOT', Path(__file__).resolve().parents[1]))
HOOK = ROOT/'hooks/full_suite_before_package.sh'


def decision(workspace, command, cwd=None):
    env={**os.environ,'SAPOTE_WORKSPACE_ROOT':str(workspace),'CLAUDE_PROJECT_DIR':str(workspace),
         'PYTHONDONTWRITEBYTECODE':'1'}
    env.pop('ZIPOPT',None);env.pop('TAR_OPTIONS',None)
    result=subprocess.run(['bash',str(HOOK)],input=json.dumps({'tool_name':'Bash',
        'tool_input':{'command':command},'cwd':str(cwd or workspace)}),
        cwd=workspace,env=env,text=True,capture_output=True)
    assert result.returncode==0,result.stderr
    return json.loads(result.stdout) if result.stdout.strip() else {}


def held(workspace,command,cwd=None):
    return decision(workspace,command,cwd).get('hookSpecificOutput',{}).get('permissionDecision')=='deny'


def candidate(path,green=False):
    path.mkdir(parents=True)
    if green:
        (path/'tools').mkdir();shutil.copy2(ROOT/'tools/full_suite_receipt.py',path/'tools/full_suite_receipt.py')
        spec=importlib.util.spec_from_file_location('h06_fixture_receipt',ROOT/'tools/full_suite_receipt.py')
        receipt=importlib.util.module_from_spec(spec);spec.loader.exec_module(receipt)
        (path/'_CANDIDATE_NOTES').mkdir();(path/receipt.LOG).write_bytes(b'synthetic verifier fixture; no actual suite claim\n')
        digest=receipt.tree_hash(path)
        (path/receipt.MARKER).write_text(json.dumps({'schema':receipt.SCHEMA,
            'command':[sys.executable,*receipt.COMMAND_TAIL],'cwd':str(path.resolve()),'exit_code':0,
            'tree_before':digest,'tree_after':digest,'log_sha256':receipt.sha((path/receipt.LOG).read_bytes()),
            'pytest_addopts':'','pytest_plugins':'', 'python_dont_write_bytecode':'1', 'pythonpath':'.'}))
    return path


@pytest.mark.parametrize('command',[
    'zip -r out.zip .','tar -cf out.tar .','tar cf out.tar .','tar -chf out.tar .',
    'ditto -c -k --keepParent . out.zip',
])
def test_dot_sources_bind_tool_cwd(tmp_path,command):
    c=candidate(tmp_path/'candidate_cut_held')
    assert held(tmp_path,command,c)


@pytest.mark.parametrize('command',[
    'cd "{c}" && zip -r out.zip .',
    '(cd "{c}"; zip -r out.zip .)',
    'pushd "{c}"; zip -r out.zip .; popd',
    'C="{c}"; cd "$C"; zip -r out.zip .',
    'if test -d "{c}"; then cd "{c}"; fi; zip -r out.zip .',
    'pack() {{ cd "{c}"; zip -r out.zip .; }}; pack',
    'env -C "{c}" zip -r out.zip .',
    'sudo -D "{c}" zip -r out.zip .',
    'bash -c \'cd "{c}"; zip -r out.zip .\'',
    'eval \'cd "{c}"; zip -r out.zip .\'',
])
def test_shared_cwd_scopes_gate_actual_sources(tmp_path,command):
    c=candidate(tmp_path/'candidate_cut_held')
    assert held(tmp_path,command.format(c=c))


@pytest.mark.parametrize('command',[
    'tar -cf out.tar -C "{c}" .',
    'tar cf out.tar -C"{c}" .',
    'tar --create --file=out.tar --directory="{c}" .',
    'ditto -ck "{c}" out.zip',
])
def test_archiver_specific_source_operands(tmp_path,command):
    c=candidate(tmp_path/'candidate_cut_held')
    assert held(tmp_path,command.format(c=c))


def test_exact_path_beats_duplicate_green_basename(tmp_path):
    candidate(tmp_path/'one'/'candidate_cut_same',green=True)
    other=candidate(tmp_path/'two'/'candidate_cut_same')
    assert held(tmp_path,f'zip -r out.zip "{other}"')


def test_existing_sources_outside_lookup_root_and_depth_are_bound(tmp_path):
    workspace=tmp_path/'workspace';workspace.mkdir()
    c=candidate(tmp_path/'outside'/'candidate_cut_external')
    assert held(workspace,f'zip -r out.zip "{c}"')
    d=candidate(workspace/'a'/'b'/'c'/'candidate_cut_deep')
    assert held(workspace,f'zip -r out.zip "{d}"')


def test_parent_directory_and_symlink_sources_find_candidates(tmp_path):
    parent=tmp_path/'collection';c=candidate(parent/'candidate_cut_held')
    assert held(tmp_path,f'zip -r out.zip "{parent}"')
    alias=tmp_path/'alias';alias.symlink_to(c,target_is_directory=True)
    assert held(tmp_path,'zip -r out.zip alias')


def test_missing_source_is_not_silently_allowed(tmp_path):
    assert held(tmp_path,'zip -r out.zip candidate_cut_missing')


@pytest.mark.parametrize('command',[
    'zip -r candidate_cut_output.zip ordinary',
    'tar -cf candidate_cut_output.tar ordinary',
    'ditto -ck ordinary candidate_cut_output.zip',
    'ditto ordinary copy',
    'tar -xf candidate_cut_missing.zip',
    'tar -tf candidate_cut_missing.tar',
    'tar --list --file candidate_cut_missing.tar',
    'ditto -xk candidate_cut_missing.zip destination',
    'zip --version',
    'printf "%s" "zip -r out.zip candidate_cut_missing"',
    'cat <<EOF\nzip -r out.zip candidate_cut_missing\nEOF\n',
    'pack() { zip out.zip candidate_cut_missing; }; printf done',
    'zip() { printf done; }; zip candidate_cut_missing',
])
def test_non_candidate_and_non_creation_controls(tmp_path,command):
    (tmp_path/'ordinary').mkdir()
    assert not held(tmp_path,command)


def test_matching_green_canonical_source_passes(tmp_path):
    c=candidate(tmp_path/'candidate_cut_green',green=True)
    assert not held(tmp_path,f'zip -r out.zip "{c}"')
    assert not held(tmp_path,'zip -r ../out.zip .',c)


@pytest.mark.parametrize('command',[
    'tar -cf out.tar -T list.txt',
    'tar --create --file out.tar --files-from=-',
    'zip -r out.zip -@',
    'zip -r out.zip *',
    'source unknown.sh; zip -r out.zip .',
])
def test_unsupported_indirection_is_an_explicit_hold(tmp_path,command):
    (tmp_path/'list.txt').write_text('ordinary\n')
    out=decision(tmp_path,command)
    assert out['hookSpecificOutput']['permissionDecision']=='deny'
    assert 'Cannot bind packaging sources safely' in out['hookSpecificOutput']['permissionDecisionReason']


def test_child_shell_does_not_treat_parent_scalar_as_exported(tmp_path):
    c=candidate(tmp_path/'candidate_cut_held');(tmp_path/'ordinary').mkdir()
    # Child may lack C; failed cd leaves its actual cwd at the held candidate.
    assert held(tmp_path,f'C="{tmp_path/"ordinary"}"; bash -c \'cd "$C"; zip -r out.zip .\'',c)


@pytest.mark.parametrize('command',[
    'TAR_OPTIONS="-C {c}" tar -cf out.tar .',
    'env TAR_OPTIONS="-C {c}" tar -cf out.tar .',
    'ZIPOPT="-@" zip out.zip ordinary',
])
def test_archive_environment_overrides_do_not_silently_rebind_sources(tmp_path,command):
    c=candidate(tmp_path/'candidate_cut_held');ordinary=tmp_path/'ordinary';ordinary.mkdir()
    assert held(tmp_path,command.format(c=c),ordinary)


def test_explicit_child_environment_binding_is_supported(tmp_path):
    c=candidate(tmp_path/'candidate_cut_held')
    assert held(tmp_path,f'env C="{c}" bash -c \'cd "$C"; zip -r out.zip .\'')
    (tmp_path/'ordinary').mkdir()
    assert not held(tmp_path,f'env C="{tmp_path/"ordinary"}" bash -c \'cd "$C" && zip -r ../out.zip .\'')


def test_cleared_child_environment_cannot_reuse_host_oldpwd(tmp_path,monkeypatch):
    c=candidate(tmp_path/'candidate_cut_held');ordinary=tmp_path/'ordinary';ordinary.mkdir()
    monkeypatch.setenv('OLDPWD',str(ordinary))
    assert held(tmp_path,'env -i bash -c \'cd -; zip -r out.zip .\'',c)


@pytest.mark.parametrize('command',[
    'case x in x) printf done;; esac',
    'case x in x) printf "%s" "zip -r out.zip candidate_cut_missing";; esac',
])
def test_unsupported_read_only_grammar_cannot_become_false_packaging_hold(tmp_path,command):
    assert not held(tmp_path,command)


def test_unsupported_grammar_with_actual_packaging_is_held(tmp_path):
    c=candidate(tmp_path/'candidate_cut_held')
    assert held(tmp_path,f'case x in x) zip -r out.zip "{c}";; esac')


@pytest.mark.parametrize('prefix',[
    'printf changed > "{c}/README.md"',
    'rm "{c}/README.md"',
    'cp replacement.txt "{c}/README.md"',
    'dd if=replacement.txt of="{c}/README.md"',
    'mutate() {{ printf changed > "{c}/README.md"; }}; mutate',
    'touch "{c}/README.md"',
])
def test_prior_recognized_mutations_invalidate_combined_packaging_request(tmp_path,prefix):
    c=candidate(tmp_path/'candidate_cut_green',green=True)
    (tmp_path/'replacement.txt').write_text('fixture replacement')
    out=decision(tmp_path,prefix.format(c=c)+f'; zip -r out.zip "{c}"')
    assert out['hookSpecificOutput']['permissionDecision']=='deny'
    assert 'earlier in this request' in out['hookSpecificOutput']['permissionDecisionReason']


def test_prior_namespace_mutation_cannot_reuse_old_symlink_target(tmp_path):
    c=candidate(tmp_path/'candidate_cut_held');ordinary=tmp_path/'ordinary';ordinary.mkdir()
    alias=tmp_path/'alias';alias.symlink_to(ordinary,target_is_directory=True)
    assert held(tmp_path,f'ln -sf "{c}" alias; zip -r out.zip alias')


def test_unrelated_notes_and_later_mutations_do_not_stale_prior_packaging(tmp_path):
    c=candidate(tmp_path/'candidate_cut_green',green=True)
    assert not held(tmp_path,f'printf note > notes.txt; zip -r out.zip "{c}"')
    assert not held(tmp_path,f'zip -r out.zip "{c}"; printf later > "{c}/README.md"')


def test_parent_source_symlink_to_candidate_file_binds_ancestor(tmp_path):
    c=candidate(tmp_path/'outside'/'candidate_cut_held')
    (c/'README.md').write_text('synthetic fixture')
    parent=tmp_path/'ordinary';parent.mkdir()
    (parent/'reference.txt').symlink_to(c/'README.md')
    assert held(tmp_path,'zip -r out.zip ordinary')


def test_prior_mutation_of_candidate_reached_only_through_nested_symlink(tmp_path):
    c=candidate(tmp_path/'outside'/'candidate_cut_green',green=True)
    parent=tmp_path/'ordinary';parent.mkdir()
    (parent/'reference').symlink_to(c,target_is_directory=True)
    assert held(tmp_path,f'printf changed > "{c}/README.md"; zip -r out.zip ordinary')


@pytest.mark.parametrize('flag',['-T','-rT','--test'])
def test_zip_test_option_with_sources_still_creates_archive(tmp_path,flag):
    c=candidate(tmp_path/'candidate_cut_held')
    assert held(tmp_path,f'zip {flag} out.zip "{c}"')


def test_tar_read_control_preserves_ambient_option_compatibility(tmp_path,monkeypatch):
    monkeypatch.setenv('TAR_OPTIONS','--gzip')
    # decision() clears ambient archiver options, so use a literal prefix assignment.
    assert not held(tmp_path,'TAR_OPTIONS="--gzip" tar -tf existing.tar')


@pytest.mark.parametrize('creator',[
    'zip -r "{c}/earlier.zip" ordinary',
    'zip -r "{c}/earlier" ordinary',
    'tar -cf "{c}/earlier.tar" ordinary',
    'tar --create --file="{c}/earlier.tar" ordinary',
    'ditto -ck ordinary "{c}/earlier.zip"',
])
def test_prior_archive_output_changes_later_candidate_receipt(tmp_path,creator):
    c=candidate(tmp_path/'candidate_cut_green',green=True)
    (tmp_path/'ordinary').mkdir()
    out=decision(tmp_path,creator.format(c=c)+f'; zip -r final.zip "{c}"')
    assert out['hookSpecificOutput']['permissionDecision']=='deny'
    assert 'earlier in this request' in out['hookSpecificOutput']['permissionDecisionReason']


@pytest.mark.parametrize('file_alias',[False,True])
def test_archive_output_aliases_cannot_hide_later_candidate_mutation(tmp_path,file_alias):
    c=candidate(tmp_path/'candidate_cut_green',green=True)
    (tmp_path/'ordinary').mkdir()
    alias=tmp_path/'output_alias'
    if file_alias:
        alias=tmp_path/'output_alias.zip'
        alias.symlink_to(c/'tools'/'full_suite_receipt.py')
        output='output_alias.zip'
    else:
        alias.symlink_to(c,target_is_directory=True)
        output='output_alias/earlier.zip'
    out=decision(tmp_path,f'zip -r "{output}" ordinary; zip -r final.zip "{c}"')
    assert out['hookSpecificOutput']['permissionDecision']=='deny'


@pytest.mark.parametrize('command',[
    'zip -r "{c}/self.zip" "{c}"',
    'tar -cf "{c}/self.tar" "{c}"',
    'ditto -ck "{c}" "{c}/self.zip"',
])
def test_output_inside_current_packaged_source_is_explicit_hold(tmp_path,command):
    c=candidate(tmp_path/'candidate_cut_green',green=True)
    out=decision(tmp_path,command.format(c=c))
    assert out['hookSpecificOutput']['permissionDecision']=='deny'
    assert 'archive output intersects' in out['hookSpecificOutput']['permissionDecisionReason']


def test_ordinary_archive_output_outside_source_preserves_current_and_later_controls(tmp_path):
    c=candidate(tmp_path/'candidate_cut_green',green=True)
    ordinary=tmp_path/'ordinary';ordinary.mkdir()
    assert not held(tmp_path,f'zip -r earlier.zip ordinary; zip -r final.zip "{c}"')
    # A later output inside an already-packaged candidate cannot change that earlier archive.
    assert not held(tmp_path,f'zip -r final.zip "{c}"; zip -r "{c}/later.zip" ordinary')
    assert not held(tmp_path,f'zip -r "{c}/unrelated.zip" ordinary')
    assert not held(tmp_path,f'tar -cf - "{c}"')


def test_archive_output_symlink_inside_current_candidate_is_held(tmp_path):
    c=candidate(tmp_path/'candidate_cut_green',green=True)
    (tmp_path/'outside.zip').symlink_to(c/'new.zip')
    out=decision(tmp_path,f'zip -r outside.zip "{c}"')
    assert out['hookSpecificOutput']['permissionDecision']=='deny'
    assert 'archive output intersects' in out['hookSpecificOutput']['permissionDecisionReason']


def test_tar_implicit_output_destination_is_not_guessed(tmp_path):
    (tmp_path/'ordinary').mkdir()
    out=decision(tmp_path,'tar -c ordinary')
    assert out['hookSpecificOutput']['permissionDecision']=='deny'
    assert 'explicit -f/--file' in out['hookSpecificOutput']['permissionDecisionReason']


@pytest.mark.parametrize('operator',['|','&'])
def test_concurrent_candidate_write_cannot_reuse_preflight_receipt(tmp_path,operator):
    c=candidate(tmp_path/'candidate_cut_green',green=True)
    command=f'tar -cf - "{c}" {operator} gzip > "{c}/out.tar.gz"'
    out=decision(tmp_path,command)
    assert out['hookSpecificOutput']['permissionDecision']=='deny'
    assert 'concurrent pipeline/background write' in out['hookSpecificOutput']['permissionDecisionReason']


def test_pipeline_external_output_and_quoted_pipe_sequential_write_controls(tmp_path):
    c=candidate(tmp_path/'candidate_cut_green',green=True)
    assert not held(tmp_path,f'tar -cf - "{c}" | gzip >out.tar.gz')
    assert not held(tmp_path,f'printf "%s" "| &"; zip -r out.zip "{c}"; printf later >"{c}/README.md"')
    assert not held(tmp_path,f'tar -cf - "{c}" | gzip >out.tar.gz; printf later >notes.txt')


def test_command_wide_concurrency_hold_is_explicitly_conservative(tmp_path):
    c=candidate(tmp_path/'candidate_cut_green',green=True)
    assert held(tmp_path,f'printf note | cat; zip -r out.zip "{c}"; printf later >"{c}/README.md"')


def test_literal_nested_shell_pipeline_write_is_concurrent(tmp_path):
    c=candidate(tmp_path/'candidate_cut_green',green=True)
    command=f'bash -c \'tar -cf - "{c}" | gzip >"{c}/out.tar.gz"\''
    out=decision(tmp_path,command)
    assert out['hookSpecificOutput']['permissionDecision']=='deny'
    assert 'concurrent pipeline/background write' in out['hookSpecificOutput']['permissionDecisionReason']


def test_heredoc_body_pipe_is_not_a_concurrent_operator(tmp_path):
    c=candidate(tmp_path/'candidate_cut_green',green=True)
    command=f'cat <<\'TEXT\'\n| &\nTEXT\nzip -r out.zip "{c}"; printf later >"{c}/README.md"'
    assert not held(tmp_path,command)
