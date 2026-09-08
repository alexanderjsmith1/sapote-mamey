import hashlib,json,sqlite3,subprocess,sys,zlib,zipfile,shutil
from pathlib import Path
import pytest
from mamey import structured_domain_motif_extension as mod

def fixture(tmp_path):
 source=tmp_path/'sources';folder=source/'pkg'/'package';folder.mkdir(parents=True)
 archive=tmp_path/'source.zip'
 with zipfile.ZipFile(archive,'w') as z:z.writestr('results.json','{"fixture":true}')
 ph=hashlib.sha256(b'MAAA').hexdigest();identity=mod.exact_locus_display('TEST_STRAIN','contig_full_001','region001','BGC001')
 base=tmp_path/'base.sqlite';c=sqlite3.connect(base);c.executescript('''CREATE TABLE source(strain TEXT,source_sha256 TEXT,original_locator TEXT);CREATE TABLE locus(locus_key TEXT,strain TEXT,full_node TEXT,region TEXT,bgc_alias TEXT,exact_identity TEXT,source_member TEXT,source_member_sha256 TEXT,annotations_zlib BLOB);CREATE TABLE gene(locus_key TEXT,gene_order INTEGER,locus_tag TEXT,protein_sha256 TEXT,cds_start INTEGER,cds_end INTEGER,strand INTEGER);CREATE TABLE feature(locus_key TEXT,feature_order INTEGER,feature_type TEXT,source_qualifiers_zlib BLOB,parts_json TEXT,explicit_gene_tags_json TEXT,binding_state TEXT);CREATE TABLE section_profile(profile_sha256 TEXT,bundle_version TEXT,code_zip_sha256 TEXT,member TEXT,contract_text TEXT);CREATE TABLE section_relevance(section_number INTEGER,profile_sha256 TEXT,requirement TEXT,relation TEXT,limits TEXT);''')
 c.execute('INSERT INTO source VALUES(?,?,?)',('TEST_STRAIN',mod.sha(archive),str(archive)));a={'structured_comment':{'antiSMASH-Data':{'Orig. start':'0','Orig. end':'100'}}};c.execute('INSERT INTO locus VALUES(?,?,?,?,?,?,?,?,?)',('locus1','TEST_STRAIN','contig_full_001','region001','BGC001',identity,'source.gbk','a'*64,zlib.compress(json.dumps(a).encode())));c.execute('INSERT INTO gene VALUES(?,?,?,?,?,?,?)',('locus1',1,'gene1',ph,1,12,1));contract='Generic fifty-section fixture';profile=hashlib.sha256(contract.encode()).hexdigest();c.execute('INSERT INTO section_profile VALUES(?,?,?,?,?)',(profile,'TEST','b'*64,'contract.md',contract));c.executemany('INSERT INTO section_relevance VALUES(?,?,?,?,?)',[(n,profile,'Requirement '+str(n),'fixture','no science') for n in range(1,51)]);c.commit();c.close()
 manifest={'strain_id':'TEST_STRAIN','input_zip_sha256':mod.sha(archive),'bgcs':[{'bgc_id':'BGC001','contig':'contig_full_001','antismash_region':'region001','start':0,'end':100}]};(folder/'manifest.json').write_text(json.dumps(manifest));(folder/'TEST_gene_context.jsonl').write_text(json.dumps({'bgc_id':'BGC001','cds':[{'locus_tag':'gene1','start':1,'end':12,'strand':1}]}));(folder/'TEST_proteins.faa').write_text('>gene1 bgc=BGC001\nMAAA\n');(folder/'TEST_AntiSMASH_Evidence_Parse.json').write_text('{"json_mode":"off"}')
 x={'schema_version':'antismash_structured_tables_v2','counts':dict.fromkeys(mod.TABLES,0),**{t:[] for t in mod.TABLES}};x['hmm']=[{'row_id':'HMM1','bgc_id':'BGC001','mapping_status':'MAPPED','locus_tag':'gene1','domain_name':'fixture_domain','bitscore':12.3456789,'evalue':'2.3e-09'}];x['counts']['hmm']=1;(folder/'TEST_3_antismash_structured.json').write_text(json.dumps(x))
 row={'package':'pkg','manifest':'pkg/package/manifest.json','manifest_sha256':mod.sha(folder/'manifest.json'),'structured_path':'pkg/package/TEST_3_antismash_structured.json','structured_sha256':mod.sha(folder/'TEST_3_antismash_structured.json')};return source,base,row

def test_cli_import_resume_and_no_copy(tmp_path):
 source,base,row=fixture(tmp_path);inv=tmp_path/'inventory.json';inv.write_text(json.dumps([row]));out=tmp_path/'sidecar.sqlite';receipt=tmp_path/'receipt.json';cmd=[sys.executable,'-m','mamey.structured_domain_motif_extension','--inventory',str(inv),'--inventory-pin',mod.sha(inv),'--source-root',str(source),'--base',str(base),'--base-pin',mod.sha(base),'--out',str(out),'--allowed-root',str(tmp_path),'--receipt',str(receipt)]
 subprocess.run(cmd,check=True,capture_output=True,text=True);before=mod.sha(out);subprocess.run(cmd+['--resume'],check=True,capture_output=True,text=True);assert before==mod.sha(out);assert json.loads(receipt.read_text())['state']=='RESUME_COMPLETE_OUTPUT_UNCHANGED'
 c=mod.ro(out);assert c.execute('SELECT count(*) FROM observed_row').fetchone()[0]==1;assert c.execute('SELECT raw_zlib FROM observation').fetchone()[0] is None;assert not c.execute("SELECT 1 FROM sqlite_master WHERE name='gene'").fetchone();assert c.execute("SELECT evidence_state FROM observation").fetchone()[0]=='BOUND';c.close()

