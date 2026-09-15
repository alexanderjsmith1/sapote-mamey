import copy,json,xml.etree.ElementTree as ET
import pytest
from mamey.interactive_figures import bee_review_prototypes as module

def fixture():
    owners=[{'strain':'DEMO-'+str(i),'host_raw':'Bombus sp.','Candida':'positive' if i else 'negative','MRSA':'not_tested','source_row':i+2,'source_sha256':'a'*64} for i in range(2)]
    rows=[{'binding':{'strain':o['strain']},'assay':o,'comparison':{'disposition':'REVIEW_CANDIDATE','genome_input_sha256':'b'*64,'product_counts':{'NRPS':i+1}},'chitin':dict({f:i for f in module.FAMILIES},input_sha256='b'*64,receipt_sha256='c'*64)} for i,o in enumerate(owners)]
    return {'selected':rows,'bee_owner_rows':owners,'excluded_packages':[]}

def test_valid():assert len(module.validate(fixture()))==2

@pytest.mark.parametrize('mutation,code',[
    ('duplicate','EMPTY_OR_DUPLICATE_GENOME_STRAINS'),
    ('wasp','NON_BEE_OWNER_RECORD'),
    ('hold','GENOME_HOLD_NOT_CLEARED'),
    ('content','GENOME_CONTENT_MISMATCH'),
    ('negative','INVALID_FAMILY_COUNT'),
])
def test_refuses_invalid(mutation,code):
    d=copy.deepcopy(fixture())
    if mutation=='duplicate':d['selected'].append(d['selected'][0])
    if mutation=='wasp':d['bee_owner_rows'][0]['host_raw']='Wasp'
    if mutation=='hold':d['selected'][0]['comparison']['disposition']='QC_HOLD_AUDIT_ONLY'
    if mutation=='content':d['selected'][0]['chitin']['input_sha256']='d'*64
    if mutation=='negative':d['selected'][0]['chitin'][module.FAMILIES[0]]=-1
    with pytest.raises(ValueError,match=code):module.validate(d)

def test_generic_portable_render(tmp_path):
    source=tmp_path/'input.json';source.write_text(json.dumps(fixture()))
    out=tmp_path/'output';figures=module.render(source,out);assert len(figures)==4
    for f in figures:
        svg=ET.parse(out/f['svg']).getroot()
        assert not any(x.tag.endswith('image') for x in svg.iter())
        assert any(x.tag.endswith('text') for x in svg.iter())
        assert f['minimum_font_pt']>=8 and f['width_inches']==7.2
    with pytest.raises(ValueError,match='OUTPUT_ALREADY_EXISTS'):module.render(source,out)
