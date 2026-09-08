import pytest
from mamey.evidence_disagreements import compare_statements,matches

def statement(channel,text,resolution='source_named_hit_annotation',**kw):
    return dict(id=channel,channel=channel,statement=text,resolution=resolution,binding='BOUND',**kw)

def test_keywords_cannot_assert_biological_contradiction():
    a=statement('nr','kinase');b=statement('SwissProt','hydrolase')
    assert compare_statements([a,b])[0]['rule']=='TEXT_VARIATION_UNRESOLVED'
    b['resolution']='partial_domain_or_module'
    assert compare_statements([a,b])[0]['rule']=='DIFFERING_RESOLUTION'
    b['binding']='HELD'
    assert compare_statements([a,b])==[]

def test_explicit_opposition_requires_same_scope_and_source():
    a=statement('nr','source statement',assertion=dict(predicate='catalyzes',scope='assay1',term='reaction-X',polarity='positive',source='receipt-A'))
    b=statement('SwissProt','source counterstatement',assertion=dict(predicate='catalyzes',scope='assay1',term='reaction-X',polarity='negative',source='receipt-B'))
    assert compare_statements([a,b])[0]['rule']=='EXPLICIT_OPPOSED_STATEMENTS_REVIEW'
    b['assertion']['scope']='assay2'
    assert compare_statements([a,b])[0]['rule']=='TEXT_VARIATION_UNRESOLVED'

@pytest.mark.parametrize('key,value',[('protein_sha256','b'*64),('locus_tag','wrong'),('cds_start',2),('cds_end',500),('strand',-1),('assembly_source_sha256','wrong')])
def test_wrong_protein_geometry_and_boundary_are_unbound(key,value):
    g=dict(protein_sha256='a'*64,locus_tag='gene1',cds_start=1,cds_end=300,strand=1)
    b=dict(g);b[key]=value
    assert not matches(g,b)
    assert not matches(g,None)

def test_missing_hash_cannot_match():
    assert not matches({'protein_sha256':None},{'protein_sha256':None})

