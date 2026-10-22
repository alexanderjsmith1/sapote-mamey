import shutil
import importlib.util
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('b03',ROOT/'tools/region_protein_by_genus.py')
b03=importlib.util.module_from_spec(spec);spec.loader.exec_module(b03)

def rows():
    return [dict(strain='fixture_a',genus='Example',amino_acids='1000',missing_CDS_lengths='0'),
            dict(strain='fixture_b',genus='Example',amino_acids='2000',missing_CDS_lengths='0')]

def test_valid():
    assert b03.validate(rows())['row_count']==2

@pytest.mark.parametrize('value',['nan','inf','-1','0','1.5',''])
def test_invalid_values(value):
    data=rows();data[0]['amino_acids']=value
    with pytest.raises(ValueError): b03.validate(data)

def test_duplicate():
    data=rows();data[1]['strain']=data[0]['strain']
    with pytest.raises(ValueError,match='duplicate'): b03.validate(data)

def test_missing_length():
    data=rows();data[0]['missing_CDS_lengths']='1'
    with pytest.raises(ValueError,match='missing CDS'): b03.validate(data)

def test_empty():
    with pytest.raises(ValueError): b03.validate([])

def test_one_point():
    with pytest.raises(ValueError): b03.validate(rows()[:1])

def test_blank_identity():
    data=rows();data[0]['genus']=''
    with pytest.raises(ValueError,match='blank identity'): b03.validate(data)

def test_subfloor_refused(tmp_path):
    with pytest.raises(ValueError,match='publication gate'):
        b03.main(['--data','absent','--caption','absent','--out',str(tmp_path/'out'),'--min-text-pt','7'])

@pytest.mark.skipif(shutil.which("Rscript") is None, reason="needs R: Rscript not on PATH (see bundle_support/install_r_figure_packages.R)")
def test_render_and_no_overwrite(tmp_path):
    import json
    data=tmp_path/'data.tsv'
    data.write_text('strain\tgenus\tamino_acids\tmissing_CDS_lengths\na\tExample\t1000\t0\nb\tExample\t2000\t0\nc\tExample\t3000\t0\nd\tOther\t4000\t0\n')
    cap=tmp_path/'caption.md';cap.write_text('Synthetic assembly totals grouped by genus.\n')
    args=['--data',str(data),'--caption',str(cap),'--out',str(tmp_path/'out')]
    assert b03.main(args)==0
    receipt=json.loads((tmp_path/'out/RUN_INFO.json').read_text())
    runtime=json.loads((tmp_path/'out/R_RUNTIME.json').read_text())
    assert receipt['execution']['R_version'] == runtime['R_version']
    assert receipt['execution']['ggplot2_version'] == runtime['packages']['ggplot2']['version']
    assert runtime['session_info'] and runtime['packages']['ggplot2']['path']
    import hashlib
    for artifact in receipt['execution']['artifacts']:
        assert artifact['sha256']==hashlib.sha256((tmp_path/'out'/artifact['path']).read_bytes()).hexdigest()
    assert Path(receipt['execution']['command'][0]).is_absolute()
    assert receipt['min_text']['smallest_pt']>=8
    assert abs(receipt['min_text']['page_width_in']-7.2)<=0.01   # Linux cairo rounds the page to whole points (7.194 in)
    assert (tmp_path/'out/region_protein_by_genus.png').read_bytes().find(b'Sapote-Mamey')>=0
    box=(tmp_path/'out/region_protein_by_genus_box_summary.tsv').read_text().splitlines()
    assert box[1].split('\t')==['1','1.5','2','2.5','1','3']
    with pytest.raises(FileExistsError): b03.main(args)


def test_missing_runtime_is_not_success(tmp_path):
    with pytest.raises(FileNotFoundError): b03.read_r_runtime(tmp_path/'missing.json')

@pytest.mark.parametrize('record',[{}, {'schema_version':'sapote.r-render-runtime.v1','R_version':'R mock','session_info':['mock'],'packages':{}}])
def test_incomplete_runtime_is_not_success(tmp_path,record):
    import json
    path=tmp_path/'runtime.json';path.write_text(json.dumps(record))
    with pytest.raises(ValueError,match='runtime receipt'): b03.read_r_runtime(path)
