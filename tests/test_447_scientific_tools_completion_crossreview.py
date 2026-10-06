"""Synthetic independent repair acceptance; no external science/network runs."""
import csv
import importlib.util
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location('crossreview_' + name, ROOT/'tools'/(name+'.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def gbk(path, tag='copy', name='synthetic', translation='MKTAYIAK'):
    from Bio import SeqIO
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.SeqFeature import SeqFeature, FeatureLocation
    rec=SeqRecord(Seq('ATG'*20), id=name, name=name, description='synthetic fixture')
    rec.annotations['molecule_type']='DNA'
    f=SeqFeature(FeatureLocation(0,24,strand=1),type='CDS')
    f.qualifiers={'translation':[translation],'locus_tag':[tag],'gene':[name]}
    rec.features=[f]
    SeqIO.write(rec,path,'genbank')


def screen(path, rows):
    with path.open('w',newline='') as handle:
        w=csv.DictWriter(handle,fieldnames=['strain_id','organism','screening_pattern','max_inhibition_raw'])
        w.writeheader(); w.writerows(rows)


def test_matching_tied_optimum_details_identical_on_input_swap(monkeypatch):
    tool=load('cluster_relate')
    weights={('A','C'):0,('A','D'):0,('A','E'):50,('B','C'):50,('B','D'):0,('B','E'):100}
    monkeypatch.setattr(tool,'_gid',lambda al,a,b:weights[(a,b)])
    forward=tool._one_to_one_result(['A','B'],['C','D','E'],None,30)
    reverse=tool._one_to_one_result(['C','D','E'],['A','B'],None,30)
    assert forward==pytest.approx((2,.5,1/3,2/3))
    assert reverse==pytest.approx(forward)


def test_requested_pyswrd_fallback_effective_engine_truthful(tmp_path,monkeypatch):
    tool=load('cluster_relate')
    monkeypatch.setitem(sys.modules,'pyswrd',SimpleNamespace(search=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('synthetic unavailable'))))
    monkeypatch.setattr(tool,'_genes',lambda p:['MKTAYIAK'])
    def render(labels,dist,out,title):
        path=Path(out)/'dendrogram.png';path.write_bytes(b'synthetic render');return str(path)
    monkeypatch.setattr(tool,'make_dendrogram',render)
    out=tmp_path/'out'
    assert tool.main(['--gbk','A:a','--gbk','B:b','--engine','pyswrd','--outdir',str(out)])==0
    receipt=json.loads((out/'comparison_contract.json').read_text())
    assert receipt['requested_engine']=='pyswrd'
    assert receipt['effective_engine']=='biopython_global_all_pairs'


@pytest.mark.parametrize('name', ['cluster_relate','cluster_gene_compare'])
def test_render_failure_publishes_no_partial_cli_outputs(tmp_path,monkeypatch,name):
    tool=load(name);a=tmp_path/'a.gbk';b=tmp_path/'b.gbk';out=tmp_path/'out'
    gbk(a,name='a');gbk(b,name='b')
    def fail(*a,**kw): raise RuntimeError('synthetic renderer unavailable')
    monkeypatch.setattr(tool,'make_dendrogram' if name=='cluster_relate' else 'make_heatmap',fail)
    with pytest.raises(RuntimeError,match='renderer unavailable'):
        tool.main(['--gbk','A:'+str(a),'--gbk','B:'+str(b),'--outdir',str(out)])
    assert not out.exists() or not list(out.iterdir())


def test_screen_missing_dossier_parent_refuses_before_metadata(tmp_path):
    tool=load('bioassay_to_activity_channel');source=tmp_path/'screen.csv';out=tmp_path/'out'
    screen(source,[dict(strain_id='SYN',organism='target',screening_pattern='NO_50PCT_OBSERVATION',max_inhibition_raw='0')])
    with pytest.raises(SystemExit):
        tool.main(['--recon',str(source),'--out',str(out),'--af-dossier-csv',str(tmp_path/'missing'/'dossier.csv')])
    assert not out.exists()


def test_extraction_nan_hit_refused(monkeypatch):
    tool=load('extract_cluster')
    monkeypatch.setitem(sys.modules,'pyswrd',SimpleNamespace(search=lambda *a,**kw:[SimpleNamespace(query_index=0,target_index=0,result=SimpleNamespace(identity=float('nan')))]))
    with pytest.raises(ValueError,match='ALIGNMENT_UNVERIFIED'):
        tool.find_cluster([('syn',1,0,24,1,'MKTAYIAK')],[('marker','MKTAYIAK')])


def test_screen_blank_target_refused(tmp_path):
    tool=load('bioassay_to_activity_channel');source=tmp_path/'screen.csv'
    screen(source,[dict(strain_id='SYN',organism='target',screening_pattern='NO_50PCT_OBSERVATION',max_inhibition_raw='0'),
                   dict(strain_id='SYN',organism='',screening_pattern='ARTIFACT',max_inhibition_raw='90')])
    with pytest.raises(ValueError):tool.build(source)


def test_ncbi_returned_wrong_accession_refused(tmp_path,monkeypatch):
    tool=load('fetch_reference_cluster');source=tmp_path/'other.gbk'
    gbk(source,name='ZZ999999.1')
    monkeypatch.setattr(tool.urllib.request,'urlopen',lambda *a,**kw:io.BytesIO(source.read_bytes()))
    out=tmp_path/'refs'
    assert tool.main(['--ncbi','AA123456.1:requested','--outdir',str(out)])==2
    assert not out.exists()


def test_ncbi_exact_versioned_response_positive_control(tmp_path,monkeypatch):
    tool=load('fetch_reference_cluster');source=tmp_path/'exact.gbk'
    gbk(source,name='AA123456.1')
    monkeypatch.setattr(tool.urllib.request,'urlopen',lambda *a,**kw:io.BytesIO(source.read_bytes()))
    out=tmp_path/'refs'
    assert tool.main(['--ncbi','AA123456.1:requested','--outdir',str(out)])==0
    receipt=json.loads((out/'requested.reference_selection.json').read_text())
    assert receipt['references'][0]['selected_record_ids']==['AA123456.1']


def test_transitive_homology_control_explicit_conflict_and_permutation(tmp_path,monkeypatch):
    tool=load('cluster_gene_compare');paths={}
    for label in 'ABC':
        paths[label]=tmp_path/(label+'.gbk');gbk(paths[label],tag=label,name=label,translation=label)
    def identity(al,a,b): return (80 if set((a,b)) in ({'A','B'},{'B','C'}) else 10),100
    monkeypatch.setattr(tool,'global_identity',identity)
    for labels in (list('ABC'),list('CBA')):
        clusters,recs,pairs,groups,resolved=tool.compare(labels,[paths[x] for x in labels])
        assert len(groups)==1 and len(next(iter(groups.values())))==3
        assert set(resolved.values())=={'CONFLICT: A | B | C'}
        assert len(pairs)==2  # absent A-C pair is not manufactured


def test_screen_late_dossier_write_failure_leaves_no_published_set(tmp_path,monkeypatch):
    tool=load('bioassay_to_activity_channel');source=tmp_path/'screen.csv';out=tmp_path/'out';dossier=tmp_path/'dossier.csv'
    screen(source,[dict(strain_id='SYN',organism='target',screening_pattern='NO_50PCT_OBSERVATION',max_inhibition_raw='0')])
    from mamey import csv_safety
    original=csv_safety.SafeDictWriter.writerows
    writes=[]
    def fault(self,rows):
        rows=list(rows);original(self,rows[:1]);writes.extend(rows[:1])
        raise OSError('synthetic late dossier write failure')
    monkeypatch.setattr(csv_safety.SafeDictWriter,'writerows',fault)
    with pytest.raises((OSError,ValueError,SystemExit)):
        tool.main(['--recon',str(source),'--out',str(out),'--af-dossier-csv',str(dossier)])
    assert not out.exists() or not list(out.iterdir())
    assert not dossier.exists()
    assert len(writes)==1


def test_screen_late_publication_failure_rolls_back_owned_metadata_and_dossier(tmp_path,monkeypatch):
    tool=load('bioassay_to_activity_channel');source=tmp_path/'screen.csv';out=tmp_path/'out';dossier=tmp_path/'dossier.csv'
    screen(source,[dict(strain_id='SYN',organism='target',screening_pattern='NO_50PCT_OBSERVATION',max_inhibition_raw='0')])
    from mamey import output_transaction
    original=output_transaction.os.fsync
    calls=[]
    def fault(fd):
        calls.append(fd)
        if len(calls)==3:raise OSError('synthetic final dossier flush failure')
        return original(fd)
    monkeypatch.setattr(output_transaction.os,'fsync',fault)
    with pytest.raises(OSError,match='final dossier flush failure'):
        tool.main(['--recon',str(source),'--out',str(out),'--af-dossier-csv',str(dossier)])
    assert not out.exists() or not list(out.iterdir())
    assert not dossier.exists()
    assert len(calls)==3