def test_resume_partial_and_changed_source(tmp_path):
 source,base,row=fixture(tmp_path);shutil.copytree(source/'pkg',source/'alternate');r2=dict(row,package='alternate',manifest='alternate/package/manifest.json',structured_path='alternate/package/TEST_3_antismash_structured.json');rows=mod.resolve_inventory(source,[row,r2]);out=tmp_path/'sidecar.sqlite';mod.build(rows,base,out,mod.sha(base),tmp_path,selection=['pkg']);mod.build(rows,base,out,mod.sha(base),tmp_path,resume=True);c=mod.ro(out);assert c.execute('SELECT count(*) FROM package').fetchone()[0]==2;assert c.execute('SELECT count(DISTINCT package_id) FROM observed_row').fetchone()[0]==2;c.close()
 (source/'pkg/package/TEST_proteins.faa').write_text('>gene1 bgc=BGC001\nMBBB\n')
 with pytest.raises(ValueError,match='RESUME_SOURCE_DRIFT'):mod.build(rows,base,out,mod.sha(base),tmp_path,resume=True)

def test_wrong_assembly_protein_geometry_and_count(tmp_path):
 source,base,row=fixture(tmp_path);rows=mod.resolve_inventory(source,[row]);bc=mod.ro(base);loci,sources=mod.base_index(bc);folder=source/'pkg/package'
 fp=folder/'TEST_proteins.faa';fp.write_text('>gene1 bgc=BGC001\nMBBB\n');_,ls,obs=mod.package_data(rows[0],loci,sources,{});assert obs[0]['state']=='UNBOUND' and 'GENE_PROTEIN_LINK_UNBOUND' in obs[0]['holds'];fp.write_text('>gene1 bgc=BGC001\nMAAA\n')
 mp=folder/'manifest.json';m=json.loads(mp.read_text());m['input_zip_sha256']='0'*64;m['bgcs'][0]['end']=99;mp.write_text(json.dumps(m));rows[0]['manifest_sha256']=mod.sha(mp);_,ls,obs=mod.package_data(rows[0],loci,sources,{});assert {'ASSEMBLY_SOURCE_HASH_UNBOUND_OR_CONFLICT','REGION_GEOMETRY_CONFLICT'}<=set(obs[0]['holds'])
 sp=Path(rows[0]['structured_path']);x=json.loads(sp.read_text());x['counts']['hmm']=2;sp.write_text(json.dumps(x))
 with pytest.raises(ValueError,match='TABLE_COUNT_OR_TYPE_HOLD'):mod.load_export(sp,mod.sha(sp))
 bc.close()

def test_callback_raw_precision_and_source_tamper(tmp_path):
 source,base,row=fixture(tmp_path);out=tmp_path/'sidecar.sqlite';mod.build(mod.resolve_inventory(source,[row]),base,out,mod.sha(base),tmp_path)
 d=mod.ro(out);b=mod.ro(base);m={'database':{'sha256':mod.sha(out)},'base_database_sha256':mod.sha(base)}
 with pytest.raises(mod.owner.ToolDatabaseInspectionError,match='GUARDED_READ_TRANSACTION_REQUIRED'):mod.inspect_verified_connections(d,b,m,package_root=source)
 for c in [d,b]:c.execute('PRAGMA query_only=ON');c.execute('BEGIN');c.execute('SELECT name FROM sqlite_master LIMIT 1').fetchall()
 got=mod.inspect_verified_connections(d,b,m,package_root=source);assert got['rows'][0]['raw']['bitscore']==12.3456789;assert got['rows'][0]['raw']['evalue']=='2.3e-09'
 sp=source/'pkg/package/TEST_3_antismash_structured.json';sp.write_text('{}')
 with pytest.raises(mod.owner.ToolDatabaseInspectionError,match='SOURCE_EXPORT_HASH_DRIFT'):mod.inspect_verified_connections(d,b,m,package_root=source)
 d.close();b.close()

def test_manifest_dependency_and_portable_locator_guards(tmp_path):
 source,base,row=fixture(tmp_path)
 with pytest.raises(mod.owner.ToolDatabaseInspectionError,match='UNSAFE_RELATIVE_LOCATOR'):mod.resolve_inventory(source,[dict(row,manifest='../outside')])
 with pytest.raises(ValueError,match='BASE_HASH_DRIFT'):mod.build(mod.resolve_inventory(source,[row]),base,tmp_path/'out.sqlite','0'*64,tmp_path)
 with pytest.raises(ValueError,match='OUTPUT_ROOT_DRIFT'):mod.build([],base,tmp_path.parent/'outside.sqlite',mod.sha(base),tmp_path)
