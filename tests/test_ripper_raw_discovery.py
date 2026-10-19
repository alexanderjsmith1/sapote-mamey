"""Self-authored tiny SQLite/FASTA/stage fixtures; no upstream or HMM execution."""
import hashlib,importlib.util,json,os,sqlite3,tempfile,unittest
from pathlib import Path
from contextlib import closing
ROOT=Path(__file__).resolve().parents[1];sp=importlib.util.spec_from_file_location('raw_adapter',ROOT/'tools/ripper_adapter.py');a=importlib.util.module_from_spec(sp);sp.loader.exec_module(a);m=a.owned_module('ripper_raw_discovery')
class RawDiscovery(unittest.TestCase):
 def setUp(self):
  self.work=Path(tempfile.mkdtemp(prefix=self._testMethodName+'-',dir=os.environ.get('RIPPER_TEST_ROOT',tempfile.gettempdir())));self.inner=self.work/'upstream_run'
  for name in ('sqlite','output','temp','blastdb'):(self.inner/name).mkdir(parents=True,exist_ok=True)
  self.bound={'genbank':{'path':str(self.work/'synthetic.gbk')},'query_fasta':{'path':str(self.work/'synthetic.faa')},'prodigal_short':{'path':str(self.work/'prodigal-short')}}
  self.contract={'table':'ripper','expected_subject':'SYNTHETIC_TE_001','config':{'min_peptide_length':20,'max_peptide_length':120}};self.db=self.inner/'sqlite/ripper.sqlite3';self.seq='M'+'A'*19
  with closing(sqlite3.connect(self.db)) as c, c:c.execute('CREATE TABLE ripper(acc TEXT,species TEXT,ppser INTEGER,fastaid TEXT,aaseq TEXT,ppstrand INTEGER,testrand INTEGER,pptedist INTEGER,score float,unique(acc,ppser))')
 def row(self,acc='SYNTHETIC_TE_001',serial=1):
  with closing(sqlite3.connect(self.db)) as c, c:c.execute('INSERT INTO ripper VALUES(?,?,?,?,?,?,?,?,?)',(acc,'Synthetic only',serial,acc+'_'+str(serial),self.seq,1,1,12,1.0))
  (self.inner/'output/synthetic_rip.faa').write_text('>'+acc+'_'+str(serial)+' SYNTHETIC_NOT_UPSTREAM\n'+self.seq+'\n');(self.inner/'output/synthetic_rip.gbk').write_text('LOCUS       SYNTHETIC\nORIGIN\n        1 atg\n//\n')
 def stage(self,stage,nohit=False):
  temp=self.inner/'temp';out=temp/(stage+'.stdout');err=temp/(stage+'.stderr');out.write_text('SYNTHETIC only\n');err.write_text('');dbprefix=str(self.inner/'blastdb/synthetic');outp=temp/(stage+'.result');outp.write_text('SYNTHETIC')
  if stage.startswith('makeblastdb-'):
   k=stage.removeprefix('makeblastdb-');argv=['makeblastdb','-in',str(temp/'input'),'-title','synthetic','-dbtype',k,'-out',dbprefix];contract={'kind':'blastdb_'+k,'prefix':dbprefix};paths=[]
   for suffix in (('nhr','nin','nsq') if k=='nucl' else ('phr','pin','psq')):
    p=Path(dbprefix+'.'+suffix);p.write_text('SYNTHETIC_NOT_DB_FORMAT');paths.append(p)
   outcome='DATABASE_FILES_PRESENT_FORMAT_UNVERIFIED'
  elif stage=='blastp':
   outp.write_text('BLASTP SYNTHETIC\nQuery= synthetic\nDatabase: synthetic\n'+('No hits found\n' if nohit else 'Score = 42\n'));argv=['blastp','-query',self.bound['query_fasta']['path'],'-db',dbprefix,'-out',str(outp),'-evalue','1e-3'];contract={'kind':'blastp_pairwise','path':str(outp)};paths=[outp];outcome='NO_HIT_DECLARED_UNATTESTED' if nohit else 'HITS_DECLARED_UNBOUND'
  elif stage=='blastn':
   outp.write_text('SYNTHETIC_Q\tSYNTHETIC_S\t100\t63\t0\t0\t1\t63\t21\t83\t1e-9\t99\n')
   argv=['blastn','-query',str(temp/'query'),'-subject',str(temp/'subject'),'-task','megablast','-out',str(outp),'-outfmt','6','-dust','no'];contract={'kind':'blastn_tsv','path':str(outp)};paths=[outp];outcome='ALIGNMENT_ROWS_SHAPE_OBSERVED_UNBOUND'
  else:
   outp.write_text('1\t63\t+\t12.5\n')
   argv=[self.bound['prodigal_short']['path'],'-p','meta','-f','gff','-i',str(temp/'input'),'-s',str(outp)];contract={'kind':'prodigal_scores','path':str(outp)};paths=[outp];outcome='SCORE_ROWS_SHAPE_OBSERVED_UNBOUND'
  d={'schema':'ripper-local-stage-review-v1','stage':stage,'argv':argv,'stdout':str(out),'stderr':str(err),'contract':contract,'state':'STARTED','validation_scope':'LOCAL_SHAPE_RULES_NATIVE_WORKFLOW_UNVERIFIED'};(temp/(stage+'.stdout.started.json')).write_text(json.dumps(d))
  d.update(state='EXIT_ZERO_OUTPUT_OBSERVED_UNVERIFIED',raw_status=0,validation={'outcome':outcome},outputs=[{'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]);terminal=temp/(stage+'.stdout.terminal.json');terminal.write_text(json.dumps(d));return terminal
 def complete(self,nohit=False):
  stages=('makeblastdb-nucl','makeblastdb-prot','blastp') if nohit else ('makeblastdb-nucl','makeblastdb-prot','blastp','blastn','prodigal-short')
  for stage in stages:self.stage(stage,nohit)
  if not nohit and not (self.inner/'output/synthetic_rip.gbk').exists():(self.inner/'output/synthetic_rip.gbk').write_text('LOCUS       SYNTHETIC\nORIGIN\n        1 atg\n//\n')
 def parse(self):return m.parse_discovery(a.binding_api(),self.inner,self.bound,self.contract)
 def test_raw_candidate_is_unbound_without_hmm_or_coordinates(self):
  self.row();self.complete();d=self.parse();self.assertEqual(d['status'],'SUCCESS_UNBOUND');self.assertEqual(d['candidates'][0]['peptide_id'],'SYNTHETIC_TE_001_1');self.assertEqual(d['candidates'][0]['hmm_annotation'],'NOT_RUN');self.assertEqual(d['candidate_membership'],'UNVERIFIED');self.assertEqual(d['coordinate_provenance'],'ABSENT_PRODUCER_MAPPING')
 def test_completed_no_blastp_hit_is_discovery_scope_only(self):
  self.complete(True);d=self.parse();self.assertEqual(d['status'],'NO_HIT');self.assertFalse(d['biological_absence_inferred']);self.assertEqual(d['candidate_count'],0)
 def test_zero_retained_rows_after_full_stage_roster_is_scoped(self):
  self.complete();d=self.parse();self.assertEqual(d['status'],'NO_RETAINED_CANDIDATES');self.assertFalse(d['biological_absence_inferred'])
 def test_empty_summary_or_exit_zero_without_stages_never_proves_no_hit(self):
  (self.inner/'output/summary.tsv').touch();d=self.parse();self.assertEqual(d['status'],'AMBIGUOUS');self.assertIsNone(d['candidate_count'])
 def test_started_without_terminal_remains_ambiguous(self):
  p=self.stage('blastp');p.rename(p.with_suffix('.retained_incomplete'));d=self.parse();self.assertEqual(d['status'],'AMBIGUOUS');self.assertIn('STARTED_TERMINAL_ROSTER_MISMATCH',d['incomplete'])
 def test_wrong_subject_preserves_original_accession_and_ambiguity(self):
  self.row('OTHER_SUBJECT');self.complete();d=self.parse();self.assertEqual(d['status'],'AMBIGUOUS');self.assertEqual(d['candidates'][0]['enzyme_accession'],'OTHER_SUBJECT');self.assertIsNone(d['candidate_count'])
 def test_fasta_disagrees_with_sqlite_refused(self):
  self.row();self.complete();(self.inner/'output/synthetic_rip.faa').write_text('>SYNTHETIC_TE_001_1\n'+'M'*20+'\n')
  with self.assertRaisesRegex(ValueError,'SQLITE_FASTA_MISMATCH'):self.parse()
 def test_missing_candidate_export_remains_ambiguous(self):
  self.row();self.complete();p=self.inner/'output/synthetic_rip.faa';p.rename(self.inner/'output/preserved_missing_fixture.faa');d=self.parse();self.assertEqual(d['status'],'AMBIGUOUS')
 def test_no_hit_declaration_cannot_coexist_with_candidate_rows(self):
  self.row();self.complete(True)
  with self.assertRaisesRegex(ValueError,'NO_HIT_EXPORT_CONTRADICTION'):self.parse()
 def test_failed_stage_never_becomes_no_hit(self):
  self.complete(True);p=self.inner/'temp/blastp.stdout.terminal.json';d=json.loads(p.read_text());d.update(raw_status=256,state='FAILED_OR_REFUSED');p.write_text(json.dumps(d))
  with self.assertRaisesRegex(ValueError,'STAGE_FAILED_OR_UNRESOLVED'):self.parse()
 def test_stage_argv_substitution_refused(self):
  self.complete(True);p=self.inner/'temp/blastp.stdout.terminal.json';d=json.loads(p.read_text());d['argv'][2]='/unbound/query';p.write_text(json.dumps(d))
  with self.assertRaisesRegex(ValueError,'STARTED_TERMINAL_MISMATCH'):self.parse()
 def test_stage_digest_mismatch_refused(self):
  self.complete(True);(self.inner/'temp/blastp.result').write_text('CHANGED')
  with self.assertRaisesRegex(ValueError,'OUTPUT_DIGEST_MISMATCH'):self.parse()
 def test_live_sqlite_journal_refused(self):
  (Path(str(self.db)+'-wal')).write_text('SYNTHETIC')
  with self.assertRaisesRegex(ValueError,'LIVE_SIDECAR_REFUSED'):self.parse()
 def test_unsafe_table_name_refused(self):
  self.contract['table']='ripper;DROP'
  with self.assertRaisesRegex(ValueError,'SQL_TABLE_INVALID'):self.parse()
 def test_output_symlink_and_external_path_refused(self):
  p=self.inner/'temp/link';p.symlink_to(self.work/'unbound')
  with self.assertRaisesRegex(ValueError,'SYMLINK_REFUSED'):m.contained(self.inner,str(p))
  with self.assertRaisesRegex(ValueError,'OUTSIDE_RUN'):m.contained(self.inner,str(self.work/'outside'))
 def test_coherently_mutated_stage_argv_still_refused(self):
  self.complete(True)
  for suffix in ('started','terminal'):
   p=self.inner/('temp/blastp.stdout.'+suffix+'.json');d=json.loads(p.read_text());d['argv'][2]=str(self.work/'unbound_query');p.write_text(json.dumps(d))
  with self.assertRaisesRegex(ValueError,'ARGV_OR_CONTRACT_MISMATCH'):self.parse()
 def test_noncanonical_identity_or_nonfinite_score_refused(self):
  self.row();self.complete()
  with closing(sqlite3.connect(self.db)) as c, c:c.execute("UPDATE ripper SET fastaid='OTHER_ID'")
  with self.assertRaisesRegex(ValueError,'IDENTITY_INVALID'):self.parse()
 def test_sqlite_view_or_different_columns_refused(self):
  with closing(sqlite3.connect(self.db)) as c, c:c.execute('ALTER TABLE ripper ADD COLUMN unbound TEXT')
  with self.assertRaisesRegex(ValueError,'EXACT_COLUMNS_REQUIRED'):self.parse()
 def test_no_unique_source_identity_constraint_refused(self):
  with closing(sqlite3.connect(self.db)) as c, c:
   c.execute('DROP TABLE ripper');c.execute('CREATE TABLE ripper(acc TEXT,species TEXT,ppser INTEGER,fastaid TEXT,aaseq TEXT,ppstrand INTEGER,testrand INTEGER,pptedist INTEGER,score float)')
  with self.assertRaisesRegex(ValueError,'UNIQUE_IDENTITY_REQUIRED'):self.parse()
 def test_coherent_invalid_blastn_shape_refused(self):
  self.complete();p=self.inner/'temp/blastn.result';p.write_text('INVALID_SYNTHETIC')
  terminal=self.inner/'temp/blastn.stdout.terminal.json';d=json.loads(terminal.read_text());d['outputs']=[{'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}];terminal.write_text(json.dumps(d))
  with self.assertRaisesRegex(ValueError,'BLASTN_ROW_INVALID'):self.parse()
 def test_coherent_invalid_prodigal_shape_refused(self):
  self.complete();p=self.inner/'temp/prodigal-short.result';p.write_text('1\\t63\\t+\\tnan\\n')
  terminal=self.inner/'temp/prodigal-short.stdout.terminal.json';d=json.loads(terminal.read_text());d['outputs']=[{'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}];terminal.write_text(json.dumps(d))
  with self.assertRaisesRegex(ValueError,'PRODIGAL_ROW_INVALID'):self.parse()
 def replace_prodigal_output(self,text,outcome='SCORE_ROWS_SHAPE_OBSERVED_UNBOUND'):
  self.complete();p=self.inner/'temp/prodigal-short.result';p.write_text(text)
  terminal=self.inner/'temp/prodigal-short.stdout.terminal.json';d=json.loads(terminal.read_text());d['outputs']=[{'path':str(p),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}];d['validation']['outcome']=outcome;terminal.write_text(json.dumps(d))
 def test_exact_native_prodigal_header_is_metadata_not_candidate(self):
  header='Beg\tEnd\tStd\tTotal\tCodPot\tStrtSc\tCodon\tRBSMot\tSpacer\tRBSScr\tUpsScr\tTypeScr\tGCCont'
  self.row();self.replace_prodigal_output('# native metadata\n'+header+'\n1\t63\t+\t2.5\t0\t0\tATG\tNone\tNone\t0\t0\t0\t0.5\n');d=self.parse();self.assertEqual(d['status'],'SUCCESS_UNBOUND');self.assertFalse(d['biological_absence_inferred'])
 def test_native_header_variants_duplicate_and_misplaced_refused(self):
  header='Beg\tEnd\tStd\tTotal\tCodPot\tStrtSc\tCodon\tRBSMot\tSpacer\tRBSScr\tUpsScr\tTypeScr\tGCCont';row='1\t63\t+\t2.5\n'
  for text in [header.replace('Beg','BEGIN')+'\n'+row,header+'\n'+header+'\n'+row,row+header+'\n',' '+header+'\n'+row,header+'\tExtra\n'+row]:
   self.replace_prodigal_output(text)
   with self.subTest(text=text),self.assertRaisesRegex(ValueError,'RAW_PRODIGAL_ROW_INVALID'):self.parse()
 def test_exact_header_only_retains_no_score_rows_qualification(self):
  header='Beg\tEnd\tStd\tTotal\tCodPot\tStrtSc\tCodon\tRBSMot\tSpacer\tRBSScr\tUpsScr\tTypeScr\tGCCont'
  self.replace_prodigal_output(header+'\n','NO_SCORE_ROWS_REPORTED_UNVERIFIED');d=self.parse();self.assertEqual(d['stages']['prodigal-short']['outcome'],'NO_SCORE_ROWS_REPORTED_UNVERIFIED');self.assertFalse(d['biological_absence_inferred'])
 def test_native_header_does_not_bypass_malformed_score_row(self):
  header='Beg\tEnd\tStd\tTotal\tCodPot\tStrtSc\tCodon\tRBSMot\tSpacer\tRBSScr\tUpsScr\tTypeScr\tGCCont'
  self.replace_prodigal_output(header+'\n1\t63\t+\tnan\n')
  with self.assertRaisesRegex(ValueError,'RAW_PRODIGAL_ROW_INVALID'):self.parse()
 def test_actual_pinned_prodigal_score_bytes_from_owner(self):
  selected=os.environ.get('RIPPER_ACTUAL_PRODIGAL_SCORES')
  if not selected:self.skipTest('explicit actual fabricated Prodigal score file not selected')
  raw=Path(selected).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),'07f6cc25bf192462a2a646561630e0cb8ce5d689516f14c6f5bfad687f7c0ceb');self.replace_prodigal_output(raw.decode());d=self.parse();self.assertEqual(d['stages']['prodigal-short']['outcome'],'SCORE_ROWS_SHAPE_OBSERVED_UNBOUND');self.assertFalse(d['biological_absence_inferred'])
if __name__=='__main__':unittest.main()
