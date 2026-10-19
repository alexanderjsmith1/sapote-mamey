"""Root R defaults refuse export without hiding source or intended PDF assets."""
import importlib.util
import os
from pathlib import Path
import shlex
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = Path(os.environ.get('R_DEVICE_TOOLS', str(ROOT/'tools')))


def load(name):
    spec = importlib.util.spec_from_file_location('rdevice_'+name, TOOLS/(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


RESERVED = ['Rplots.pdf','Rplots.ps','Rplots.svg','Rplot001.pdf','Rplot1000.ps',
            'Rplot001.svg','Rplot001.png','Rplot001.jpeg','Rplot001.jpg',
            'Rplot001.tiff','Rplot001.tif','Rplot001.bmp','rplots.PDF']


@pytest.mark.parametrize('name', RESERVED)
def test_source_and_stage_guards_refuse_reserved_root_names_without_removal(tmp_path,name):
    stage=tmp_path/'stage';stage.mkdir()
    target=stage/name;target.write_bytes(b'synthetic default device bytes')
    before=target.read_bytes()
    env=dict(os.environ,PYTHON=sys.executable,STAGE=str(stage))
    source='source '+shlex.quote(str(TOOLS/'cut_preflight.sh'))+'\nsapote_assert_no_review_root "$STAGE"\n'
    result=subprocess.run(['bash','-e','-c',source],env=env,capture_output=True,text=True,timeout=15)
    assert result.returncode!=0, result.stdout+result.stderr
    assert 'root default R device output' in result.stderr
    assert target.read_bytes()==before
    script=(TOOLS/'make_public_tier.sh').read_text()
    function='fail_on_backup_debris() {'+script.split('fail_on_backup_debris() {',1)[1].split('# --- 0.',1)[0]
    result=subprocess.run(['bash','-e','-c','source '+shlex.quote(str(TOOLS/'cut_preflight.sh'))+'\n'+function+'\nfail_on_backup_debris'],env=env,capture_output=True,text=True,timeout=15)
    assert result.returncode!=0, result.stdout+result.stderr
    assert 'root default R device output' in result.stderr
    assert target.read_bytes()==before


@pytest.mark.parametrize('kind',['file','directory','broken_symlink','directory_symlink'])
def test_final_inventory_refuses_reserved_root_entries_without_following(tmp_path,kind,monkeypatch):
    stage=tmp_path/'stage';stage.mkdir();target=stage/'Rplots.pdf'
    if kind=='file': target.write_bytes(b'preserve synthetic file')
    elif kind=='directory':target.mkdir()
    elif kind=='broken_symlink':target.symlink_to(tmp_path/'missing')
    else:
        outside=tmp_path/'outside';outside.mkdir();(outside/'sentinel.txt').write_text('preserve')
        target.symlink_to(outside,target_is_directory=True)
    def forbidden_sha(path):pytest.fail('default device bytes must not be read through admission')
    mod=load('finalize_public_archive');monkeypatch.setattr(mod,'_sha_path',forbidden_sha)
    with pytest.raises(mod.ArchiveTransactionError,match='root_default_r_device_output'):
        mod.inventory_stage(stage)
    assert os.path.lexists(target)
    if kind=='file':assert target.read_bytes()==b'preserve synthetic file'
    if kind=='directory_symlink':assert (tmp_path/'outside/sentinel.txt').read_text()=='preserve'


@pytest.mark.parametrize('rel',['selected_panel.pdf','Rplots_named.pdf','docs/Rplots.pdf','figures/Rplot001.pdf','tests/fixtures/Rplots.pdf','Rplot01.pdf'])
def test_named_and_nested_figure_files_are_governed_and_not_refused(tmp_path,rel):
    policy=load('tracked_file_policy')
    assert policy.is_tracked(rel)
    root=tmp_path/'source';root.mkdir();path=root/rel;path.parent.mkdir(parents=True,exist_ok=True)
    path.write_bytes(b'synthetic admitted figure bytes')
    assert policy.root_default_r_device_outputs(root)==[]
    assert policy.check_default_r_device_outputs(root)==0
    names=[m.name for m in load('finalize_public_archive').inventory_stage(root)]
    assert rel in names


@pytest.mark.parametrize('which',['private','public'])
def test_derivation_refuses_root_default_even_though_pdf_is_outside_text_scope(tmp_path,which,monkeypatch):
    private=tmp_path/'private';public=tmp_path/'public';private.mkdir();public.mkdir()
    for root in (private,public):(root/'README.md').write_text('public fixture')
    target=(private if which=='private' else public)/'Rplots.pdf';target.write_bytes(b'preserve')
    monkeypatch.setattr(sys,'argv',['verify_tier_derivation',str(private),str(public)])
    assert load('verify_tier_derivation').main()==2
    assert target.read_bytes()==b'preserve'


def test_reserved_names_remain_tracked_and_not_derivation_omissions():
    policy=load('tracked_file_policy');derivation=load('verify_tier_derivation')
    for name in RESERVED:
        assert policy.is_tracked(name)
        assert not derivation._is_stripped(name)


def test_read_only_guard_handles_clean_and_invalid_roots(tmp_path):
    policy=load('tracked_file_policy')
    assert policy.check_default_r_device_outputs(tmp_path)==0
    assert policy.check_default_r_device_outputs(tmp_path/'missing')==2
    file=tmp_path/'file';file.write_text('not root')
    assert policy.check_default_r_device_outputs(file)==2


def test_export_finalizer_preflights_debris_before_archive_write(tmp_path,monkeypatch):
    root=tmp_path/'stage';root.mkdir();target=root/'Rplots.pdf';target.write_bytes(b'preserve')
    output=tmp_path/'output';output.mkdir()
    mod=load('finalize_public_archive')
    monkeypatch.setattr(mod,'capability_probe',lambda output:None)
    monkeypatch.setattr(mod,'_write_archive',lambda *args:pytest.fail('dirty stage cannot be archived'))
    with pytest.raises(mod.ArchiveTransactionError,match='root_default_r_device_output'):
        mod.finalize_archive(root,output,'synthetic.zip')
    assert list(output.iterdir())==[]
    assert target.read_bytes()==b'preserve'


@pytest.mark.parametrize('name',['Rplots.pdf','Rplots.svg','Rplot001.png','Rplot1000.pdf'])
def test_tarball_verifier_refuses_historical_zip_default_before_tar_read(tmp_path,name,monkeypatch):
    import zipfile
    sealed=tmp_path/'synthetic.zip'
    with zipfile.ZipFile(sealed,'w') as z:z.writestr(name,b'preserve default fixture')
    before=sealed.read_bytes()
    mod=load('verify_release_tarball')
    monkeypatch.setattr(mod.tarfile,'open',lambda *args,**kwargs:pytest.fail('bad sealed ZIP must refuse before tar read'))
    problems=mod.check(tmp_path/'not-read.tar.gz',sealed)
    assert len(problems)==1 and 'root default R device output' in problems[0]
    assert sealed.read_bytes()==before


@pytest.mark.parametrize('state',['dirty','missing','clean'])
def test_actual_guard_cli_has_actionable_stderr_and_silent_success(tmp_path,state):
    root=tmp_path/'root'
    if state!='missing':root.mkdir()
    if state=='dirty':(root/'Rplots.pdf').write_bytes(b'preserve CLI fixture')
    result=subprocess.run([sys.executable,'-B',str(TOOLS/'tracked_file_policy.py'),
                           '--check-default-r-device-outputs',str(root)],
                          capture_output=True,text=True,timeout=15)
    assert result.stdout==''
    if state=='clean':
        assert result.returncode==0 and result.stderr==''
    elif state=='dirty':
        assert result.returncode==2
        assert 'REFUSED' in result.stderr and 'Rplots.pdf' in result.stderr
        assert 'preserve/adjudicate' in result.stderr and 'no bytes removed' in result.stderr
        assert (root/'Rplots.pdf').read_bytes()==b'preserve CLI fixture'
    else:
        assert result.returncode==2 and 'scan incomplete' in result.stderr
        assert 'existing nonsymlink directory root' in result.stderr


def test_clean_derivation_does_not_add_guard_pass_lines(tmp_path,monkeypatch,capsys):
    private=tmp_path/'private';public=tmp_path/'public';private.mkdir();public.mkdir()
    for root in (private,public):(root/'README.md').write_text('public fixture')
    monkeypatch.setattr(sys,'argv',['verify_tier_derivation',str(private),str(public)])
    assert load('verify_tier_derivation').main()==0
    captured=capsys.readouterr()
    assert 'root default R device output guard' not in captured.out
    assert 'OK: public tier' in captured.out and captured.err==''
