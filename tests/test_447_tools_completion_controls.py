"""Synthetic negative, boundary, oracle and filesystem ownership controls for audit repairs."""
import csv
import importlib.util
import itertools
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location('completion_' + name, ROOT / 'tools' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('weights', [
    [[.9,.8],[.8,0]], [[.9],[.8],[.7]], [[.9,.9,.1]], [[0,0],[0,0]],
    [[.3,.7,.9],[.8,.1,.5],[.4,.8,.2]], [[.1,.2],[.3,.4],[.8,.6]],
])
def test_one_to_one_matches_bruteforce_oracle(weights):
    tool = load('cluster_relate')
    size = max(len(weights), len(weights[0]))
    padded = [row + [0] * (size-len(row)) for row in weights] + [[0]*size for _ in range(size-len(weights))]
    expected = max(sum(row[col] for row,col in zip(padded, permutation))
                   for permutation in itertools.permutations(range(size)))
    matches = tool._maximum_weight_matching(weights)
    assert sum(w for _,_,w in matches) == pytest.approx(expected)
    assert len({r for r,_,_ in matches}) == len(matches)
    assert len({c for _,c,_ in matches}) == len(matches)


def test_one_to_one_copy_denominator_permutation_engine_and_empty(monkeypatch):
    tool = load('cluster_relate')
    monkeypatch.setattr(tool, '_genes', lambda path: {'a':['MKTAYIAK']*3, 'b':['MKTAYIAK'], 'c':[]}[path])
    for engine in ('pyswrd', 'biopython'):
        _, dist, sim, detail = tool.pairwise_distances(['a','b'], ['a','b'], metric='one_to_one_v1', engine=engine)
        assert sim[0][1] == .3333 and dist[0][1] == .6667
        assert detail[(0,1)] == (1,100.0)
        assert tool.pairwise_distances(['b','a'], ['b','a'], metric='one_to_one_v1', engine=engine)[1] == dist
    with pytest.raises(ValueError, match='nonempty'):
        tool.pairwise_distances(['a','c'], ['a','c'], metric='one_to_one_v1')


@pytest.mark.parametrize('strand', [-1, 1])
def test_extraction_coordinate_conversion_and_terminal_slice(tmp_path, monkeypatch, strand):
    tool = load('extract_cluster')
    genome = tmp_path/'genome.fna'
    genome.write_text('>synthetic\n' + 'ATG'*33 + '\n')
    gene = SimpleNamespace(begin=1, end=99, strand=strand, translate=lambda:'M'*33+'*')
    fake = SimpleNamespace(GeneFinder=lambda **kw: SimpleNamespace(find_genes=lambda seq:[gene]))
    monkeypatch.setitem(sys.modules, 'pyrodigal', fake)
    proteins, sequences = tool.genecall(genome)
    assert proteins[0][2:5] == (0,99,strand)
    cluster = {'contig':'synthetic','gene_start':1,'gene_end':1,'hits':[(1,'marker',100,0)]}
    record, bounds = tool.extract_gbk(proteins, sequences, cluster, 'Synthetic', flank=0)
    assert bounds == (0,99)
    assert len(record.seq) == 99
    feature = record.features[0]
    assert (int(feature.location.start),int(feature.location.end),feature.location.strand) == (0,99,strand)
    assert len(feature.extract(record.seq)) == 99


@pytest.mark.parametrize('label', ['../escape', 'A/B', '.hidden', 'a\\b'])
def test_extract_rejects_output_names_before_gene_call(tmp_path, monkeypatch, label):
    tool = load('extract_cluster')
    monkeypatch.setattr(tool, 'run', lambda *a,**kw: pytest.fail('gene call before admission'))
    out = tmp_path/'out'
    with pytest.raises(SystemExit):
        tool.main(['--genome','missing','--marker','missing','--label',label,'--outdir',str(out)])
    assert not out.exists()


def screen_csv(path, rows):
    fields = ['strain_id','organism','screening_pattern','max_inhibition_raw','host','genus_16s']
    with path.open('w', newline='') as handle:
        writer=csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def test_screen_credible_survives_artifact_and_exports_agree(tmp_path):
    tool = load('bioassay_to_activity_channel')
    rows=[dict(strain_id='SYN1',organism='MRSA',screening_pattern='SUPPORTED_MULTI_CONCENTRATION_HIT',max_inhibition_raw='60'),
          dict(strain_id='SYN1',organism='MRSA',screening_pattern='ARTIFACT',max_inhibition_raw='90')]
    path=tmp_path/'screen.csv'
    results=[]
    for order in (rows, rows[::-1]):
        screen_csv(path,order)
        obj=tool.build(path)['SYN1']
        af=tool.build_af_dossier(path)[0]
        assert obj['metadata_state']=='MEASURED_POSITIVE'
        assert obj['assays'][0]['best_inhibition_pct']==60
        assert len(obj['assays'][0]['source_rows'])==2
        assert af['anti_MRSA']=='positive'
        results.append((obj,af))
    assert results[0]==results[1]


@pytest.mark.parametrize('tier,value,state', [('ARTIFACT','90','UNKNOWN'),('SUPPORTED_MULTI_CONCENTRATION_HIT','NaN','UNKNOWN'),('NO_50PCT_OBSERVATION','','UNKNOWN'),('NO_50PCT_OBSERVATION','0','NEGATIVE')])
def test_screen_unknown_is_not_negative(tmp_path,tier,value,state):
    tool=load('bioassay_to_activity_channel'); path=tmp_path/'screen.csv'
    screen_csv(path,[dict(strain_id='SYN1',organism='MRSA',screening_pattern=tier,max_inhibition_raw=value)])
    assert tool.build(path)['SYN1']['observation_state']==state
    assert tool.build_af_dossier(path)[0]['anti_MRSA']==state.lower()


@pytest.mark.parametrize('identities', [['SYN1','../bad'],['SYN1','syn1']])
def test_screen_whole_roster_admission_before_output(tmp_path,identities):
    tool=load('bioassay_to_activity_channel'); path=tmp_path/'screen.csv'; out=tmp_path/'out'
    screen_csv(path,[dict(strain_id=sid,organism='MRSA',screening_pattern='NO_50PCT_OBSERVATION',max_inhibition_raw='0') for sid in identities])
    with pytest.raises(SystemExit):
        tool.main(['--recon',str(path),'--out',str(out)])
    assert not out.exists()


def synthetic_gbk(path,tags,label):
    from Bio import SeqIO
    from Bio.Seq import Seq
    from Bio.SeqRecord import SeqRecord
    from Bio.SeqFeature import SeqFeature,FeatureLocation
    rec=SeqRecord(Seq('ATG'*500),id='syn',name='syn',description='synthetic')
    rec.annotations['molecule_type']='DNA'
    for i,tag in enumerate(tags):
        f=SeqFeature(FeatureLocation(i*90,i*90+90),type='CDS')
        f.qualifiers={'locus_tag':[tag],'translation':['MKTAYIAKQRQISFVKSHFSRQLEERLGLIE'],'gene':[label]}
        rec.features.append(f)
    SeqIO.write(rec,path,'genbank')


def test_homology_retains_paralogs_and_conflicting_original_annotations(tmp_path):
    tool=load('cluster_gene_compare')
    a,b=tmp_path/'A.gbk',tmp_path/'B.gbk'
    synthetic_gbk(a,['copy1','copy2'],'curatedA');synthetic_gbk(b,['copy3'],'curatedB')
    original=[a.read_bytes(),b.read_bytes()]
    labels=['A','B']
    clusters,recs,pairs,groups,resolved=tool.compare(labels,[a,b])
    assert len(groups)==1 and len(next(iter(groups.values())))==3
    assert set(resolved.values())=={'CONFLICT: curatedA | curatedB'}
    tool.write_annotated_gbks(labels,[a,b],clusters,recs,resolved,tmp_path)
    tool.write_csvs(labels,clusters,pairs,groups,resolved,tmp_path)
    from Bio import SeqIO
    result=SeqIO.read(tmp_path/'annotated_gbks'/'A.gbk','genbank')
    assert [f.qualifiers['gene'] for f in result.features]==[['curatedA'],['curatedA']]
    assert all('orthology_not_established' in f.qualifiers['mamey_homology_meta'][0] for f in result.features)
    matrix=list(csv.DictReader((tmp_path/'homology_matrix.csv').open()))
    assert json.loads(matrix[0]['A'])==['copy1','copy2']
    members=list(csv.DictReader((tmp_path/'homology_members.csv').open()))
    assert len(members)==3
    assert (tmp_path/'homology_matrix.csv').read_bytes()==(tmp_path/'ortholog_matrix.csv').read_bytes()
    assert [a.read_bytes(),b.read_bytes()]==original


def test_exact_accession_selection_not_prefix_or_versionless():
    tool=load('fetch_reference_cluster'); conn=sqlite3.connect(':memory:')
    conn.execute('CREATE TABLE gbk (id INTEGER,path TEXT)')
    conn.executemany('INSERT INTO gbk VALUES (?,?)',[(1,'/refs/BGC0000001.gbk'),(2,'/refs/BGC00000010.gbk'),(3,'/refs/NC_123456.11.gbk'),(4,'/refs/NC_123456.1.gbk')])
    assert tool.select_gbk(conn,'BGC0000001')[0]==1
    assert tool.select_gbk(conn,'NC_123456.1')[0]==4
    for text in ('BGC1','NC_123456','NC_123'):
        with pytest.raises(ValueError): tool.select_gbk(conn,text)


def test_archive_predictable_sibling_is_never_opened_or_removed(tmp_path):
    tool=load('finalize_public_archive')
    stage=tmp_path/'stage';stage.mkdir();(stage/'data.txt').write_text('data')
    foreign=tmp_path/'.result.zip.archtxn.tmp';foreign.write_text('foreign')
    result=tool.finalize_archive(stage,tmp_path,'result.zip')
    assert result.status=='COMMITTED' and foreign.read_text()=='foreign'
    assert not list(tmp_path.glob('.archtxn-*'))


def test_archive_traversal_error_refuses_before_write(tmp_path,monkeypatch):
    tool=load('finalize_public_archive')
    stage=tmp_path/'stage';stage.mkdir()
    monkeypatch.setattr(tool,'capability_probe',lambda *_:None)
    def broken_walk(path,**kwargs):
        kwargs['onerror'](PermissionError('synthetic unreadable subtree'))
        return iter(())
    monkeypatch.setattr(tool.os,'walk',broken_walk)
    with pytest.raises(tool.ArchiveTransactionError,match='stage_traversal_unverified'):
        tool.finalize_archive(stage,tmp_path,'result.zip')
    assert not (tmp_path/'result.zip').exists()


def test_archive_postcommit_error_reports_existing_archive(tmp_path,monkeypatch,capsys):
    tool=load('finalize_public_archive');stage=tmp_path/'stage';stage.mkdir();(stage/'data').write_text('x')
    original=tool._sha_path
    def fail_final(path):
        if Path(path).name=='result.zip': raise OSError('synthetic postcommit hash read failure')
        return original(path)
    monkeypatch.setattr(tool,'_sha_path',fail_final)
    rc=tool._main(['--stage-root',str(stage),'--output-dir',str(tmp_path),'--archive-name','result.zip'])
    output=capsys.readouterr()
    assert rc!=0 and (tmp_path/'result.zip').is_file()
    receipt=json.loads(output.out)
    assert receipt['status']=='COMMITTED_HOLD' and receipt['committed'] is True
    assert receipt['archive_path']==str(tmp_path/'result.zip')


def test_verified_pair_sidecar_race_never_deletes_foreign_or_committed_archive(tmp_path,monkeypatch):
    tool=load('publish_verified_pair');src=tmp_path/'src';src.mkdir();out=tmp_path/'out';out.mkdir()
    archive=src/'code.tar.gz';sidecar=src/'code.tar.gz.sha256';archive.write_bytes(b'archive');sidecar.write_bytes(b'sidecar')
    link=tool.os.link
    def racing_link(source,target):
        if str(target).endswith('.sha256'): Path(target).write_bytes(b'foreign')
        link(source,target)
    monkeypatch.setattr(tool.os,'link',racing_link)
    result=tool.publish_pair(archive,sidecar,out,tool.sha(archive),tool.sha(sidecar))
    assert result['status']=='COMMITTED_HOLD'
    assert (out/archive.name).read_bytes()==b'archive'
    assert (out/sidecar.name).read_bytes()==b'foreign'
    assert not list(out.glob('.verified-pair-*'))


def test_verified_pair_mutated_source_refuses_before_output(tmp_path):
    tool=load('publish_verified_pair');a=tmp_path/'code.tar.gz';b=tmp_path/'code.tar.gz.sha256'
    a.write_bytes(b'a');b.write_bytes(b'b');digest=tool.sha(a);a.write_bytes(b'changed')
    with pytest.raises(ValueError,match='changed'):
        tool.publish_pair(a,b,tmp_path/'out',digest,tool.sha(b))
    assert not (tmp_path/'out'/a.name).exists()


def test_screen_actual_cli_exports_and_manifest_binding(tmp_path):
    tool=load('bioassay_to_activity_channel'); path=tmp_path/'screen.csv';out=tmp_path/'out';af=tmp_path/'dossier.csv'
    screen_csv(path,[dict(strain_id='SYN1',organism='MRSA',screening_pattern='SUPPORTED_MULTI_CONCENTRATION_HIT',max_inhibition_raw='60')])
    tool.main(['--recon',str(path),'--out',str(out),'--af-dossier-csv',str(af)])
    obj=json.loads((out/'SYN1_bioactivity_metadata.json').read_text())
    from mamey.bioactivity_metadata import normalize_bioactivity
    normalize_bioactivity(obj)
    assert list(csv.DictReader(af.open()))[0]['anti_MRSA']=='positive'
    import hashlib
    assert json.loads((out/'MANIFEST.json').read_text())['source_sha256']==hashlib.sha256(path.read_bytes()).hexdigest()


def test_screen_bad_header_does_not_certify_empty_input(tmp_path):
    tool=load('bioassay_to_activity_channel');path=tmp_path/'bad.csv';path.write_text('wrong,fields\na,b\n')
    with pytest.raises(ValueError,match='required evidence columns'):tool.build(path)
