"""Only actual declaration prefix executes; never source preparation or a cut."""
import os
from pathlib import Path
import subprocess
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]

def invoke(tmp_path, source, output):
    text=(ROOT/'tools/release_cut.sh').read_text().split('\nPHASE=',1)[0]
    code=text+'\nprintf "SOURCE=%s\\nOUTPUT=%s\\n" "$SRC" "$OUT"\n'
    env=dict(os.environ,PYTHON=sys.executable,PYTHONDONTWRITEBYTECODE='1')
    env.pop('PYTEST_ADDOPTS',None);env.pop('RELEASE_PYTEST_MODE',None)
    return subprocess.run(['bash','-s','--','9.7.452',str(source),str(output)],input=code,cwd=tmp_path,env=env,capture_output=True,text=True,timeout=5)

@pytest.mark.parametrize('kind',['relative','parent_relative','absolute','missing_parents'])
def test_output_is_bound_in_caller_directory(tmp_path,kind):
    source=tmp_path/'source with spaces';source.mkdir()
    if kind=='relative':output=Path('out with spaces')
    elif kind=='parent_relative':output=Path('../sibling/output');(tmp_path.parent/'sibling').mkdir(exist_ok=True)
    elif kind=='absolute':output=tmp_path/'absolute output'
    else:output=Path('not-created/nested/output')
    expected=(tmp_path/output).resolve()
    result=invoke(tmp_path,source,output)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'OUTPUT='+str(expected)+'\n' in result.stdout
    assert not expected.exists() and list(source.iterdir())==[]

@pytest.mark.parametrize('kind',['equal','within','ancestor','alias_within'])
def test_overlapping_trees_refuse_before_source_or_output_mutation(tmp_path,kind):
    source=tmp_path/'source';source.mkdir()
    if kind=='equal':output=source
    elif kind=='within':output=source/'nested/output'
    elif kind=='ancestor':output=tmp_path
    else:
        alias=tmp_path/'source_alias';alias.symlink_to(source,target_is_directory=True);output=alias/'nested/output'
    marker=source/'evidence';marker.write_bytes(b'preserve')
    result=invoke(tmp_path,source,output)
    assert result.returncode==2
    assert 'RELEASE-PATH-002' in result.stderr
    assert marker.read_bytes()==b'preserve' and list(source.iterdir())==[marker]

def test_missing_source_is_actionable_hold_without_output_creation(tmp_path):
    output=tmp_path/'output'
    result=invoke(tmp_path,tmp_path/'absent-source',output)
    assert result.returncode==2 and 'RELEASE-PATH-001' in result.stderr
    assert not output.exists()


@pytest.mark.parametrize('optimization',['0','1','2'])
def test_source_file_is_typed_hold_even_when_python_optimizes(tmp_path,monkeypatch,optimization):
    monkeypatch.setenv('PYTHONOPTIMIZE',optimization)
    source=tmp_path/'source_file';source.write_bytes(b'preserve source file')
    output=tmp_path/'output'
    result=invoke(tmp_path,source,output)
    assert result.returncode==2 and 'RELEASE-PATH-001' in result.stderr
    assert source.read_bytes()==b'preserve source file' and not output.exists()
