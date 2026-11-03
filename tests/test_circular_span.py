from types import SimpleNamespace as NS
import pytest
from mamey import parsers
from mamey.models import BGCRecord

def _record(topology,length):
    return NS(id='CP000001.1',name='CP000001.1',description='chromosome',annotations={'topology':topology},features=[NS(type='region',location=NS(start=0,end=length),qualifiers={'product':['NRPS']})],seq='N'*length)

def _run(monkeypatch,topology='circular',length=200,contig=1000,start=900,end=100):
    rec=_record(topology,length);name='CP000001.1.region001.gbk'
    monkeypatch.setattr(parsers,'validate_region_intake_resources',lambda p:None)
    monkeypatch.setattr(parsers,'read_genbank_records',lambda p,region_only=False:[(name,rec)])
    monkeypatch.setattr(parsers,'_region_orig_bounds_from_zip',lambda p:{name:(start,end)})
    monkeypatch.setattr(parsers,'_contig_length_map_from_zip',lambda p:{rec.id:contig} if contig else {})
    return list(parsers.iter_region_core_inputs('synthetic.zip'))[0][2]

def test_wrap_has_validated_span_and_nonwrap_has_no_new_field(monkeypatch):
    fields=_run(monkeypatch); assert fields['validated_circular_span_bp']==200
    assert BGCRecord(**fields).length_kb==0.2
    fields=_run(monkeypatch,topology='linear',length=200,start=100,end=300)
    assert 'validated_circular_span_bp' not in fields and BGCRecord(**fields).length_kb==0.2

@pytest.mark.parametrize('options,code',[
    ({'topology':'linear'},'CIRCULAR_REGION_METADATA_UNRESOLVED'),
    ({'contig':0},'CIRCULAR_REGION_METADATA_UNRESOLVED'),
    ({'length':201},'CIRCULAR_REGION_LENGTH_MISMATCH'),
    ({'start':1000},'CIRCULAR_REGION_METADATA_UNRESOLVED'),
])
def test_unverified_wraps_refuse(monkeypatch,options,code):
    with pytest.raises(ValueError,match=code): _run(monkeypatch,**options)
