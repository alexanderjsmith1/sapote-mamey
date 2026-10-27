from pathlib import Path
import importlib.util
import os
import pytest
ROOT=Path(os.environ.get('CAPABILITY_REVIEW_BASE',Path(__file__).resolve().parents[1]))
spec=importlib.util.spec_from_file_location('capability_byte_fixture',ROOT/'tests/test_delivery_capability_card.py')
fx=importlib.util.module_from_spec(spec);spec.loader.exec_module(fx)
@pytest.fixture
def card():
    value=fx.CapabilityCard();value.setUp()
    try:yield value
    finally:value.tearDown()
def receipt(card,adapter,count='missing',empty=False):
    if empty:
        card.artifact.write_bytes(b'');card.config['artifact'].update(sha256=fx.mod.sha(card.artifact),bytes=0)
    target=card.config['artifact'];kind='static_dependencies' if adapter=='tb03_static' else 'data_syntax'
    if adapter=='tb03_static':
        value={'schema':'sapote.standalone_delivery.receipt.v1','status':'PASS_STATIC_CONTRACT','files_checked':[{'path':'viewer.html','sha256':target['sha256'],'state':'MATCH'}],'errors':[]}
        if count!='missing':value['files_checked'][0]['bytes']=count
        card.receipt(value,kind=kind,adapter=adapter,member='viewer.html')
    else:
        value={'status':'PASS_DATA_BINDINGS_AND_JS_SYNTAX','HTML_sha256':target['sha256'],'errors':[]}
        if count!='missing':value['standalone_HTML_bytes']=count
        card.receipt(value,kind=kind,adapter=adapter)
    return card.check(kind)
@pytest.mark.parametrize('adapter',['tb03_static','locus_data_syntax'])
@pytest.mark.parametrize('count',['missing',None,False])
def test_required_count_cannot_be_silently_hash_only(card,adapter,count):
    row=receipt(card,adapter,count,empty=count is False)
    assert row['state']=='RECEIPT_INVALID'
@pytest.mark.parametrize('adapter',['tb03_static','locus_data_syntax'])
@pytest.mark.parametrize('empty',[False,True])
def test_valid_integer_count_keeps_bound_producer_scope(card,adapter,empty):
    count=0 if empty else card.config['artifact']['bytes'];row=receipt(card,adapter,count,empty)
    assert row['state']=='BOUND_REPORTED_PASS' and row['producer_claim_only'] is True

def test_explicit_hash_only_protein_adapter_remains_supported(card):
    card.receipt({'status':'PASS_DATA_PRESERVATION_AND_JS_SYNTAX','output_viewer_sha256':card.config['artifact']['sha256'],'point_arrays_unchanged':True},kind='data_syntax',adapter='protein_data_syntax')
    assert card.check('data_syntax')['state']=='BOUND_REPORTED_PASS'
