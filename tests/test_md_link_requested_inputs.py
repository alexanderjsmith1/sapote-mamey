"""Requested-path coverage only; unsupported-extension policy is unchanged."""
import importlib.util
import os
from pathlib import Path
import pytest
TARGET=Path(__file__).resolve().parents[1]/'tools/check_md_links.py'
spec=importlib.util.spec_from_file_location('md_links_candidate',TARGET);tool=importlib.util.module_from_spec(spec);spec.loader.exec_module(tool)

@pytest.mark.parametrize('kind',['missing_file','missing_directory','file_as_directory','empty_directory_argument'])
def test_missing_requested_scope_never_reports_clean(tmp_path,capsys,kind):
    valid=tmp_path/'valid.md';valid.write_text('# Software fixture\n')
    args=[str(valid)]
    if kind=='missing_file':args += [str(tmp_path/'missing.md')]
    elif kind=='missing_directory':args += ['--dir',str(tmp_path/'missing')]
    elif kind=='file_as_directory':args += ['--dir',str(valid)]
    else:args += ['--dir','']
    with pytest.raises(SystemExit) as caught:tool.main(args)
    assert caught.value.code==2
    streams=capsys.readouterr();assert 'OK —' not in streams.out
    assert 'requested' in streams.err

def test_unenumerable_requested_tree_refused(tmp_path,monkeypatch,capsys):
    valid=tmp_path/'valid.md';valid.write_text('# Software\n')
    def blocked(path,onerror=None):
        if onerror is not None:onerror(PermissionError('synthetic directory refusal'))
        return iter(())
    monkeypatch.setattr(tool.os,'walk',blocked)
    with pytest.raises(SystemExit) as caught:tool.main([str(valid),'--dir',str(tmp_path)])
    assert caught.value.code==2 and 'OK —' not in capsys.readouterr().out

def test_valid_file_directory_and_broken_link_contracts(tmp_path,capsys):
    valid=tmp_path/'valid.md';valid.write_text('# Software\n')
    assert tool.main([str(valid)])==0
    assert tool.main(['--dir',str(tmp_path)])==0
    valid.write_text('[Missing](definitely_missing_fixture.md)\n')
    assert tool.main([str(valid)])==1

@pytest.mark.parametrize('kind',['missing_only','empty_directory'])
def test_existing_no_markdown_refusal_retained(tmp_path,kind):
    args=[str(tmp_path/'missing.md')] if kind=='missing_only' else ['--dir',str(tmp_path)]
    with pytest.raises(SystemExit) as caught:tool.main(args)
    assert caught.value.code==2

def test_non_markdown_policy_unchanged(tmp_path):
    valid=tmp_path/'valid.md';valid.write_text('# Software\n')
    unsupported=tmp_path/'supplied.txt';unsupported.write_text('[Broken](missing.md)\n')
    assert tool.main([str(valid),str(unsupported)])==0
