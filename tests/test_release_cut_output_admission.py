"""Existing-output admission without preparation, registry or package execution."""
import os
from pathlib import Path
import subprocess
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]

def fixture(tmp_path,kind):
    source=tmp_path/'source';source.mkdir();(source/'evidence').write_bytes(b'keep source')
    output=tmp_path/'output'
    if kind=='directory':output.mkdir();(output/'prior.log').write_bytes(b'keep prior log')
    elif kind=='file':output.write_bytes(b'keep prior file')
    elif kind=='dangling':output.symlink_to(tmp_path/'not-created')
    else:
        target=tmp_path/'target';target.mkdir();(target/'prior.log').write_bytes(b'keep alias evidence');output.symlink_to(target,target_is_directory=True)
    return source,output

def run(tmp_path,source,output,*,mode='monolithic',phase='',full=False):
    env=dict(os.environ,PYTHON=sys.executable,PYTHONDONTWRITEBYTECODE='1',RELEASE_PYTEST_MODE=mode,RELEASE_WORKFLOW_PHASE=phase)
    env.pop('PYTEST_ADDOPTS',None)
    text=(ROOT/'tools/release_cut.sh').read_text()
    if full:
        tools=source/'tools';tools.mkdir();(tools/'cut_preflight.sh').write_text('# no cut hooks execute in this refusal fixture\n')
        command=['bash',str(ROOT/'tools/release_cut.sh'),'9.7.452',str(source),str(output)]
        return subprocess.run(command,cwd=tmp_path,env=env,capture_output=True,text=True,timeout=5)
    prefix=text.split('\nif [[ "$PYTEST_MODE" == partitioned && -z "$PHASE" ]]; then',1)[0]
    return subprocess.run(['bash','-s','--','9.7.452',str(source),str(output)],input=prefix+'\nprintf "ADMITTED\\n"\n',cwd=tmp_path,env=env,capture_output=True,text=True,timeout=5)

@pytest.mark.parametrize('kind',['directory','file','dangling','alias'])
def test_monolithic_refuses_occupied_output_before_source_preparation(tmp_path,kind):
    source,output=fixture(tmp_path,kind)
    result=run(tmp_path,source,output)
    assert result.returncode==2 and 'RELEASE-PATH-003' in result.stderr
    assert 'fresh output directory' in result.stderr
    assert (source/'evidence').read_bytes()==b'keep source'
    if kind=='directory':assert (output/'prior.log').read_bytes()==b'keep prior log'
    elif kind=='file':assert output.read_bytes()==b'keep prior file'
    elif kind=='dangling':assert output.is_symlink() and not output.exists()
    else:assert output.is_symlink() and (output/'prior.log').read_bytes()==b'keep alias evidence'

@pytest.mark.parametrize('mode,phase',[('partitioned',''),('monolithic','prepare'),('monolithic','integrity'),('monolithic','post-gates')])
def test_resume_and_internal_owners_keep_their_existing_admission_boundary(tmp_path,mode,phase):
    source,output=fixture(tmp_path,'directory')
    result=run(tmp_path,source,output,mode=mode,phase=phase)
    assert result.returncode==0 and 'ADMITTED' in result.stdout
    assert (output/'prior.log').read_bytes()==b'keep prior log'

@pytest.mark.parametrize('kind',['directory','file','dangling','alias'])
def test_actual_package_phase_refuses_all_occupied_locators_before_builder(tmp_path,kind):
    source,output=fixture(tmp_path,kind)
    result=run(tmp_path,source,output,phase='package',full=True)
    assert result.returncode!=0 and 'package target is occupied' in result.stderr
    assert 'registry preflight' not in result.stderr and 'cut the CODE' not in result.stdout
    assert (source/'evidence').read_bytes()==b'keep source'
    if kind=='dangling':assert not output.exists() and output.is_symlink()
