"""Generic disposable fixtures. No biological example is an observed record."""
import contextlib,hashlib,importlib.util,json,sqlite3,sys,tempfile,unittest
from pathlib import Path
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
if (HERE/'cohort_next_evidence_actions.py').exists():sys.path.insert(0,str(HERE))
else:sys.path.insert(0,str(HERE.parent/'tools'))
from cohort_next_evidence_actions import View,digest

class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  # An intentionally tiny test double of the external existing reader interface.
  self.reader=self.root/'reader.py';self.reader.write_text("import sqlite3\ndef connect(p):\n c=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row;c.execute('PRAGMA query_only=ON');return c\n")
  self.identity=self.root/'identity.py';self.identity.write_text("def exact_locus_display(*p):\n if len(p)!=4 or any(not x or x=='unknown' for x in p):raise ValueError('identity hold')\n return ' / '.join(p)\n")
  self.contract=self.root/'contract.md';self.contract.write_text('Generic contract fixture\n');h=digest(self.contract)
  self.sha='a'*64;self.ident='FIXTURE / contig_complete_001 / region001 / fixture_alias';self.paths={}
  schema={
   'census':"CREATE TABLE metadata(key,value);CREATE TABLE strain(strain,selection_state,state);CREATE TABLE locus(locus_key PRIMARY KEY,exact_identity);CREATE TABLE gene(locus_key,gene_order,locus_tag,protein_sha256,protein_length,PRIMARY KEY(locus_key,gene_order));",
   'priority':"CREATE TABLE metadata(key,value);CREATE TABLE occurrence(query_sha256,locus_key,gene_order,locus_tag,exact_identity,protein_length,tier);CREATE TABLE channel_state(channel,query_sha256,state,PRIMARY KEY(channel,query_sha256));CREATE TABLE queue(channel,rank,query_sha256,tier,representative_identity,representative_gene,PRIMARY KEY(channel,rank));",
   'registry':"CREATE TABLE profile(profile_sha256,contract_text);CREATE TABLE section_relevance(section,profile_sha256,requirement);CREATE TABLE denominator_resolution(assertion_id,state,population,blocker,source_id);CREATE TABLE comparison_group(group_id,entity,attribute,blockers_json);CREATE TABLE comparison_member(group_id,assertion_id);",
   'wetlab':"CREATE TABLE metadata(key,value);CREATE TABLE section_profile(profile_sha256,contract_text);CREATE TABLE section_relevance(section_number,profile_sha256,requirement);CREATE TABLE source_record(record_id,strain,source_id,sheet,row_number);CREATE TABLE observation(record_id,observation_id,missing_metadata_json);CREATE TABLE source(source_id,path,sha256);"}
  for k,sql in schema.items():
   p=self.root/(k+'.sqlite');c=sqlite3.connect(p);c.executescript(sql);c.close();self.paths[k]=p
  self.run_sql('census','INSERT INTO metadata VALUES (?,?)',('selection_sha256','selection_A'))
  self.run_sql('census','INSERT INTO strain VALUES (?,?,?)',('FIXTURE','SELECTED','COMPLETE'))
  self.run_sql('census','INSERT INTO locus VALUES (?,?)',('locusA',self.ident))
  self.run_sql('census','INSERT INTO gene VALUES (?,?,?,?,?)',('locusA',1,'gene1',self.sha,100))
  self.run_sql('priority','INSERT INTO metadata VALUES (?,?)',('sources',json.dumps({'antismash_gene_census__v0.1.1__2026-09-07':{'sha256':digest(self.paths['census'])}})))
  self.run_sql('priority','INSERT INTO metadata VALUES (?,?)',('method','source core-first routing fixture'))
  self.run_sql('priority','INSERT INTO occurrence VALUES (?,?,?,?,?,?,?)',(self.sha,'locusA',1,'gene1',self.ident,100,0))
  for channel in ('nr','clustered_nr'):
   self.run_sql('priority','INSERT INTO channel_state VALUES (?,?,?)',(channel,self.sha,'NO_VERIFIED_SEARCH'))
   self.run_sql('priority','INSERT INTO queue VALUES (?,?,?,?,?,?)',(channel,1,self.sha,0,self.ident,'gene1'))
  self.run_sql('registry','INSERT INTO profile VALUES (?,?)',(h,self.contract.read_text()))
  self.run_sql('wetlab','INSERT INTO section_profile VALUES (?,?)',(h,self.contract.read_text()))
  self.run_sql('wetlab','INSERT INTO metadata VALUES (?,?)',('census_sha256',json.dumps(digest(self.paths['census']))))
  for n in range(1,51):
   self.run_sql('registry','INSERT INTO section_relevance VALUES (?,?,?)',(n,h,'Requirement '+str(n)))
   self.run_sql('wetlab','INSERT INTO section_relevance VALUES (?,?,?)',(n,h,'Requirement '+str(n)))
  self.paths.update(reader=self.reader,identity=self.identity,contract=self.contract)
  self.pin()
 def tearDown(self):self.tmp.cleanup()
 def run_sql(self,k,q,args=()):
  with contextlib.closing(sqlite3.connect(self.paths[k])) as c:
   c.execute(q,args);c.commit()
 def pin(self):
  self.manifest=self.root/'manifest.json';self.manifest.write_text(json.dumps({'schema':'next_evidence_actions/1','population':'fixture_selection_A_not_B','sources':{k:{'path':p.name,'sha256':digest(p),'bytes':p.stat().st_size} for k,p in self.paths.items()}}));self.pin_value=digest(self.manifest)
 def view(self):return View(self.root,self.manifest,self.pin_value)
 def test_channel_identity_and_pagination(self):
  v=self.view();self.assertEqual(v.counts['missing'],2);self.assertEqual(v.query()['total'],1);self.assertEqual(v.query(offset=1)['rows'],[])
  self.assertNotEqual(v.evidence('missing',self.sha,'nr')['channel'],v.evidence('missing',self.sha,'clustered_nr')['channel'])
 def test_tampered_source(self):
  self.reader.write_text(self.reader.read_text()+'\n# mutation');self.assertRaisesRegex(ValueError,'SOURCE_HASH',self.view)
 def test_changed_dependency_after_start(self):
  v=self.view();self.identity.write_text(self.identity.read_text()+'\n# mutation');self.assertRaisesRegex(ValueError,'SOURCE_CHANGED',v.query)
 def test_wrong_protein_repin_does_not_admit(self):
  self.run_sql('priority','UPDATE occurrence SET query_sha256=?',('b'*64,));self.pin();self.assertRaisesRegex(ValueError,'PROTEIN_BINDING',self.view)
 def test_wrong_assembly_repin_does_not_admit(self):
  self.run_sql('priority','UPDATE occurrence SET locus_key=?',('other_assembly',));self.pin();self.assertRaisesRegex(ValueError,'ASSEMBLY',self.view)
 def test_boundary_gene_cannot_join_by_hash(self):
  self.run_sql('priority','INSERT INTO occurrence VALUES (?,?,?,?,?,?,?)',(self.sha,'outside_region',2,'boundary_gene',self.ident,100,0));self.pin();self.assertRaisesRegex(ValueError,'BINDING',self.view)
 def test_mixed_population_dependency(self):
  self.run_sql('census','UPDATE metadata SET value=? WHERE key=?',('selection_B','selection_sha256'));self.pin();self.assertRaisesRegex(ValueError,'CENSUS_BINDING',self.view)
 def test_nohit_not_missing(self):
  self.run_sql('priority','UPDATE channel_state SET state=?',('VERIFIED_NO_HIT',));self.pin();self.assertRaisesRegex(ValueError,'QUEUE_STATE',self.view)
 def test_parse_failed_not_zero(self):
  self.paths['priority'].write_bytes(b'parse failed');self.pin();self.assertRaises(sqlite3.DatabaseError,self.view)
 def test_section_mismatch(self):
  self.run_sql('wetlab','UPDATE section_relevance SET requirement=? WHERE section_number=50',('wrong',));self.pin();self.assertRaisesRegex(ValueError,'EXACT50',self.view)
 def test_duplicate_occurrence(self):
  self.run_sql('priority','INSERT INTO occurrence SELECT * FROM occurrence');self.pin();self.assertRaisesRegex(ValueError,'BINDING',self.view)
 def test_unknown_and_unbound_states_remain_distinct(self):
  v=self.view();self.assertRaises(ValueError,v.evidence,'missing','b'*64);self.assertEqual(v.query(search='nothing')['total'],0)
  self.assertRaises(ValueError,v.query,channel='merged');self.assertRaises(ValueError,v.query,limit=101)
if __name__=='__main__':unittest.main(verbosity=2)
