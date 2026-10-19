from pathlib import Path
import os,json,hashlib,importlib.util,shutil
import pytest
from tools import protein_pcoa_render as current
from tests.test_page_receipt_finalization import attempt
ROOT=Path(__file__).resolve().parents[1]
SOURCE=Path(os.environ.get('LANE06_RUNTIME_PPR',ROOT/'tools/protein_pcoa_render.py'))
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
ppr=load('page_execution_driver',SOURCE)

def test_page_runtime_record_is_required(tmp_path):
    with pytest.raises(ppr.RenderRefusal,match='in-run runtime'):ppr.page_execution_record(tmp_path/'PAGE','stamp')

@pytest.mark.parametrize('fault',['stamp','versions','fit_state'])
def test_page_runtime_record_rejects_incomplete_or_other_run(tmp_path,fault):
    payload=dict(schema='sapote-mamey.r-page-execution.v1',stamp='stamp',scope='CURRENT_RENDER_PROCESS',labeler='BEE_GREEDY_PRINT_POINT_PLACEMENT_AND_R_GEOM_TEXT',numeric_fit_execution='NOT_EXECUTED_BY_THIS_RENDERER',r_version='SyntheticRversion',loaded_namespace_versions={n:'synthetic' for n in ['ggplot2','jsonlite','patchwork','svglite','ggtext']})
    if fault=='stamp':payload['stamp']='other'
    if fault=='versions':payload['loaded_namespace_versions'].pop('ggplot2')
    if fault=='fit_state':payload['numeric_fit_execution']='ASSUMED_FIT'
    (tmp_path/'PAGE_runtime.json').write_text(json.dumps(payload))
    with pytest.raises(ppr.RenderRefusal,match='incomplete or does not match'):ppr.page_execution_record(tmp_path/'PAGE','stamp')

def test_drawn_artifact_drift_is_not_completed(attempt,monkeypatch):
    from tools import protein_pcoa_page_docs as docs
    run,out,meta,names,root,qc=attempt
    def altered(*a):
        v=qc(*a);(out/'figure.svg').write_text('<svg>edited after drawing</svg>');return v
    monkeypatch.setattr(docs,'check_page_docs',altered)
    assert run()==2 and not (out/'render_receipt.json').exists()

@pytest.mark.skipif(not shutil.which('Rscript'),reason='Rscript unavailable')
def test_actual_page_records_in_run_versions_fonts_and_keys(tmp_path,monkeypatch):
    C=Path(current.__file__).resolve().parents[1]
    fixture=load('runtime_page_fixture',C/'tests/test_m5_452_pcoa_page_defaults.py');fixture.ppr=ppr
    root=fixture.make_kit(tmp_path,[('SYN-970',2.5,2.5,95.0),('SYN-971',.5,.5,30.0)])
    assert fixture.page(root)==0
    out=root/'out';render=json.loads((out/'render_receipt.json').read_text())
    r=render['rendering_runtime']['r_runtime'];fonts=render['rendering_runtime']['fonts']
    assert r['state']=='PER_PAGE_IN_RUN_RECORDS' and fonts['state']=='OBSERVED_FINAL_PDFS'
    record=r['pages'][0]['record'];assert record['r_version'].startswith('R version ')
    assert all(isinstance(record['loaded_namespace_versions'].get(n),str) and record['loaded_namespace_versions'][n] for n in ['ggplot2','patchwork','jsonlite','svglite','ggtext'])
    assert record['labeler']=='BEE_GREEDY_PRINT_POINT_PLACEMENT_AND_R_GEOM_TEXT'
    assert record['numeric_fit_execution']=='NOT_EXECUTED_BY_THIS_RENDERER'
    assert fonts['pages'][0]['faces'] and all('UNKNOWN' not in face for face in fonts['pages'][0]['faces'])
    assert render['artifact_root']==str(out.resolve()) and all(x['relative_path'] for x in render['outputs'])
    for b in render['outputs']:assert hashlib.sha256(Path(b['path']).read_bytes()).hexdigest()==b['sha256']
    qc=load('runtime_page_qc',ppr._ROOT/'tools/figure_render_qc.py')
    png=out/'PAGE_KS_query_PCOA_TRIMAP.png';flags=qc.completed_packet_flags(png,hashlib.sha256((out/'render_receipt.json').read_bytes()).hexdigest())
    assert not [m for lv,m in flags if lv=='error']
