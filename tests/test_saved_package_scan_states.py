import csv, hashlib, json, sqlite3
from pathlib import Path
import pytest
try:
    import build_saved_scan_states as b
except ModuleNotFoundError:
    from tools import build_saved_scan_states as b

def fixture(root):
    root.mkdir();ident={'bgc_id':'BGC001','contig':'contig_complete_001','antismash_region':'region001','start':0,'end':900}
    m={'strain_id':'TEST-1','bundle_version':'9.7.412','workflow_version':'1.9.150','input_zip_sha256':'a'*64,'bgcs':[ident], 'bgc_crosswalk':[dict(ident)],'files':[], 'source_scans':{'concordance_per_bgc':{'BGC001':{'verdict':'NO_REFERENCE','reason':'source recorded only'}},'blda_tta':{'status':'NOT_APPLICABLE','per_bgc':{}},'rggmci':{'schema':'source_scan_channel_alias_v1','alias_of':'pairs.json'}}}
    (root/'pairs.json').write_text('{"ranked_pairs":[],"status":"NOT_RUN"}')
    (root/'TEST-1_proteins.faa').write_text('>gene1 bgc=BGC001\nMAAA\n')
    with (root/'TEST-1_gene_by_gene_all_bgcs.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['strain','contig','region','bgc_id','locus_tag','cds_start','cds_end','strand','aa_length','boundary_flag']);w.writerow(['TEST-1','contig_complete_001','region001','BGC001','gene1',1,12,'+',4,'INTERIOR'])
    for p in root.iterdir():m['files'].append({'path':p.name,'sha256':b.sha(p),'bytes':p.stat().st_size})
    (root/'manifest.json').write_text(json.dumps(m));return root

def edit(root,fn):
    p=root/'manifest.json';m=json.loads(p.read_text());fn(m);p.write_text(json.dumps(m))

def test_saved_states_and_hashes(tmp_path):
    p=fixture(tmp_path/'package');s=b.snapshot(p)
    assert s['genes']['BGC001'][0]['protein_sha256']==hashlib.sha256(b'MAAA').hexdigest()
    receipt=b.build([p],tmp_path/'out.sqlite');assert receipt['counts']['locus']==1
    c=sqlite3.connect(tmp_path/'out.sqlite')
    r=c.execute("select state,saved_status,evidence_index_state from signal where channel='concordance_per_bgc'").fetchone()
    assert r==('RECORDED_LOCUS_RESULT_NOT_ADMITTED','"NO_REFERENCE"','UNSUPPORTED_CHANNEL_NOT_COERCED')
    assert c.execute("select evidence_index_state from signal where channel='rggmci'").fetchone()[0]=='UNBOUND'
    assert c.execute('select exact_identity from locus').fetchone()[0]=='TEST-1 / contig_complete_001 / region001 / BGC001'

@pytest.mark.parametrize('kind',['alias_tamper','alias_traversal','alias_symlink','duplicate_alias','missing_identity','crosswalk','gene_tamper','missing_alias','duplicate_json','nonfinite'])
def test_negative_sources(tmp_path,kind):
    p=fixture(tmp_path/'package')
    if kind=='alias_tamper':(p/'pairs.json').write_text('{"ranked_pairs":[1]}')
    elif kind=='alias_traversal':edit(p,lambda m:m['source_scans']['rggmci'].update(alias_of='../outside.json'))
    elif kind=='alias_symlink':
        (tmp_path/'outside.json').write_text('{}');(p/'linked.json').symlink_to(tmp_path/'outside.json');edit(p,lambda m:m['source_scans']['rggmci'].update(alias_of='linked.json'))
    elif kind=='duplicate_alias':edit(p,lambda m:m['bgcs'].append(dict(m['bgcs'][0])))
    elif kind=='missing_identity':edit(p,lambda m:m['bgcs'][0].pop('contig'))
    elif kind=='crosswalk':edit(p,lambda m:m['bgc_crosswalk'][0].update(contig='foreign'))
    elif kind=='gene_tamper':(p/'TEST-1_proteins.faa').write_text('>gene1 bgc=BGC001\nMBBB\n')
    elif kind=='missing_alias':edit(p,lambda m:m['source_scans']['rggmci'].update(alias_of='missing.json'))
    elif kind=='duplicate_json':(p/'manifest.json').write_text('{"strain_id":"TEST-1","strain_id":"OTHER"}')
    elif kind=='nonfinite':(p/'manifest.json').write_text('{"value":NaN}')
    with pytest.raises((ValueError,FileNotFoundError)):b.snapshot(p)

def test_receipt_drift_is_typed_not_validation(tmp_path):
    p=fixture(tmp_path/'package');(p/'commit_receipt.json').write_text('{"status":"REFUSED"}')
    edit(p,lambda m:m['files'].append({'path':'commit_receipt.json','sha256':'0'*64,'bytes':1}))
    s=b.snapshot(p);assert s['integrity']['commit_receipt.json']=='SAVED_RECEIPT_MANIFEST_MISMATCH_HOLD_NOT_VALIDATION_AUTHORITY'

def test_missing_is_not_no_match():
    assert b.signal_value('concordance_per_bgc',None,'BGC001')[0]=='MISSING_CHANNEL_NOT_NEGATIVE'
    assert b.signal_value('concordance_per_bgc',{},'BGC001')[0]=='UNRECORDED_LOCUS_NOT_NEGATIVE'

def test_output_not_overwritten(tmp_path):
    p=tmp_path/'db';p.write_bytes(b'keep')
    with pytest.raises(ValueError,match='OUTPUT_ALREADY_EXISTS'):b.build([],p)
    assert p.read_bytes()==b'keep'

def manifest_for(root):
    db=root/'out.sqlite'
    m=dict(schema='tool_database_release_manifest/1',channel='current_package_scan_states',version='0.1.0',database=db.name,database_sha256=b.sha(db),bytes=db.stat().st_size)
    (root/'release.json').write_text(json.dumps(m));return b.sha(root/'release.json')

def test_governed_reader_and_index(tmp_path):
    from mamey import tool_database_reader as reader
    from mamey.mode_b.gene_first_explore import load_evidence_index
    p=fixture(tmp_path/'package');b.build([p],tmp_path/'out.sqlite');pin=manifest_for(tmp_path)
    identity=('TEST-1','contig_complete_001','region001','BGC001')
    r=reader.inspect_tool_database(tmp_path,'release.json',adapter='package-scan-states-v1',identity=identity,limit=100,expected_manifest_sha256=pin)
    assert len(r['results']['records'])==26
    rows=reader.saved_scan_evidence_index_rows(r);assert len(rows)==5 and all(x['evidence_state']=='UNBOUND' for x in rows)
    with (tmp_path/'index.tsv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),delimiter='\t');w.writeheader();w.writerows(rows)
    loaded,_=load_evidence_index(tmp_path/'index.tsv',dict(zip(('strain','full_node','region','bgc_alias'),identity)),{'gene1'})
    assert len(loaded)==5 and all(x['evidence_state']=='UNBOUND' for x in loaded)
    genes=reader.inspect_tool_database(tmp_path,'release.json',adapter='package-scan-genes-v1',identity=identity,expected_manifest_sha256=pin)
    assert len(genes['results']['records'])==1
    assert genes['results']['records'][0]['membership']=='INTERIOR'

@pytest.mark.parametrize('kind',['db_tamper','manifest_pin','false_bound','raw_tamper','identity_conflict','variant_metadata','bad_hash','missing_hash','sidecar','negative_offset'])
def test_reader_refusals(tmp_path,kind):
    from mamey import tool_database_reader as reader
    p=fixture(tmp_path/'package');b.build([p],tmp_path/'out.sqlite');pin=manifest_for(tmp_path)
    adapter='package-scan-states-v1';kw={}
    if kind=='db_tamper':
        with (tmp_path/'out.sqlite').open('ab') as f:f.write(b'x')
    elif kind=='manifest_pin':pin='0'*64
    elif kind=='sidecar':(tmp_path/'out.sqlite-wal').write_bytes(b'held')
    elif kind=='negative_offset':kw['offset']=-1
    else:
        c=sqlite3.connect(tmp_path/'out.sqlite')
        if kind=='false_bound':c.execute("update signal set evidence_index_state='BOUND' where channel='rggmci'")
        elif kind=='raw_tamper':c.execute("update signal set raw_sha256=?",('0'*64,))
        elif kind=='identity_conflict':c.execute("update locus set exact_identity='wrong'")
        elif kind=='variant_metadata':c.execute("update metadata set value='wrong' where key='channel'")
        elif kind=='bad_hash':c.execute("update gene set protein_sha256='invalid'");adapter='package-scan-genes-v1'
        elif kind=='missing_hash':c.execute("update gene set protein_sha256=NULL,state='PRESENT'");adapter='package-scan-genes-v1'
        c.commit();c.close();pin=manifest_for(tmp_path)
    with pytest.raises(reader.ToolDatabaseInspectionError):reader.inspect_tool_database(tmp_path,'release.json',adapter=adapter,identity=('TEST-1','contig_complete_001','region001','BGC001'),limit=100,expected_manifest_sha256=pin,**kw)

def test_variants_are_not_merged_and_pagination(tmp_path):
    from mamey import tool_database_reader as reader
    a=fixture(tmp_path/'a');c=fixture(tmp_path/'c');edit(c,lambda m:m.update(analysis_date='different source occurrence'))
    b.build([a,c],tmp_path/'out.sqlite');pin=manifest_for(tmp_path)
    r=reader.inspect_tool_database(tmp_path,'release.json',adapter='package-scan-states-v1',identity=('TEST-1','contig_complete_001','region001','BGC001'),limit=3,offset=25,expected_manifest_sha256=pin)['results']
    assert r['total_records']==52 and r['returned_records']==3 and r['next_offset']==28
    assert len(r['package_occurrences'])==2 and r['locus_query_state']=='MULTIPLE_PACKAGE_OCCURRENCES_NOT_MERGED'

def test_resume_reuses_and_refuses_changed_source(tmp_path):
    p=fixture(tmp_path/'package');out=tmp_path/'out.sqlite';r=b.build([p],out)
    resumed=b.build([p],out,resume=True)
    assert resumed['counts']==r['counts'] and resumed['packages'][0]['state']=='VERIFIED_COMMITTED_PARTITION_REUSED'
    (p/'TEST-1_proteins.faa').write_text('>gene1 bgc=BGC001\nMBBB\n')
    with pytest.raises(ValueError,match='RESUME_SOURCE_CHANGED_HOLD'):b.build([p],out,resume=True)

def test_resume_rejects_changed_population(tmp_path):
    p=fixture(tmp_path/'package');out=tmp_path/'out.sqlite';b.build([p],out)
    edit(p,lambda m:m.update(input_zip_sha256='b'*64))
    with pytest.raises(ValueError,match='RESUME_DEPENDENCY_OR_POPULATION_CHANGED_HOLD'):b.build([p],out,resume=True)

def test_wrong_dependency_refused(tmp_path):
    p=fixture(tmp_path/'package');dependency=tmp_path/'dependency.sqlite';dependency.write_bytes(b'wrong')
    with pytest.raises(ValueError,match='CENSUS_HASH_HOLD'):b.build([p],tmp_path/'out.sqlite',dependency,'0'*64)

def test_gene_boundary_and_length_holds_not_repaired(tmp_path):
    p=fixture(tmp_path/'package');q=p/'TEST-1_gene_by_gene_all_bgcs.csv';q.write_text(q.read_text().replace(',4,INTERIOR',',99,BOUNDARY_OVERLAP'))
    edit(p,lambda m:[row.update(sha256=b.sha(q),bytes=q.stat().st_size) for row in m['files'] if row['path']==q.name])
    s=b.snapshot(p);g=s['genes']['BGC001'][0]
    assert g['membership']=='BOUNDARY_OVERLAP' and g['state']=='PROTEIN_LENGTH_CONFLICT_HOLD'
