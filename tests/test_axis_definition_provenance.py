"""Definition provenance and signed values; synthetic receipts are contract fixtures, not execution evidence."""
from pathlib import Path
import json,hashlib,copy
import numpy as np
import pytest
from tools import protein_pcoa_render as ppr
from tools import protein_pcoa_ordinate as ordinate
import importlib.util
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
docs=load("axis_definition_docs",Path(__file__).resolve().parents[1]/"tools/protein_pcoa_page_docs.py")
from tests.test_protein_identity_missingness import page_record

@pytest.fixture
def native_packet(tmp_path):
    # Actually run the unchanged native numeric function on a tiny nonmetric input.
    distance=np.array([[0,0,0],[0,0,1],[0,1,0]],dtype=np.float64)
    before=distance.copy();coords,ratios=ordinate.classical_pcoa(distance)
    table=tmp_path/'PCOA_KS.tsv'
    table.write_text('id\tPC1\tPC2\tPC3\n'+''.join(f'SYN_{i}\t'+ '\t'.join(repr(float(x)) for x in row)+'\n' for i,row in enumerate(coords)))
    source=Path(ordinate.__file__);source_binding=ppr.file_binding(source);coordinate=ppr.file_binding(table)
    run=dict(resource_schema='sapote-mamey.protein-pcoa-resource.v1',pct_axes=list(ratios),outputs={table.name:coordinate},producer_sources=[source_binding])
    run_path=tmp_path/'RUN_KS.json';run_path.write_text(json.dumps(run));run_binding=ppr.file_binding(run_path)
    return run,coordinate,source_binding,source.read_bytes(),run_binding,coords,ratios

def metadata(packet,**changes):
    run,coordinate,source,raw,binding,*_=packet
    args=dict(run=run,coordinates=coordinate,source=source,source_bytes=raw,run_binding=binding,resource_chain=True);args.update(changes)
    return ppr.bound_axis_metadata(**args)

def test_native_nonmetric_ratios_preserved_with_truthful_definition(native_packet):
    run,coordinate,source,raw,binding,coords,ratios=native_packet
    original=coords.copy();axes=metadata(native_packet)
    assert axes['pct_axes']==list(ratios)==run['pct_axes']
    assert np.array_equal(coords,original)
    assert any(value>100 for value in ratios) and any(value<0 for value in ratios)
    assert axes['definition']['state']=='NATIVE_COORDINATE_SOURCE_BOUND'
    assert axes['coordinates']==coordinate and axes['definition']['source']==source
    assert axes['annotation_run']==binding and axes['fit_execution']=='RECORDED_SUCCESSFUL_RESOURCE_CHAIN'
    assert axes['renderer_fit_execution']=='NOT_EXECUTED'
    rec=page_record();rec['axis_metadata']=axes;rec['pct_axes']=list(ratios[:2])
    caption=docs.caption_text(rec,[],{},None)
    assert 'eigenvalue/signed-trace ratios' in caption and 'not conventional variance explained' in caption
    assert 'without clipping or renormalization' in caption and 'only the first two axes' in caption
    assert '150.0%' in caption and len(axes['pct_axes'])==3

@pytest.mark.parametrize('fault',['no_chain','wrong_coordinate','wrong_source','duplicate_source','changed_function','legacy_schema','missing_producers','altered_bytes'])
def test_no_native_definition_claim_from_unbound_or_unknown_metadata(native_packet,fault):
    run,coordinate,source,raw,binding,*_=native_packet;run=copy.deepcopy(run);changes=dict(run=run)
    if fault=='no_chain':changes['resource_chain']=False
    if fault=='wrong_coordinate':run['outputs'][Path(coordinate['path']).name]['sha256']='0'*64
    if fault=='wrong_source':run['producer_sources'][0]['sha256']='0'*64
    if fault=='duplicate_source':run['producer_sources'].append(run['producer_sources'][0])
    if fault=='changed_function':
        raw=raw.replace(b'100 * v / tr',b'99 * v / tr');source=dict(source,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw));run['producer_sources']=[source];changes.update(source=source,source_bytes=raw)
    if fault=='legacy_schema':run.pop('resource_schema')
    if fault=='missing_producers':run.pop('producer_sources')
    if fault=='altered_bytes':changes['source_bytes']=raw+b'\n'
    axes=metadata(native_packet,**changes)
    assert axes['definition']['state']=='SUPPLIED_UNVERIFIED'
    assert axes['fit_execution']=='UNVERIFIED_SUPPLIED_METADATA'
    assert axes['pct_axes']==native_packet[-1]
    rec=page_record();rec['axis_metadata']=axes;rec['pct_axes']=axes['pct_axes'][:2]
    caption=docs.caption_text(rec,[],{},None)
    assert 'supplied percentage annotations' in caption and 'definition and fit execution are unverified' in caption
    assert 'native eigenvalue/signed-trace ratios' not in caption

