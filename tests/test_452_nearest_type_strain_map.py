import csv,json
from pathlib import Path
import pytest
from PIL import Image
from pypdf import PdfReader
from tools import nearest_type_strain_map as m
from tools._map_export import sha


def fixture(tmp_path,flag=True):
    tree=tmp_path/'anchors.contree';tree.write_text('((tipA:0.1,tipB:0.2):0.1,(tipC:0.1,(tipD:0.1,tipE:0.1):0.1):0.2);\n')
    anchors=tmp_path/'anchors.tsv'
    names=['Streptomyces example A','Nocardia example B','Micromonospora example C','Streptomyces example D','Nocardia example E']
    anchors.write_text('tip\tdeposited_organism_name'+('\tfromtype' if flag else '')+'\n'+''.join(f'tip{c}\t{n}'+('\t'+v if flag else '')+'\n' for c,n,v in zip('ABCDE',names,['1','false','true','0',''])))
    mapping=tmp_path/'map.tsv';mapping.write_text('isolate\tanchor_tip\thost_as_recorded\n'+''.join(f'SYN-{970+i}\ttip{c}\tHost {i%2}\n' for i,c in enumerate('ABCDEA')))
    return tree,anchors,mapping


def test_render_and_counts(tmp_path):
    t,a,i=fixture(tmp_path);out=tmp_path/'out'
    assert m.main(['--tree',str(t),'--anchors',str(a),'--isolate-map',str(i),'--out',str(out)])==0
    reader=PdfReader(out/'nearest_type_strain_map.pdf');sizes=[]
    text=reader.pages[0].extract_text(visitor_text=lambda t,cm,tm,f,s:sizes.append(s) if t.strip() else None)
    assert text.count('[T]')==2 and min(sizes)>=8
    assert float(reader.pages[0].mediabox.width)==pytest.approx(7.2*72)
    assert 'Sapote-Mamey' in reader.metadata.creator
    image=Image.open(out/'nearest_type_strain_map.png');assert image.width==4320 and 'Sapote-Mamey' in image.info['Software']
    info=json.loads((out/'RUN_INFO.json').read_text());assert info['host_bar_sum']==info['isolate_rows']==6
    colors=json.loads(m.PALETTE_PATH.read_text())['default']
    assert all(r['color']==colors[r['genus']] for r in info['tip_labels'])
    assert all(r['name'] in text for r in info['tip_labels'])
    counts=list(csv.DictReader((out/'host_counts.tsv').open(),delimiter='\t'));assert sum(int(r['isolates']) for r in counts)==6
    assert {sha(t),sha(a),sha(i)}<={x['sha256'] for x in info['inputs']}
    assert all(sha(out/r['path'])==r['sha256'] for r in info['outputs'])
    with pytest.raises(FileExistsError):m.main(['--tree',str(t),'--anchors',str(a),'--isolate-map',str(i),'--out',str(out)])


def test_missing_fromtype_no_markers(tmp_path):
    t,a,i=fixture(tmp_path,False);out=tmp_path/'out'
    m.main(['--tree',str(t),'--anchors',str(a),'--isolate-map',str(i),'--out',str(out)])
    assert '[T]' not in PdfReader(out/'nearest_type_strain_map.pdf').pages[0].extract_text()
    assert json.loads((out/'RUN_INFO.json').read_text())['type_marker_source']=='column absent; no type markers'


def test_palette_override(tmp_path):
    t,a,i=fixture(tmp_path);raw=json.loads(m.PALETTE_PATH.read_text());key=next(iter(raw['sets']))
    _,anchors,_,_,_=m.load(t,a,i,key)
    expected={**raw['default'],**raw['sets'][key]}
    assert all(r['color']==expected[r['genus']] for r in anchors.values())


@pytest.mark.parametrize('mutation,error',[
    ('duplicate','ISOLATE_ID'),('unknown','UNKNOWN_ANCHOR'),('flag','INVALID_FROMTYPE'),
    ('anchor','ANCHOR_TIPS'),('length','TREE_LENGTH'),('blank','EMPTY_DEPOSITED_NAME')])
def test_refusals(tmp_path,mutation,error):
    t,a,i=fixture(tmp_path)
    if mutation=='duplicate':i.write_text(i.read_text()+i.read_text().splitlines()[1]+'\n')
    if mutation=='unknown':i.write_text(i.read_text().replace('tipA','tipZ'))
    if mutation=='flag':a.write_text(a.read_text().replace('\ttrue','\tmaybe'))
    if mutation=='anchor':a.write_text(a.read_text().replace('tipA','tipZ'))
    if mutation=='length':t.write_text(t.read_text().replace('0.1','-0.1'))
    if mutation=='blank':a.write_text(a.read_text().replace('Streptomyces example A',''))
    with pytest.raises(ValueError,match=error):m.load(t,a,i)


def test_tree_and_name_preserved(tmp_path):
    t,a,i=fixture(tmp_path);a.write_text(a.read_text().replace('Nocardia example B','Nocardia example B (T)'))
    tree,anchors,counts,_,_=m.load(t,a,i)
    assert [x.name for x in tree.get_terminals()]==['tipA','tipB','tipC','tipD','tipE']
    assert [x.branch_length for x in tree.get_terminals()]==[.1,.2,.1,.1,.1]
    assert anchors['tipB']['deposited_organism_name']=='Nocardia example B (T)' and not anchors['tipB']['type_marker']
    with pytest.raises(ValueError,match='PRINT_GATE'):m.draw(tree,anchors,counts,floor=7)
