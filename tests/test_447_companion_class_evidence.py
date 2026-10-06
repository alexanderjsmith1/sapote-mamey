"""Synthetic/mocked tests; no real genomes, companion jobs, or network."""
import csv
import hashlib
import json
import subprocess
import zipfile
from dataclasses import fields, MISSING
from pathlib import Path
from types import SimpleNamespace
import pytest
pytest.importorskip("Bio")
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqRecord import SeqRecord
from Bio.SeqFeature import SeqFeature, FeatureLocation
import io
from mamey import gecco_crosscheck as G
from mamey import metabolomics_bridge as M
from mamey import nonks_second_proof as N
from mamey.companion_evidence import identity_text

@pytest.fixture
def fixture(tmp_path):
    package = tmp_path / 'package'; package.mkdir()
    contig = 'NODE_1_length_900_cov_7.0'
    record = SeqRecord(Seq('N' * 900), id=contig, name=contig, description='synthetic only')
    record.annotations['molecule_type'] = 'DNA'
    record.features = [SeqFeature(FeatureLocation(a,b,strand=1),type='CDS',qualifiers={'locus_tag':[pid],'translation':['M' * ((b-a)//3)]}) for a,b,pid in [(30,90,'g1'),(330,390,'g2'),(630,690,'g3')]]
    record2 = SeqRecord(Seq('N' * 900), id='NODE_2_length_900_cov_7.0', name='NODE_2', description='synthetic only')
    record2.annotations['molecule_type']='DNA'
    record2.features=[record.features.pop(1)]
    buf=io.StringIO(); SeqIO.write([record, record2],buf,'genbank'); raw=buf.getvalue().encode()
    archive=tmp_path/'source.zip'
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('source.gbk',raw)
        for source, num, start, end in ((record, 1, 0, 200), (record2, 2, 300, 500)):
            region = source[start:end]
            region.id = source.id; region.name = source.name
            region.annotations['molecule_type'] = 'DNA'
            region.annotations['structured_comment'] = {'antiSMASH-Data':{'Orig. start':str(start), 'Orig. end':str(end)}}
            region.features.insert(0, SeqFeature(FeatureLocation(0, end-start), type='region', qualifiers={'region_number':[str(num)]}))
            buffer=io.StringIO(); SeqIO.write([region],buffer,'genbank')
            z.writestr(f'{source.id}.region{num:03d}.gbk',buffer.getvalue())
    bgcs=[{'bgc_id':f'BGC{i:03d}','contig':contig if i==1 else 'NODE_2_length_900_cov_7.0','region_number':i,'antismash_region':f'region{i:03d}', 'start':start,'end':end,'products':[product],'source_gbk':f'{contig if i==1 else record2.id}.region{i:03d}.gbk','closest_mibig_accession':'BGCREF1' if i==1 else 'UNRESOLVED','source_kcb_file':'known.txt' if i==1 else 'UNRESOLVED','source_kcb_locator':'rank1' if i==1 else 'UNRESOLVED','ks_domain_count':0} for i,start,end,product in [(1,0,200,'NRPS'),(2,300,500,'RiPP')]]
    scans={'domain_architecture':{'per_bgc':{'BGC001':{'domain_counts':{'NRPS_A':1}},'BGC002':{'domain_counts':{'RiPP_precursor':1}}}},'mibig_per_gene':{'per_gene_mibig':{'BGC001':[{'query_gene':'g1','pct_identity':80,'mibig_accession':'BGCREF1','source_file':'known.txt'},{'query_gene':'g0','pct_identity':70,'mibig_accession':'BGCREF1','source_file':'known.txt'}]}},'pks_ks_scan':{}}
    manifest={'strain_id':'SYN-1','input_zip':'source.zip','input_zip_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'bgcs':bgcs,'source_scans':scans}
    (package/'manifest.json').write_text(json.dumps(manifest))
    rgg={'contig_a':contig,'contig_b':'NODE_2_length_900_cov_7.0','bgc_a':'BGC001','bgc_b':'BGC002','rggmci_confidence':'HIGH_RG_GMCI_RESCUE','functional_rescue_class':'COMPLEMENTARY','rggmci_score':'26'}
    with (package/'SYN-1_4A_RGGMCI_ranked_pairs.csv').open('w',newline='') as h:
        w=csv.DictWriter(h,fieldnames=list(rgg));w.writeheader();w.writerow(rgg)
    return SimpleNamespace(package=package, archive=archive, manifest=manifest, rgg=rgg, out=tmp_path/'output')

@pytest.fixture
def mocked_gecco(monkeypatch):
    monkeypatch.setattr(G.shutil,'which',lambda _: '/mock/gecco')
    calls=[]
    def fake(command, **kwargs):
        calls.append(command)
        if '--version' in command: return subprocess.CompletedProcess(command,0,'GECCO 0.11.0','')
        rawdir=Path(command[command.index('-o')+1]);rawdir.mkdir()
        (rawdir/'genome.genes.tsv').write_text('sequence_id\tprotein_id\tstart\tend\taverage_p\tmax_p\nNODE_1_length_900_cov_8\tg1\t31\t90\t0.9\t0.95\nNODE_2_length_900_cov_8\tg2\t331\t390\t0.1\t0.15\nNODE_1_length_900_cov_8\tg3\t631\t690\t0.8\t0.9\n')
        (rawdir/'genome.clusters.tsv').write_text('sequence_id\tcluster_id\tstart\tend\ttype\tmax_p\nNODE_1_length_900_cov_8\tc1\t31\t90\tNRP\t0.95\nNODE_1_length_900_cov_8\tc2\t631\t690\tUnknown\t0.9\n')
        return subprocess.CompletedProcess(command,0,'mocked completion','')
    monkeypatch.setattr(G.subprocess,'run',fake)
    return calls

def snapshot(package):
    return {str(p.relative_to(package)):hashlib.sha256(p.read_bytes()).hexdigest() for p in package.rglob('*') if p.is_file()}

def score(f, pos='CONSISTENT'):
    return {'strain':'SYN-1','identity_a':identity_text('SYN-1',f.manifest['bgcs'][0]),'identity_b':identity_text('SYN-1',f.manifest['bgcs'][1]),'layers_verdict':pos,'relative':'synthetic-relative','pair':'BGC001+BGC002'}

def test_gecco_overlap_only_and_gene_join(fixture,mocked_gecco):
    f=fixture; before=snapshot(f.package)
    gap=f.out.parent/'genes.csv';gap.write_text('query_gene\ng1\nunknown\n')
    rows=G.crosscheck(f.package,f.archive,f.out,gap_genes=[gap])
    assert rows[0]['gecco_clusters']==['c1'] and rows[1]['state']=='NO_OVERLAP_OBSERVED'
    assert len(list(f.out.glob('SYN-1_7_*.csv')))==3
    assert 'c2' in (f.out/'SYN-1_7_gecco_only_clusters.csv').read_text()
    joined=list(csv.DictReader((f.out/'genes_gecco.csv').open()))
    assert joined[0]['gecco_mean_p']=='0.9' and joined[1]['gecco_join_state']=='NO_SOURCE_LOCUS_TAG_MATCH'
    assert '--cds-feature' in mocked_gecco[-1] and '--force-tsv' in mocked_gecco[-1]
    assert snapshot(f.package)==before
    assert G.bound_support(f.package,f.out)[rows[0]['identity']]['gecco_clusters']==['c1']

def test_missing_gecco_typed_no_output(fixture,monkeypatch):
    monkeypatch.setattr(G.shutil,'which',lambda _:None)
    with pytest.raises(ValueError,match='NOT_INSTALLED'):G.crosscheck(fixture.package,fixture.archive,fixture.out)
    assert not fixture.out.exists()

@pytest.mark.parametrize('damage',['gene_missing','gene_coord','duplicate','probability','bad_version','no_clusters'])
def test_gecco_validation(fixture,mocked_gecco,monkeypatch,damage):
    old=G.subprocess.run
    def fake(command,**kw):
        result=old(command,**kw)
        if '--version' in command:
            return subprocess.CompletedProcess(command,0,'GECCO 0.10.3','') if damage=='bad_version' else result
        p=Path(command[command.index('-o')+1]); genes=p/'genome.genes.tsv'
        text=genes.read_text()
        if damage=='gene_missing': text='\n'.join(text.splitlines()[:-1])+'\n'
        if damage=='gene_coord':text=text.replace('\t31\t90','\t30\t90')
        if damage=='duplicate':text+='NODE_1_length_900_cov_8\tg1\t31\t90\t0.9\t0.95\n'
        if damage=='probability':text=text.replace('0.95','1.95')
        genes.write_text(text)
        if damage=='no_clusters':(p/'genome.clusters.tsv').write_text('sequence_id\tcluster_id\tstart\tend\ttype\tmax_p\n')
        return result
    monkeypatch.setattr(G.subprocess,'run',fake)
    if damage=='no_clusters':
        assert all(r['state']=='NO_OVERLAP_OBSERVED' for r in G.crosscheck(fixture.package,fixture.archive,fixture.out))
    else:
        with pytest.raises(ValueError):G.crosscheck(fixture.package,fixture.archive,fixture.out)
        assert not fixture.out.exists()

def test_gecco_subprocess_fail_no_published_artifact(fixture,mocked_gecco,monkeypatch):
    old=G.subprocess.run
    def fake(command,**kw):
        if '--version' in command:return old(command,**kw)
        raise subprocess.CalledProcessError(7,command)
    monkeypatch.setattr(G.subprocess,'run',fake)
    with pytest.raises(subprocess.CalledProcessError):G.crosscheck(fixture.package,fixture.archive,fixture.out)
    assert not fixture.out.exists()

def test_metabolomics_targets_and_exact_sources(fixture):
    f=fixture;before=snapshot(f.package)
    rows=M.export_metabolomics(f.package,f.out,f.archive)
    assert len(rows)==2 and all(r['claim_ceiling']==M.CAPACITY_CEILING for r in rows)
    assert rows[0]['median_pct_identity']==75 and rows[0]['close_match_74pct'] is True
    assert rows[1]['median_pct_identity'] is None and rows[1]['close_match_74pct'] is None
    assert rows[0]['npclassifier_pathways']==['Peptides']
    for ptr in json.loads((f.out/'nplinker/source_pointers.json').read_text()):
        assert hashlib.sha256((f.out/'nplinker'/ptr['staged_file']).read_bytes()).hexdigest()==ptr['source_sha256']
    assert json.loads((f.out/'podp_record_template.json').read_text())['ms_metadata'] is None
    assert snapshot(f.package)==before

@pytest.mark.parametrize('case',['product_only','tailoring_only','unknown_class','no_scans'])
def test_mapping_never_fabricates_class(fixture,case):
    f=fixture; scans=f.manifest['source_scans']
    scans['domain_architecture']['per_bgc']['BGC001']['domain_counts']={'Halogenase':1} if case=='tailoring_only' else {'Unknown':1} if case=='unknown_class' else {}
    if case=='no_scans':scans=None
    row=M.metabolomics_targets('SYN-1',f.manifest['bgcs'],scans)[0]
    assert row['biosynthetic_classes']==['unmapped'] and row['npclassifier_pathways']==['unmapped']

def test_manifest_field_populated_for_new_run(fixture):
    from mamey.models import MameyRun, RunContext, BGCRecord, AssemblyMetrics, SourceScanBundle
    scans=SourceScanBundle(**{f.name:{} for f in fields(SourceScanBundle) if f.default is MISSING and f.default_factory is MISSING})
    scans.domain_architecture=fixture.manifest['source_scans']['domain_architecture']
    bgcs=[BGCRecord(b['bgc_id'],b['contig'],b['region_number'],b['start'],b['end'],900) for b in fixture.manifest['bgcs']]
    ctx=RunContext('SYN-1','Synthetic','0','gold',str(fixture.archive),str(fixture.out))
    run=MameyRun(ctx,AssemblyMetrics(900,1,900,50,900),bgcs,{},scans)
    rows=run.to_dict()['metabolomics_targets']
    assert len(rows)==2 and rows[0]['biosynthetic_classes']==['NRPS']

@pytest.mark.parametrize('command',['gecco','metabolomics','nonks'])
def test_all_outputs_refuse_inside_symlink_and_existing(fixture,mocked_gecco,command):
    f=fixture
    fn=lambda out: G.crosscheck(f.package,f.archive,out) if command=='gecco' else M.export_metabolomics(f.package,out,f.archive) if command=='metabolomics' else N.recompute(f.package,out=out)
    with pytest.raises(ValueError,match='INSIDE_PACKAGE'):fn(f.package/'new')
    alias=f.out.parent/'alias';alias.symlink_to(f.package,target_is_directory=True)
    with pytest.raises(ValueError,match='INSIDE_PACKAGE'):fn(alias/'new')
    f.out.mkdir();(f.out/'stale').write_text('old')
    with pytest.raises(ValueError,match='OUTPUT_EXISTS'):fn(f.out)
    assert (f.out/'stale').read_text()=='old'

def test_bound_gecco_support_export_and_tamper(fixture,mocked_gecco):
    f=fixture;G.crosscheck(f.package,f.archive,f.out)
    rows=M.export_metabolomics(f.package,f.out.parent/'export',f.archive,f.out)
    assert rows[0]['gecco_support']['state']=='OVERLAP_OBSERVED'
    (f.out/'support.json').write_text('{}')
    with pytest.raises(ValueError,match='DIGEST_MISMATCH'):M.export_metabolomics(f.package,f.out.parent/'bad',f.archive,f.out)

@pytest.mark.parametrize('pos,expected',[('CONSISTENT','TWO_PROOF_RESCUE'),('APART_CLOSE','POSITION_VETO'),('CONFLICT','POSITION_VETO'),('APART_WEAK','RGGMCI_ONLY'),('NOT_READ','RGGMCI_ONLY')])
def test_nonks_explicit_position_policy(fixture,pos,expected):
    f=fixture; row={**f.rgg,'verdict':'RGGMCI_ONLY','ks_clade_id':''}
    result=N.apply_policy([row],f.manifest,[score(f,pos)],N.POSITION_POLICY)[0]
    assert result['verdict']==expected and result['rule_policy']==N.POSITION_POLICY
    assert result['identity_a']==score(f)['identity_a'] and 'SUPPORTING_ONLY' in result['kcb_role']
    assert N.apply_policy([row],f.manifest,[score(f,pos)])[0]['verdict']=='RGGMCI_ONLY'

@pytest.mark.parametrize('case',['moderate','no_logic','ks_present','unknown_class','no_relative','kcb_only'])
def test_nonks_no_unearned_promotion(fixture,case):
    f=fixture; row={**f.rgg,'verdict':'RGGMCI_ONLY','ks_clade_id':''}; sc=score(f)
    if case=='moderate':row['rggmci_confidence']='MODERATE_RG_GMCI_CANDIDATE'
    if case=='no_logic':row['verdict']='WEAK';row['functional_rescue_class']='ACCESSORY_ONLY'
    if case=='ks_present':f.manifest['bgcs'][0]['ks_domain_count']=1
    if case=='unknown_class':f.manifest['source_scans']['domain_architecture']={}
    if case=='no_relative':sc['relative']=''
    if case=='kcb_only':sc['layers_verdict']='NOT_READ';sc['kcb_complementary']='true'
    assert N.apply_policy([row],f.manifest,[sc],N.POSITION_POLICY)[0]['verdict']!='TWO_PROOF_RESCUE'

def test_scorecard_identity_duplicate_refusal(fixture):
    f=fixture;sc=score(f)
    with pytest.raises(ValueError,match='DUPLICATE'):N.position_index(f.manifest,[sc,sc])
    sc['identity_a']=sc['identity_a'].replace('region001','region009')
    with pytest.raises(ValueError,match='BINDING_MISMATCH'):N.position_index(f.manifest,[sc])

def test_nonks_command_receipt_and_interpretation(fixture):
    f=fixture;sc=score(f);path=f.out.parent/'score.tsv'
    with path.open('w',newline='') as h:
        w=csv.DictWriter(h,fieldnames=list(sc),delimiter='\t');w.writeheader();w.writerow(sc)
    rows=N.recompute(f.package,N.POSITION_POLICY,path,f.out)
    assert rows[0]['verdict']=='TWO_PROOF_RESCUE'
    rendered=list(csv.DictReader((f.out/'SYN-1_4D_two_proof_rescue.csv').open()))[0]
    assert 'position CONSISTENT' in rendered['interpretation'] and rendered['two_proof_logic_version']==N.POSITION_POLICY
    assert json.loads((f.out/'receipt.json').read_text())['scorecard_sha256']==hashlib.sha256(path.read_bytes()).hexdigest()

def test_cli_and_optional_registry():
    from mamey.cli import build_parser
    from mamey.companion_tools import load_registry
    p=build_parser()
    assert p.parse_args(['gecco-crosscheck','--package','p','--zip','z']).jobs==1
    assert p.parse_args(['export-metabolomics','--package','p']).out is None
    assert p.parse_args(['two-proof-rescue','--package','p']).policy==N.DEFAULT_POLICY
    reg={t.id:t for t in load_registry()}
    for tid in ['nplinker','prism','gnps_masst','sirius_canopus','deepbgc','bigslice']:
        assert reg[tid].requirement=='optional' and reg[tid].purpose and reg[tid].detection_command

@pytest.mark.parametrize('damage',['source_file','duplicate_gene','invalid_identity','no_source_locator'])
def test_reference_metric_requires_complete_unique_bound_rows(fixture,damage):
    f=fixture;mp=f.manifest['source_scans']['mibig_per_gene']['per_gene_mibig']['BGC001']
    if damage=='source_file':
        for r in mp:r['source_file']='foreign.txt'
    if damage=='duplicate_gene':mp.append(dict(mp[0]))
    if damage=='invalid_identity':mp[0]['pct_identity']=float('nan')
    if damage=='no_source_locator':f.manifest['bgcs'][0]['source_kcb_locator']='UNRESOLVED'
    row=M.metabolomics_targets('SYN-1',f.manifest['bgcs'],f.manifest['source_scans'])[0]
    assert row['median_pct_identity'] is None and row['close_match_74pct'] is None

@pytest.mark.parametrize('damage',['same_contig','whitespace_relative','false_logic','pkshybrid','mismatched_rgg'])
def test_nonks_binding_and_false_independent_proof(fixture,damage):
    f=fixture;row={**f.rgg,'verdict':'RGGMCI_ONLY','ks_clade_id':''};sc=score(f)
    if damage=='same_contig':
        f.manifest['bgcs'][1]['contig']=f.manifest['bgcs'][0]['contig'];row['contig_b']=row['contig_a'];sc=score(f)
    if damage=='whitespace_relative':sc['relative']=' '
    if damage=='false_logic':row['functional_rescue_class']='ACCESSORY_ONLY'
    if damage=='pkshybrid':f.manifest['bgcs'][0]['products']=['NRPS','T1PKS']
    if damage=='mismatched_rgg':
        row['contig_a']='NODE_9'
        with pytest.raises(ValueError,match='RGGMCI_LOCUS'):N.apply_policy([row],f.manifest,[sc],N.POSITION_POLICY)
        return
    assert N.apply_policy([row],f.manifest,[sc],N.POSITION_POLICY)[0]['verdict']!='TWO_PROOF_RESCUE'

def test_archive_digest_mismatch_no_export(fixture):
    fixture.archive.write_bytes(fixture.archive.read_bytes()+b'changed')
    with pytest.raises(ValueError,match='DIGEST_MISMATCH'):M.export_metabolomics(fixture.package,fixture.out,fixture.archive)
    assert not fixture.out.exists()

def test_gecco_support_other_package_bytes_refuse(fixture,mocked_gecco):
    f=fixture;G.crosscheck(f.package,f.archive,f.out)
    (f.package/'new_note').write_text('new package snapshot')
    with pytest.raises(ValueError,match='PACKAGE_BINDING'):G.bound_support(f.package,f.out)

@pytest.mark.parametrize('command',['gecco-crosscheck','export-metabolomics','two-proof-rescue'])
def test_cli_positional_alias_and_typed_refusal(fixture,command,monkeypatch):
    from mamey.cli import main
    f=fixture
    monkeypatch.setattr(G.shutil,'which',lambda _:None)
    if command=='gecco-crosscheck':args=[command,str(f.package),'--zip',str(f.archive)]
    elif command=='export-metabolomics':args=[command,str(f.package),'--out',str(f.package/'bad')]
    else:args=[command,str(f.package),'--out',str(f.package/'bad')]
    assert main(args)==2

def test_package_mutation_during_external_job_prevents_publication(fixture,mocked_gecco,monkeypatch):
    old=G.subprocess.run
    def fake(command,**kw):
        result=old(command,**kw)
        if 'run' in command:(fixture.package/'unexpected_note').write_text('changed')
        return result
    monkeypatch.setattr(G.subprocess,'run',fake)
    with pytest.raises(ValueError,match='PACKAGE_CHANGED'):G.crosscheck(fixture.package,fixture.archive,fixture.out)
    assert not fixture.out.exists()

@pytest.mark.parametrize('damage',['missing_member','duplicate_member','outside_region'])
def test_gecco_archive_admission(fixture,mocked_gecco,damage):
    f=fixture
    if damage=='outside_region':
        f.manifest['bgcs'][0]['end']=1000
        (f.package/'manifest.json').write_text(json.dumps(f.manifest))
        with pytest.raises(ValueError,match='NOT_IN_GENOME'):G.crosscheck(f.package,f.archive,f.out)
    else:
        with zipfile.ZipFile(f.archive,'a') as z:
            if damage=='duplicate_member':z.writestr('source.gbk',z.read('source.gbk'))
            else:z.writestr('additional.gbk',z.read('source.gbk'))
        f.manifest['input_zip_sha256']=hashlib.sha256(f.archive.read_bytes()).hexdigest()
        (f.package/'manifest.json').write_text(json.dumps(f.manifest))
        with pytest.raises(ValueError,match='AMBIGUOUS|DUPLICATE'):G.crosscheck(f.package,f.archive,f.out)
    assert not f.out.exists()

def test_coverage_suffix_normalization_never_collapses_distinct_contigs():
    from mamey.companion_evidence import unique_contigs
    with pytest.raises(ValueError,match='AMBIGUOUS_NORMALIZED'):unique_contigs(['NODE_1_length_900_cov_1','NODE_1_length_900_cov_2'])

def test_nonks_alternative_never_changes_default_join(fixture):
    from mamey.rescue_two_proof import two_proof_join
    f=fixture
    before=two_proof_join(f.package/'SYN-1_4A_RGGMCI_ranked_pairs.csv',{})[0]
    promoted=N.apply_policy(before,f.manifest,[score(f)],N.POSITION_POLICY)
    assert promoted[0]['verdict']=='TWO_PROOF_RESCUE'
    assert before[0]['verdict']=='RGGMCI_ONLY'
    after=N.apply_policy(before,f.manifest,policy=N.DEFAULT_POLICY)[0]
    assert after['verdict']=='RGGMCI_ONLY' and after['independent_proof_state']=='NOT_OBSERVED'