def test_supplied_definition_field_cannot_promote_sidecar_to_native():
    run=dict(pct_axes=[150,0,-50],definition={'state':'NATIVE_COORDINATE_SOURCE_BOUND'},fit_execution='SUCCEEDED')
    axes=ppr.axis_metadata(run);assert axes['definition']['state']=='SUPPLIED_UNVERIFIED'
    assert axes['pct_axes']==[150,0,-50] and axes['fit_execution']=='UNVERIFIED_SUPPLIED_METADATA'

def test_legacy_caption_never_assumes_conventional_variance():
    rec=page_record();rec['pct_axes']=[150,-50]
    caption=docs.caption_text(rec,[],{},None)
    assert 'supplied percentage annotations' in caption and '150.0%' in caption and '-50.0%' in caption
    assert 'share of variance explained' not in caption

def test_missing_axes_remain_missing():
    axes=ppr.axis_metadata({});assert axes['state']=='NOT_PROVIDED' and axes['pct_axes'] is None

from tests.test_page_receipt_finalization import attempt
@pytest.mark.parametrize('route',['native_bound','legacy_forged','failed_terminal'])
def test_main_associates_definition_only_after_coordinate_and_terminal_admission(attempt,monkeypatch,route):
    """Main-route contract with fabricated terminal records; no watched worker ran."""
    run,out,meta,names,root,check=attempt
    # The fixture's module is loaded independently, so use its module instance.
    from tests import test_page_receipt_finalization as fixture
    driver=fixture.ppr;kit=meta.parent;directory=kit/'out_KS';run_path=directory/'RUN_KS.json'
    source=root/'tools/protein_pcoa_ordinate.py';source.write_bytes(Path(ordinate.__file__).read_bytes())
    values=[150.,0.,-50.];record=dict(pct_axes=values)
    if route!='legacy_forged':
        resources=directory/'RESOURCE_ATTEMPT';resources.mkdir()
        monitor=resources/'monitored_resource.json';monitor.write_text(json.dumps(dict(attempt_id='SYN_AXIS',watch=dict(exit_code=0))))
        clusters=directory/'REFERENCE_CLUSTERS_KS.tsv';clusters.write_text('centroid\tmember\nSYN_A\tSYN_A\n')
        record.update(resource_schema='sapote-mamey.protein-pcoa-resource.v1',attempt_id='SYN_AXIS',
                      producer_sources=[driver.file_binding(source)],resource_receipt=dict(relative_path='RESOURCE_ATTEMPT/monitored_resource.json',sha256=sha(monitor)),
                      outputs={p.name:driver.file_binding(p) for p in [directory/'PCOA_KS.tsv',clusters]})
        run_path.write_text(json.dumps(record))
        (resources/'terminal.json').write_text(json.dumps(dict(state='FAILED' if route=='failed_terminal' else 'SUCCEEDED',attempt_id='SYN_AXIS',run=driver.file_binding(run_path))))
    else:
        record.update(definition=dict(state='NATIVE_COORDINATE_SOURCE_BOUND'),fit_execution='SUCCEEDED');run_path.write_text(json.dumps(record))
    captured=[]
    def page(a,s,*args,**kwargs):
        axes=a._axis_metadata_by_set[s];captured.append(axes);(out/'figure.svg').write_text('<svg/>');return dict(set=s,prefix='TEST',axis_metadata=axes)
    monkeypatch.setattr(driver,'build_page',page)
    if route=='failed_terminal':
        assert run()==2 and captured==[] and not (out/'render_receipt.json').exists()
    else:
        assert run()==0
        axes=json.loads((out/'render_receipt.json').read_text())['panels'][0]['axis_metadata']
        assert axes['pct_axes']==values and axes['renderer_fit_execution']=='NOT_EXECUTED'
        assert axes['definition']['state']==('NATIVE_COORDINATE_SOURCE_BOUND' if route=='native_bound' else 'SUPPLIED_UNVERIFIED')
        if route=='native_bound':assert axes['definition']['source']['sha256']==sha(source)

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