def fixture_view(root):
    import sqlite3,json,hashlib
    from tests.test_tool_database_reader import fixture_db,blastp_fixture,update_manifest,blastp_manifest
    from mamey.evidence_disagreements import ADAPTER
    root.mkdir(exist_ok=True)
    census=root/'census';fixture_db(census,rows=4);c=sqlite3.connect(census/'evidence.sqlite')
    for col,typ in [('source_member','TEXT'),('source_member_sha256','TEXT'),('cds_count','INTEGER')]:c.execute('ALTER TABLE locus ADD COLUMN '+col+' '+typ)
    c.execute('CREATE TABLE strain(strain TEXT,source_sha256 TEXT)');c.execute('INSERT INTO strain VALUES(?,?)',('TEST-1','e'*64))
    c.execute("UPDATE locus SET source_member='region.gbk',source_member_sha256=?,cds_count=4",('d'*64,))
    for n,q in enumerate(('a'*64,'b'*64,'c'*64,None)):
        c.execute('UPDATE gene SET protein_sha256=?,protein_length=200,cds_end=600,hold=NULL WHERE gene_order=?',(q,n))
    c.commit();c.close();update_manifest(census)
    cm=json.loads((census/'RELEASE_MANIFEST.json').read_text())
    sources={'census':{'root':'census','manifest':'RELEASE_MANIFEST.json'}}
    for name,adapter in ADAPTER.items():
        d=root/name;blastp_fixture(d,adapter);c=sqlite3.connect(d/'evidence.sqlite');c.execute('INSERT INTO metadata VALUES(?,?)',('census_sha256',cm['database_sha256']));c.execute('CREATE TABLE section_profile(profile_sha256 TEXT)');c.execute('ALTER TABLE binding ADD COLUMN assembly_source_sha256 TEXT');c.execute('UPDATE binding SET assembly_source_sha256=?',('e'*64,));c.commit();c.close();blastp_manifest(d,adapter)
        m=json.loads((d/'RELEASE_MANIFEST.json').read_text());m['census_sha256']=cm['database_sha256'];(d/'RELEASE_MANIFEST.json').write_text(json.dumps(m));sources[name]={'root':name,'manifest':'RELEASE_MANIFEST.json'}
    for name in ['domain','MIBiG']:
        d=root/name;d.mkdir();c=sqlite3.connect(d/'evidence.sqlite')
        c.executescript('CREATE TABLE gene(locus_key TEXT,gene_order INTEGER,locus_tag TEXT,protein_sha256 TEXT,cds_start INTEGER,cds_end INTEGER,strand INTEGER);CREATE TABLE locus(locus_key TEXT,exact_identity TEXT,source_member_sha256 TEXT);CREATE TABLE section_profile(profile_sha256 TEXT);CREATE TABLE metadata(key TEXT,value TEXT);')
        c.execute('INSERT INTO metadata VALUES(?,?)',('census_sha256',cm['database_sha256']))
        if name=='MIBiG':c.executescript('CREATE TABLE alignment(id INTEGER PRIMARY KEY,locus_key TEXT,gene_order INTEGER,file_id INTEGER);CREATE TABLE source_file(id INTEGER PRIMARY KEY,channel TEXT);')
        c.commit();c.close();db=d/'evidence.sqlite';m=dict(schema='antismash_reference_comparisons_candidate/1' if name=='MIBiG' else 'tool_database_release_manifest/1',database=db.name,database_sha256=hashlib.sha256(db.read_bytes()).hexdigest(),bytes=db.stat().st_size,census_sha256=cm['database_sha256']);(d/'RELEASE_MANIFEST.json').write_text(json.dumps(m));sources[name]={'root':name,'manifest':'RELEASE_MANIFEST.json'}
    for name,v in sources.items():v['manifest_sha256']=hashlib.sha256((root/v['root']/v['manifest']).read_bytes()).hexdigest()
    contract=root/'contract.md';contract.write_text('\n'.join('| '+str(n)+' | Generic fixture requirement '+str(n)+' |' for n in range(1,51)))
    config=dict(schema='mamey.disagreement-selection/1',population='Generic fixture population',sources=sources,contract={'path':contract.name,'sha256':hashlib.sha256(contract.read_bytes()).hexdigest()})
    selection=root/'selection.json';selection.write_text(json.dumps(config));return selection

def test_import_full_view_preserves_states_and_hold(tmp_path):
    from mamey.evidence_disagreements import Explorer
    selection=fixture_view(tmp_path)
    ex=Explorer(selection)
    try:
        assert ex.search()['total']==4
        g=ex.search()['rows'][0];d=ex.detail(g['id'])
        assert len(d['channels']['nr']['searches'])==2
        assert d['channels']['domain']['state']=='IDENTITY_OR_PROTEIN_BINDING_HOLD'
        assert d['channels']['MIBiG']['state']=='IDENTITY_OR_PROTEIN_BINDING_HOLD'
        assert d['gene']['channels']['nr']=='VERIFIED_MIXED_OUTCOMES'
        assert ex.search('no such gene')['rows']==[]
        with pytest.raises(ValueError):ex.detail('not-a-gene')
    finally:ex.close()

def test_mixed_population_refused(tmp_path):
    import json,hashlib
    from mamey.evidence_disagreements import Explorer
    selection=fixture_view(tmp_path);cfg=json.loads(selection.read_text());p=tmp_path/'nr/RELEASE_MANIFEST.json';m=json.loads(p.read_text());m['census_sha256']='f'*64;p.write_text(json.dumps(m));cfg['sources']['nr']['manifest_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();selection.write_text(json.dumps(cfg))
    with pytest.raises(ValueError,match='MIXED_POPULATION'):Explorer(selection)

def test_cli_real_fixture_audit(tmp_path):
    import os,subprocess,sys,json
    from pathlib import Path
    selection=fixture_view(tmp_path);out=tmp_path/'audit.json'
    r=subprocess.run([sys.executable,'tools/evidence_disagreements.py','--selection',str(selection),'--audit',str(out)],capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    assert r.returncode==0,r.stderr
    assert json.loads(out.read_text())['summary']['gene_occurrences']==4
