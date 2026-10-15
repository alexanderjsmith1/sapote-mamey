"""Joint renderer regressions using synthetic saved search results, never a live search."""
import csv
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest
from mamey.blastp_ingest import BLASTP_HITS_SCHEMA
from mamey.protein_binding import protein_sha256

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tools/blastp_identity_figures.py'

def tool():
    spec=importlib.util.spec_from_file_location('combined_renderer',SOURCE)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod

def store(path,rows):
    with sqlite3.connect(path) as con:
        names=[n for n,_,_ in BLASTP_HITS_SCHEMA]
        con.execute('CREATE TABLE hits ('+', '.join(n+' '+t+(' NOT NULL' if nn else '') for n,t,nn in BLASTP_HITS_SCHEMA)+')')
        for r in rows:
            row=dict.fromkeys(names)|dict(workspace='synthetic',bgc_id='BGC001',provenance_suspect=0,channel='ncbi_nr',hit_rank=1)|r
            con.execute('INSERT INTO hits VALUES ('+','.join('?' for _ in names)+')',[row[n] for n in names])

@pytest.fixture
def world(tmp_path):
    p={'A':'M'+'A'*99,'B':'M'+'K'*199,'C':'M'+'L'*149,'D':'M'+'G'*149,'E':'M'+'P'*99}
    prots={'ctg1_1':p['A'],'ctg1_2':p['C'],'ctg1_3':p['B'],'ctg1_4':p['B'],'ctg1_5':p['E']}
    fixture=tmp_path/'inputs';fixture.mkdir()
    lines=['strain\tgenus\tblock\tgene_context']
    for s,pp in [('S1',prots),('S0',{'ctg1_1':p['A']})]:
        cds=[dict(locus_tag=t,aa_length=len(seq),gene_kind='biosynthetic',gene_functions='biosynthetic (rule-based-clusters) T1PKS: PKS_KS') for t,seq in pp.items()]
        (fixture/f'{s}_gene_context.jsonl').write_text(json.dumps({'cds':cds})+'\n')
        (fixture/f'{s}_proteins.faa').write_text(''.join(f'>{t}\n{seq}\n' for t,seq in pp.items()))
        lines.append(f'{s}\tStreptomyces\tSynthetic\t{s}_gene_context.jsonl')
    (fixture/'genomes.tsv').write_text('\n'.join(lines)+'\n')
    rows=[]
    for g,src,vals,n in [('ctg1_1','a.csv',[90,86],100),('ctg1_2','old.csv',[100,90],200),('ctg1_2','decoy.csv',[99],150),('ctg1_5','fallback.csv',[60],101)]:
        rows += [dict(strain='S1',gene=g,source_file=src,pct_identity=v,aa_length=n,hit_rank=i) for i,v in enumerate(vals,1)]
    rows.append(dict(strain='S0',gene='ctg1_1',source_file='missing.csv',pct_identity=99,aa_length=150))
    # Exercise disk rank recovery before re-keying onto both copies of protein B.
    (fixture/'old.csv').write_text('strain,gene,hit_rank,pct_identity,aa_length\nS1,ctg1_2,1,100,200\nS1,ctg1_2,2,90,200\n')
    rows=[r for r in rows if r['source_file']!='old.csv' or r['hit_rank']==1]
    store(fixture/'snapshot.sqlite',rows)
    with (fixture/'index.tsv').open('w') as f:
        f.write('strain\tgene\tsource_file\tprotein_sha256\tquery_aa_length\tbinding_evidence\n')
        for g,src,aa in [('ctg1_1','a.csv',p['A']),('ctg1_2','old.csv',p['B']),('ctg1_2','decoy.csv',p['D'])]:
            f.write(f'S1\t{g}\t{src}\t{protein_sha256(aa)}\t{len(aa)}\tledger_sha\n')
    return fixture

# Capture actual plotted coordinates and labels while still writing the real PNG and PDF.
PROBE='''import importlib.util,json,sys
from pathlib import Path
from matplotlib.figure import Figure
spec=importlib.util.spec_from_file_location('renderer',sys.argv[1]);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
real=Figure.savefig
capture={}
def save(self,path,*args,**kwargs):
 if str(path).endswith('.png'):
  capture[Path(path).stem]=[{'points':[c.get_offsets().tolist() for c in ax.collections], 'lines':[line.get_xydata().tolist() for line in ax.lines], 'title':ax.get_title(loc='left'), 'ticks':[t.get_text() for t in ax.get_xticklabels()]} for ax in self.axes]
 return real(self,path,*args,**kwargs)
Figure.savefig=save
m.main(sys.argv[3:])
Path(sys.argv[2]).write_text(json.dumps(capture,sort_keys=True))
'''

def run(fixture,out,seed,extra=()):
    args=['--genomes',str(fixture/'genomes.tsv'),'--store',str(fixture/'snapshot.sqlite'),'--root',str(fixture),'--out',str(out),'--query-index',str(fixture/'index.tsv'),'--omit-class','RiPP','--omit-class','Terpene','--omit-class','Other',*extra]
    subprocess.run([sys.executable,'-c',PROBE,str(SOURCE),str(out.parent/(out.name+'_artists.json')),*args],check=True,capture_output=True,text=True,env=dict(os.environ,PYTHONHASHSEED=str(seed),PYTHONDONTWRITEBYTECODE='1'))

def table(path):
    return list(csv.DictReader((l for l in path.read_text().splitlines() if not l.startswith('#')),delimiter='\t'))

