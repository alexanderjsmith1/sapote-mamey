"""Tiny synthetic databases exercise real external readers without copying data.
Run: python test_integration.py --config <pinned-reader-config.json>
"""
import argparse,copy,hashlib,importlib.util,json,sqlite3,tempfile,zlib
from pathlib import Path
spec=importlib.util.spec_from_file_location('atlas',Path(__file__).with_name('build_atlas.py'));a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
def fixture(root,source):
 pins={k:v for k,v in source['inputs'].items() if k in ('domain_adapter','domain_owner','identity_owner','gly_reader')}
 def pin(k,p):pins[k]={'path':str(p),'sha256':a.sha(p),'bytes':p.stat().st_size}
 identity='TEST / contig_one / region001 / cluster_one';protein='a'*64;member='b'*64;census='c'*64
 gp=root/'gly';gp.mkdir();db=gp/'model.sqlite';c=sqlite3.connect(db)
 c.executescript('create table metadata(key text,value text);create table locus(locus_key text,strain text,full_node text,region text,bgc_alias text,exact_identity text,source_member_sha256 text,source_fields_json text,classification_json text);')
 binding={'census_sha256':census};c.execute('insert into metadata values (?,?)',('binding',json.dumps(binding)));c.execute('insert into locus values (?,?,?,?,?,?,?,?,?)',('key','TEST','contig_one','region001','cluster_one',identity,member,'{}','{}'));c.commit();c.close();pin('gly_db',db)
 m=gp/'RELEASE_MANIFEST.json';m.write_text(json.dumps({'database':db.name,'database_sha256':a.sha(db),'bytes':db.stat().st_size,'binding':binding}));pin('gly_manifest',m)
 dp=root/'domain';dp.mkdir();db=dp/'domains.sqlite';c=sqlite3.connect(db)
 c.executescript('''create table metadata(key text,value text);create table section_profile(profile_sha256 text,contract_text text);create table section_relevance(section_number integer,requirement text);create table locus(locus_key text,strain text,full_node text,region text,bgc_alias text,exact_identity text,source_member text,source_member_sha256 text);create table gene(locus_key text,gene_order integer,locus_tag text,protein_sha256 text,cds_start integer,cds_end integer,strand integer,result_state text,source_qualifiers_zlib blob);create table feature(locus_key text,feature_order integer,explicit_gene_tags_json text,binding_state text,holds_json text,source_location text,source_qualifiers_zlib blob);''')
 contract=root/'contract.md';contract.write_text('Synthetic fixture contract\n');pin('current50_contract',contract)
 c.execute('insert into metadata values (?,?)',('census_sha256',census));c.execute('insert into section_profile values (?,?)',(a.sha(contract),contract.read_text()));c.executemany('insert into section_relevance values (?,?)',[(i,'Synthetic requirement') for i in range(1,51)])
 c.execute('insert into locus values (?,?,?,?,?,?,?,?)',('key','TEST','contig_one','region001','cluster_one',identity,'contig_one.region001.gbk',member))
 c.execute('insert into gene values (?,?,?,?,?,?,?,?,?)',('key',1,'gene_one',protein,0,300,1,'OBSERVED',zlib.compress(b'{}')))
 c.execute('insert into feature values (?,?,?,?,?,?,?)',('key',1,'["gene_one"]','SOURCE_SEQUENCE_AND_GEOMETRY_BOUND','[]','[0:300](+)',zlib.compress(json.dumps({'description':['O-methyltransferase domain'],'score':['50'],'evalue':['1e-10']}).encode())))
 c.commit();c.close();pin('domain_db',db);m=dp/'RELEASE_MANIFEST.json';m.write_text(json.dumps({'database':db.name,'database_sha256':a.sha(db),'bytes':db.stat().st_size}));pin('domain_manifest',m)
 for name in ('dictionary_base','dictionary_overlay'):
  p=root/(name+'.json');entries=[]
  if name.endswith('base'):entries=[{'accession':'TIGR00001','meaning':'Synthetic test definition','occurrences':[dict(strain='TEST',full_node='contig_one',region='region001',bgc_alias='cluster_one',exact_identity=identity,gene_order=1,protein_sha256=protein)]}]
  p.write_text(json.dumps({'entries':entries}));pin(name,p);m=root/(name+'_manifest.json');m.write_text(json.dumps({'files':[{'path':p.name,'sha256':a.sha(p)}]}));pin(name+'_manifest',m)
 return {'inputs':pins,'permitted_output_root':str(root)}
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--config',required=True);args=parser.parse_args();source=json.loads(Path(args.config).read_text());checks=[]
 with tempfile.TemporaryDirectory() as td:
  root=Path(td).resolve();cfg=fixture(root,source);d=a.build(cfg);assert len(d['records'])==1 and d['records'][0]['specificity']=='UNKNOWN_NOT_ADMITTED';assert d['loci']['key']['genes'][0]['start']==0;checks+=['full reader-backed fixture','boundary gene at zero preserved','no specificity escalation']
  bad=copy.deepcopy(cfg);bad['inputs']['domain_adapter']['sha256']='0'*64
  try:a.build(bad);raise AssertionError('dependency accepted')
  except ValueError as e:assert 'INPUT_HASH_CHANGED' in str(e)
  checks.append('changed reader dependency refused')
  gp=Path(cfg['inputs']['gly_manifest']['path']);gm=json.loads(gp.read_text());gm['binding']['census_sha256']='d'*64
  db=Path(cfg['inputs']['gly_db']['path']);c=sqlite3.connect(db);c.execute('update metadata set value=? where key=?',(json.dumps(gm['binding']),'binding'));c.commit();c.close();gm['database_sha256']=a.sha(db);gp.write_text(json.dumps(gm))
  for key,p in [('gly_db',db),('gly_manifest',gp)]:cfg['inputs'][key]['sha256']=a.sha(p)
  try:a.build(cfg);raise AssertionError('population accepted')
  except ValueError as e:assert 'POPULATION_CONFLICT' in str(e)
  checks.append('mixed population refused')
 print(json.dumps({'status':'PASS_GENERIC_READER_INTEGRATION','checks':checks},indent=2))
if __name__=='__main__':main()
