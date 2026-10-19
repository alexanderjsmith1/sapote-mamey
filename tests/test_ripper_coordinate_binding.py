"""Tiny de novo mapping declarations; not output from an upstream run."""
import hashlib,importlib.util,json,os,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);obj=importlib.util.module_from_spec(spec);spec.loader.exec_module(obj);return obj
adapter=module('coordinate_adapter',ROOT/'tools/ripper_adapter.py')
coords=module('coordinate_binding',ROOT/'tools/ripper_coordinate_binding.py')
try:
 from Bio import SeqIO
 from Bio.Seq import Seq
 from Bio.SeqRecord import SeqRecord
 from Bio.SeqFeature import SeqFeature,FeatureLocation
 HAVE_BIO=True
except ImportError:HAVE_BIO=False

@unittest.skipUnless(HAVE_BIO,'optional Biopython required for coordinate/sequence tests')
class CoordinateTests(unittest.TestCase):
 def setUp(self):
  root=Path(os.environ.get('RIPPER_TEST_ROOT',tempfile.gettempdir()));root.mkdir(parents=True,exist_ok=True)
  self.work=Path(tempfile.mkdtemp(prefix=self._testMethodName+'-',dir=root));self.out=self.work/'binding'
  self.aa='M'+'C'*19;self.te='M'+'A'*29;dna=list('GCG'*200)
  for start,seq in [(0,'ATG'+'GCG'*29+'TAA'),(150,'ATG'+'TGC'*19+'TAA'),(300,'ATG'+'TGC'*19+'TAA')]:dna[start:start+len(seq)]=seq
  self.record=SeqRecord(Seq(''.join(dna)),id='SYNTHETIC_COORD',name='SYNTHETIC',description='de novo coordinate declaration test')
  self.record.annotations['molecule_type']='DNA';self.record.features=[SeqFeature(FeatureLocation(0,93,strand=1),type='CDS',qualifiers={'locus_tag':['SYNTHETIC_TE'],'translation':[self.te]})]
  self.gbk=self.work/'input.gbk';SeqIO.write(self.record,self.gbk,'genbank')
  self.faa=self.work/'query.faa';self.faa.write_text('>SYNTHETIC_QUERY\n'+self.te+'\n')
  self.q=dict(enzyme_accession='SYNTHETIC_TE',strain='SYNTHETIC',full_contig='SYNTHETIC_COORD',region='region001',bgc_alias='SYNTHETIC_BGC')
  qpath=self.write('queries.json',dict(schema_version='ripper-queries/1',queries=[self.q]));conf=self.work/'local.conf';conf.write_text('sqlite3fn sqlite/db\nprepeptab ripper\nblastdbdir blastdb\n')
  self.plan=adapter.local_plan(qpath,self.gbk,self.faa,conf,self.work/'plan','archived-e90b3e6-mergeRidePfam',True);self.plan_path=self.work/'plan/LOCAL_PLAN.json'
  candidate=dict(enzyme_accession='SYNTHETIC_TE',peptide_id='SYNTHETIC_TE_1',sequence=self.aa,query_context={k:self.q[k] for k in adapter.IDENTITY},raw_fields={'PPSerial':'1'})
  self.evidence_path=self.write('evidence.json',dict(schema_version='ripper-evidence/2',declared_upstream_state='COMPLETE',evidence_kind='synthetic_fixture',upstream_execution='NOT_EXECUTED_SYNTHETIC',query_count=1,candidate_count=1,candidates=[candidate]))
  row=dict(enzyme_accession='SYNTHETIC_TE',FastaID='SYNTHETIC_TE_1',PPSerial='1',sequence_sha256=hashlib.sha256(self.aa.encode()).hexdigest(),window_start_1based=1,window_end_inclusive=600,window_sequence_sha256=hashlib.sha256(str(self.record.seq).encode()).hexdigest(),local_start_1based=151,local_end_inclusive=213,strand=1)
  self.mapping=dict(schema_version='ripper-coordinate-map/1',mapping_origin='synthetic_fixture',evidence_sha256=self.sha(self.evidence_path),local_plan_sha256=self.sha(self.plan_path),source_genbank_sha256=self.sha(self.gbk),query_fasta_sha256=self.sha(self.faa),subject_cds_sha256=coords.subject_digest(self.sha(self.gbk),self.record.id,self.plan['semantic_validation']['selected_subject_cds']),mappings=[row])
 def sha(self,path):return hashlib.sha256(path.read_bytes()).hexdigest()
 def write(self,name,data):
  p=self.work/name;p.write_text(json.dumps(data,indent=2)+'\n');return p
 def run_binding(self):
  p=self.write('mapping.json',self.mapping)
  api={k:getattr(adapter,k) for k in ('json_input','load_bytes','binding','publish','IDENTITY','validate_local_semantics')}
  return coords.bind_coordinates(api,self.evidence_path,self.plan_path,self.gbk,self.faa,p,self.out)
 def refuse(self,code):
  with self.assertRaisesRegex(ValueError,code):self.run_binding()
  self.assertFalse(self.out.exists())
 def test_direct_match_is_unattested_not_membership(self):
  data=self.run_binding();row=data['assessments'][0]
  self.assertEqual(row['status'],'DIRECT_SEQUENCE_MATCH_UNATTESTED');self.assertEqual(row['locations'][0]['start_0based'],150);self.assertEqual(row['locations'][0]['end_exclusive'],213)
  self.assertEqual(data['candidate_membership'],'UNVERIFIED');self.assertEqual(data['upstream_execution'],'NOT_EXECUTED_SYNTHETIC')
 def test_absent_mapping_is_not_biological_no_hit(self):
  self.mapping['mappings']=[];data=self.run_binding()
  self.assertEqual(data['assessments'][0]['status'],'ABSENT_MAPPING');self.assertEqual(data['candidate_count'],1)
 def test_two_matching_locations_are_ambiguous(self):
  row=dict(self.mapping['mappings'][0],local_start_1based=301,local_end_inclusive=363);self.mapping['mappings'].append(row)
  self.assertEqual(self.run_binding()['assessments'][0]['status'],'AMBIGUOUS_DECLARED_MAPPINGS')
 def test_wrong_sequence_is_not_a_direct_match(self):
  self.mapping['mappings'][0].update(local_start_1based=1,local_end_inclusive=63)
  self.assertEqual(self.run_binding()['assessments'][0]['status'],'SEQUENCE_MISMATCH')
 def test_hashes_are_exact(self):
  for key in ('evidence_sha256','local_plan_sha256','source_genbank_sha256','query_fasta_sha256'):
   with self.subTest(key=key):
    old=self.mapping[key];self.mapping[key]='0'*64;self.refuse('INPUT_HASH_MISMATCH');self.mapping[key]=old
 def test_wrong_cds_hash_refused(self):
  self.mapping['subject_cds_sha256']='0'*64;self.refuse('SUBJECT_CDS_HASH_MISMATCH')
 def test_wrong_window_hash_refused(self):
  self.mapping['mappings'][0]['window_sequence_sha256']='0'*64;self.refuse('WINDOW_SEQUENCE_HASH_MISMATCH')
 def test_serial_identity_cannot_cross_candidate(self):
  self.mapping['mappings'][0]['PPSerial']='9001';self.refuse('UNBOUND_CANDIDATE')
 def test_geometry_bool_or_outside_refused(self):
  row=self.mapping['mappings'][0];row['local_start_1based']=True;self.refuse('INTEGER_GEOMETRY_REQUIRED')
  row['local_start_1based']=0;self.refuse('GEOMETRY_OUT_OF_RANGE')
 def test_duplicate_mapping_refused(self):
  self.mapping['mappings'].append(dict(self.mapping['mappings'][0]));self.refuse('DUPLICATE_MAPPING')
 def test_mapping_identifier_shape_refused(self):
  self.mapping['mappings'][0]['FastaID']=[];self.refuse('MAP_IDENTIFIER_INVALID')
 def test_stale_plan_source_cannot_be_rebound_by_mapping_only(self):
  self.gbk.write_text(self.gbk.read_text()+'\n');self.mapping['source_genbank_sha256']=self.sha(self.gbk);self.refuse('PLAN_SOURCE_BINDING_MISMATCH')

if __name__=='__main__':unittest.main()