def test_joint_binding_medians_and_actual_artists_across_processes(world,tmp_path):
    outputs=[]
    for seed in (0,1,42):
        out=tmp_path/f'seed{seed}';run(world,out,seed);outputs.append(out)
    for out in outputs:
        genes={r['gene']:r for r in table(out/'GENE_VALUES.tsv')}
        assert set(genes)=={'ctg1_1','ctg1_3','ctg1_4','ctg1_5'}
        assert genes['ctg1_3']['source_file']==genes['ctg1_4']['source_file']=='old.csv'
        assert genes['ctg1_3']['top10_mean_identity']=='95.00'
        assert genes['ctg1_3']['ranks_from_disk']==genes['ctg1_4']['ranks_from_disk']=='yes'
        assert genes['ctg1_3']['hits_used']==genes['ctg1_4']['hits_used']=='2'
        assert genes['ctg1_1']['top10_mean_identity']=='88.00'
        rows={r['strain']:r for r in table(out/'BLASTP_IDENTITY_BY_GENOME_numbers.tsv')}
        assert (rows['S1']['genes_with_hit'],rows['S1']['genes_in_regions'],rows['S1']['median'])==('4','5','91.5')
        assert (rows['S0']['genes_with_hit'],rows['S0']['genes_in_regions'],rows['S0']['median'])==('0','1','')
        assert '4 of 6 region genes in 2 genomes; median 91.5%' in (out/'BLASTP_IDENTITY_BY_GENOME_numbers.tsv').read_text()
        rows={(r['bgc_class'],r['strain']):r for r in table(out/'BLASTP_IDENTITY_BY_CLASS_numbers.tsv')}
        assert rows['PKS','S1']['median']=='91.5' and rows['PKS','S0']['core_genes']=='1'
        assert len(rows)==10  # omitted classes retained in the table
        info=json.loads((out/'RUN_INFO.json').read_text())
        assert info['results_binding']['S1']=={'sha':2,'unbound_sha_not_in_genome':1,'length':1}
        assert info['results_unbound']==2 and info['genomes_without_values']==['S0']
        artists=json.loads((out.parent/(out.name+'_artists.json')).read_text())
        assert 'median 91.5%' in artists['BLASTP_IDENTITY_BY_CLASS'][0]['title']
        assert any([xy[1] for xy in line]==[91.5,91.5] for line in artists['BLASTP_IDENTITY_BY_GENOME'][0]['lines'])
        assert sum(len(p) for a in artists['BLASTP_IDENTITY_BY_GENOME'] for p in a['points'])==4
    for filename in ['GENE_VALUES.tsv','BLASTP_IDENTITY_BY_GENOME_numbers.tsv','BLASTP_IDENTITY_BY_CLASS_numbers.tsv']:
        assert len({(p/filename).read_bytes() for p in outputs})==1
    assert len({(p.parent/(p.name+'_artists.json')).read_bytes() for p in outputs})==1
    from PIL import Image
    for name in ['BLASTP_IDENTITY_BY_GENOME.png','BLASTP_IDENTITY_BY_CLASS.png']:
        pixels=[]
        for out in outputs:
            with Image.open(out/name) as im: pixels.append((im.size,im.tobytes()))
        assert pixels[0]==pixels[1]==pixels[2]
    # Retain just this reusable synthetic fixture and one render when the validation runner requests it.
    if os.environ.get('BLASTP_VALIDATION_OUT'):
        import shutil
        dest=Path(os.environ['BLASTP_VALIDATION_OUT']);dest.mkdir(parents=True,exist_ok=True)
        shutil.copytree(world,dest/'inputs',dirs_exist_ok=True)
        shutil.copytree(outputs[0],dest/'render',dirs_exist_ok=True)
        shutil.copy2(outputs[0].parent/'seed0_artists.json',dest/'artists.json')


def test_query_lengths_do_not_leak_between_snapshot_calls(tmp_path):
    m=tool();region={'S1':{'ctg1_1'}};index={'S1':({}, {'ctg1_1':100})}
    for i,n in enumerate((100,200,None)):
        snap=tmp_path/f'{i}.sqlite';store(snap,[dict(strain='S1',gene='ctg1_1',source_file='same.csv',pct_identity=88,aa_length=n)])
        counts={};values=m.gene_values(snap,tmp_path,region,index=index,binding_counts=counts)
        assert bool(values)==(i==0)
        assert counts['S1']==[{ 'length':1},{'unbound_length_differs':1},{'unbound_no_sha_no_length':1}][i]


def test_sort_uses_true_median_and_keeps_empty_genome():
    m=tool();genomes=[dict(strain=s,genus='Streptomyces',block='X') for s in ['upper','true','empty']]
    assert m._order(genomes,{'upper':[10,100],'true':[60,60],'empty':[]})==[('X',['true','upper','empty'])]


def test_all_unbound_retains_rows_and_writes_figures(world,tmp_path):
    # Strong index hashes absent from this genome must not degrade to a length match.
    with (world/'index.tsv').open('a') as f:
        f.write('S1\tctg1_5\tfallback.csv\t'+'0'*64+'\t100\tledger_sha\n')
    text=(world/'index.tsv').read_text()
    for r in table(world/'index.tsv'):
        if r['protein_sha256']: text=text.replace(r['protein_sha256'],'0'*64)
    (world/'index.tsv').write_text(text)
    out=tmp_path/'empty';run(world,out,0)
    assert table(out/'GENE_VALUES.tsv')==[]
    rows=table(out/'BLASTP_IDENTITY_BY_GENOME_numbers.tsv')
    assert len(rows)==2 and all(r['genes_with_hit']=='0' and r['median']=='' for r in rows)
    assert json.loads((out/'RUN_INFO.json').read_text())['results_unbound']==5
    artists=json.loads((tmp_path/'empty_artists.json').read_text())
    assert all('median unavailable' in a['title'] for a in artists['BLASTP_IDENTITY_BY_CLASS'])
