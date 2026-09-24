"""Execute re-authored queue fixes with generic synthetic records and no external compute."""
import copy
import csv
import json
from pathlib import Path
import re
import sqlite3
import zipfile
import pytest
from tools import bigscape_clinker_html as clinker
from tools import bigscape_cross_strain as cross
from tools import bigscape_prep as prep

def gene(i,og):
    return dict(orf=i,x0=i*100,x1=i*100+80,strand=1,gene_kind='',aa=20,pfams=[og],og=og)

def payload(monkeypatch, minimum=1):
    genes={1:[gene(0,'PF1'),gene(1,'PF2'),gene(2,'PF3')],
           2:[gene(0,'PF8'),gene(1,'PF9')],3:[gene(0,'PF1'),gene(1,'PF2')],4:[gene(0,'PF1')]}
    monkeypatch.setattr(clinker,'genes_for_gbk',lambda _,gid:copy.deepcopy(genes[gid]))
    members=[dict(gbk_id=i,record_id=i,strain=f'fixture-{i}',cls='query' if i<4 else 'REF',product='example') for i in genes]
    return clinker.build_family(None,1,.7,{1:members},min_genes=minimum,row_order='similarity')

def test_seriation_and_hidden_reference_do_not_change_family_scope(monkeypatch,tmp_path):
    data=payload(monkeypatch,2)
    assert [t['record_id'] for t in data['tracks']]==[1,3,2]
    assert data['hidden_tracks']==[dict(strain='fixture-4',record_id=4,genes=1)]
    assert data['private'] is False
    out=tmp_path/'page.html';clinker.write_page(data,'Synthetic family',out)
    text=out.read_text()
    assert '1 track(s) with fewer than 2 genes hidden' in text
    assert 'id="hidden"' in text and '$("hidden").textContent' not in text
    assert '__HIDDEN_NOTE__' not in text

def test_no_hidden_tracks_still_writes_complete_page(monkeypatch,tmp_path):
    data=payload(monkeypatch);data['tracks'][0]['strain']='</script><script>bad()</script>'
    out=tmp_path/'page.html';clinker.write_page(data,'<fixture>',out)
    text=out.read_text()
    assert text.startswith('<!doctype html>') and '&lt;fixture&gt;' in text
    assert '</script><script>bad()' not in text

@pytest.mark.parametrize('pattern',['^QUERY','['])
def test_bad_query_regex_refused_before_opening_db(pattern,tmp_path):
    db=tmp_path/'missing.db'
    with pytest.raises(SystemExit) as e:clinker.main(['--db',str(db),'--out',str(tmp_path/'out'),'--query-regex',pattern])
    assert e.value.code==2 and not db.exists()

def test_full_deposited_label_and_duplicate_key_refusal(tmp_path):
    full='Example genus species complete deposited strain designation beyond three words'
    assert clinker.classify('REF__contig.region001.gbk',full,re.compile(r'^(QUERY-\d+)_'),())[0]==full
    labels=tmp_path/'labels.tsv';labels.write_text('strain\tlabel\nref\tFirst\nref\tSecond\n')
    with pytest.raises(ValueError):clinker.load_labels(labels)
    with pytest.raises(ValueError):cross.load_labels(labels)

def test_cross_strain_refuses_directory_before_db_open(tmp_path):
    db=tmp_path/'absent.db'
    with pytest.raises(SystemExit) as e:cross.main(['--db',str(db),'--out',str(tmp_path),'--run-id','1'])
    assert e.value.code==2 and not db.exists()

def test_product_parking_is_explicit_and_label_keys_stay_exact(monkeypatch,tmp_path):
    def row(product,fid):
        return dict(cutoff='.7',family_id=str(fid),run_id='1',normalized_cutoff='0.7',qualified_family_id=f'1:0.7:{fid}',gcf_namespace='fixture',n_strains='2',strains='query-1,ref-1',strain_labels='Deposited name (ref-1); query-1',n_members='2',bin='example',dominant_product=product,contains_MIBiG='no',members_locators='source-records')
    rows=[row('terpene',1),row('NRPS',2)]
    monkeypatch.setattr(cross,'build_rows',lambda *args:rows)
    out=tmp_path/'families.tsv'
    assert cross.main(['--db','unused','--out',str(out),'--run-id','1','--exclude-products','terpene'])==0
    kept=list(csv.DictReader(out.open(),delimiter='\t'));parked=list(csv.DictReader(Path(str(out)+'.PARKED.tsv').open(),delimiter='\t'))
    assert kept[0]['strains']=='query-1,ref-1' and kept[0]['family_id']=='2'
    assert parked[0]['family_id']=='1'
    receipt=json.loads(Path(str(out)+'.FILTER.json').read_text());assert receipt['kept']==receipt['parked']==1

def test_small_query_filter_never_mutates_source_or_unselected_reference(tmp_path):
    source=tmp_path/'input.zip'
    with zipfile.ZipFile(source,'w') as z:
        z.writestr('contig_A.region001.gbk','LOCUS fixture\n     CDS             1..30\n//\n')
        z.writestr('contig_B.region002.gbk','LOCUS fixture\n'+'     CDS             1..30\n'*4+'//\n')
    before=source.read_bytes();query=tmp_path/'query';ref=tmp_path/'ref';query.mkdir();ref.mkdir();excluded=[]
    assert prep.stage_zip(source,query,'query-1',4,excluded)==1
    assert prep.stage_zip(source,ref,'ref-1')==2
    assert len(excluded)==1 and excluded[0]['n_cds']==1
    assert excluded[0]['identity_state']=='SOURCE_RECORD_ONLY_ALIAS_UNBOUND'
    assert source.read_bytes()==before


def test_pdf_completion_closes_only_owned_browser(monkeypatch,tmp_path):
    pytest.importorskip('pypdf')
    from reportlab.pdfgen import canvas
    html=tmp_path/'family.html';html.write_text('<style></style>fixture')
    processes=[]
    class Browser:
        def __init__(self,args,**kwargs):
            path=next(x.split('=',1)[1] for x in args if x.startswith('--print-to-pdf='))
            pdf=canvas.Canvas(path);pdf.drawString(20,100,'GCF family synthetic fixture');pdf.save()
            self.stopped=False;processes.append(self)
        def poll(self):return 0 if self.stopped else None
        def terminate(self):self.stopped=True
        def wait(self,timeout):return 0
        def kill(self):raise AssertionError('graceful termination should suffice')
    monkeypatch.setattr(clinker.subprocess,'Popen',Browser)
    assert clinker.to_pdf(html,3,'unused')==str(html.with_suffix('.pdf'))
    assert processes[0].stopped
    assert not Path(str(html)+'.print.html').exists()
    assert clinker.to_pdf(html,3,'unused') is None
    assert len(processes)==1
