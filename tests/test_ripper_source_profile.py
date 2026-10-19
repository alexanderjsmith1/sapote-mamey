"""Source-backed contracts and synthetic rows; never run archived Perl/scripts."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('ripper_profile_adapter', ROOT/'tools/ripper_adapter.py')
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)
PROFILE_PATH = ROOT/'tools/ripper_source_profile.json'
PROFILE = json.loads(PROFILE_PATH.read_text())


class SourceProfileTests(unittest.TestCase):
    def setUp(self):
        root = Path(os.environ.get('RIPPER_TEST_ROOT', tempfile.gettempdir()))
        root.mkdir(parents=True, exist_ok=True)
        self.work = Path(tempfile.mkdtemp(prefix=self._testMethodName+'-', dir=root))
        queries = json.loads((ROOT/'tests/fixtures/ripper/queries.json').read_text())
        queries['queries'] = queries['queries'][:1]
        self.q = self.write('queries.json', queries)
        self.columns = self.write('columns.json', PROFILE['columns'])
        self.raw = self.write('raw.tsv', '\t'.join(PROFILE['headers'])+'\n'+'\t'.join(['SYNTHETIC_TE_001','Synthetic','1','SYNTHETIC_TE_001_1','MAGCAGCAGCAGCAGCAGCA','yes','12','-2.5','none','none','none'])+'\n')
        self.conf = self.write('synthetic.conf', '# Synthetic only; no upstream run\nsqlite3fn sqlite/ripp.sqlite3\nprepeptab ripper\nblastdbdir blastdb\n')
        self.log = self.write('completion.log', 'SYNTHETIC not executed\n')
        self.gbk = self.write('single.gbk', 'LOCUS       SYNTHETIC 60 bp DNA\nFEATURES             Location/Qualifiers\n     CDS             1..60\n                     /locus_tag="SYNTHETIC_TE_001"\nORIGIN\n        1 atggctggct\n//\n')
        self.faa = self.write('query.faa', '>synthetic_query_id_not_subject_id\nMAGCAGCAGCAGCAGCAGCA\n')
        self.out = self.work/'output'
        self.receipt = dict(schema_version='ripper-run/1', state='COMPLETE', upstream=adapter.PROJECT,
            evidence_kind='synthetic_fixture', reason='Synthetic source-schema contract; no upstream execution',
            upstream_revision='0'*40, exit_code=0, runtime_versions={'RiPPER':'NOT_EXECUTED'},
            completed_accessions=['SYNTHETIC_TE_001'], output_profile=PROFILE['id'], output_channel='main',
            source_profile_sha256=self.sha(PROFILE_PATH))
        self.rebind()

    def write(self, name, value):
        p=self.work/name
        p.write_text(json.dumps(value,indent=2)+'\n' if isinstance(value,dict) else value)
        return p

    def sha(self,path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def rebind(self):
        for key,p in [('queries',self.q),('columns',self.columns),('raw',self.raw),('config',self.conf),('completion_log',self.log)]:
            self.receipt[key+'_sha256']=self.sha(p)
        self.receipt_path=self.write('receipt.json',self.receipt)

    def run_import(self, channel='main'):
        return adapter.import_results(self.q,self.receipt_path,self.out,self.raw,self.columns,self.conf,self.log,PROFILE['id'],channel)

    def refused(self,message,channel='main'):
        with self.assertRaisesRegex(ValueError,message):self.run_import(channel)
        self.assertFalse(self.out.exists())

    def test_source_profile_export_is_not_execution(self):
        data=adapter.write_profile(PROFILE['id'],self.out)
        self.assertEqual(data['upstream_execution'],'NOT_EXECUTED')
        self.assertEqual(json.loads((self.out/'columns.json').read_text()),PROFILE['columns'])
        self.assertEqual(data['container_source_equivalence'],'UNKNOWN')

    def test_local_plan_keeps_execution_and_membership_held(self):
        data=adapter.local_plan(self.q,self.gbk,self.faa,self.conf,self.out,PROFILE['id'])
        self.assertEqual(data['plan_status'],'HOLD')
        self.assertEqual(data['upstream_execution'],'NOT_EXECUTED')
        self.assertEqual(data['candidate_membership'],'UNVERIFIED')
        self.assertEqual(data['expected_subject_cds_id'],'SYNTHETIC_TE_001')
        self.assertNotEqual(data['expected_subject_cds_id'],'synthetic_query_id_not_subject_id')
        self.assertIn('ripper_local.pl',' '.join(data['invocation_template']))
        self.assertNotIn('ripper_local.sh',' '.join(data['invocation_template']))
        self.assertTrue(any('FTP' in x for x in data['holds']))

    def test_multi_record_genbank_refused(self):
        self.gbk.write_text(self.gbk.read_text()*2)
        with self.assertRaisesRegex(ValueError,'SINGLE_GENBANK_RECORD'):
            adapter.local_plan(self.q,self.gbk,self.faa,self.conf,self.out,PROFILE['id'])
        self.assertFalse(self.out.exists())

    def test_multi_query_fasta_refused(self):
        self.faa.write_text(self.faa.read_text()*2)
        with self.assertRaisesRegex(ValueError,'SINGLE_FASTA_QUERY'):
            adapter.local_plan(self.q,self.gbk,self.faa,self.conf,self.out,PROFILE['id'])

    def test_missing_blastdb_config_refused(self):
        self.conf.write_text('sqlite3fn sqlite/ripp.sqlite3\nprepeptab ripper\n')
        with self.assertRaisesRegex(ValueError,'CONFIG_REQUIRES_SQLITE_TABLE_BLASTDBDIR'):
            adapter.local_plan(self.q,self.gbk,self.faa,self.conf,self.out,PROFILE['id'])

    def test_local_plan_rejects_multiple_query_contexts(self):
        self.q=ROOT/'tests/fixtures/ripper/queries.json'
        with self.assertRaisesRegex(ValueError,'ONE_QUERY_CONTEXT'):
            adapter.local_plan(self.q,self.gbk,self.faa,self.conf,self.out,PROFILE['id'])

    def test_verified_header_synthetic_import_preserves_v2_holds(self):
        data=self.run_import()
        self.assertEqual(data['upstream_execution'],'NOT_EXECUTED_SYNTHETIC')
        self.assertEqual(data['source_profile']['revision'],PROFILE['revision'])
        self.assertEqual(data['candidates'][0]['candidate_membership'],'UNVERIFIED')
        self.assertEqual(data['candidates'][0]['raw_fields']['Prodigalscore'],'-2.5')

    def test_header_only_keeps_narrow_synthetic_no_rows(self):
        self.raw.write_text('\t'.join(PROFILE['headers'])+'\n');self.rebind()
        data=self.run_import()
        self.assertEqual(data['candidate_count'],0)
        self.assertEqual(data['assessments'][0]['assessment_status'],'SYNTHETIC_NO_RETAINED_CANDIDATES')

    def test_extra_header_refused(self):
        text=self.raw.read_text().splitlines();text[0]+='\textra';text[1]+='\tunknown'
        self.raw.write_text('\n'.join(text)+'\n');self.rebind()
        self.refused('ARCHIVED_PROFILE_EXACT_HEADER_REQUIRED')

    def test_rebound_arbitrary_column_map_refused(self):
        self.columns.write_text(json.dumps(dict(PROFILE['columns'],peptide_id='Organism')));self.rebind()
        self.refused('ARCHIVED_PROFILE_COLUMNS_MISMATCH')

    def test_profile_binding_required(self):
        self.receipt['source_profile_sha256']='0'*64;self.rebind()
        self.refused('RUN_SOURCE_PROFILE_BINDING_MISMATCH')

    def test_operator_source_revision_must_match_archive(self):
        self.receipt.update(evidence_kind='operator_supplied',upstream_revision='a'*40);self.rebind()
        self.refused('ARCHIVED_PROFILE_REQUIRES_MATCHING_SOURCE_REVISION')

    def test_matching_revision_still_not_attested(self):
        self.receipt.update(evidence_kind='operator_supplied',upstream_revision=PROFILE['revision']);self.rebind()
        data=self.run_import()
        self.assertEqual(data['upstream_execution'],'OPERATOR_DECLARED_UNATTESTED')
        self.assertEqual(data['candidate_membership'],'UNVERIFIED')

    def test_main_cannot_accept_distant_identifier(self):
        self.raw.write_text(self.raw.read_text().replace('Synthetic\t1\tSYNTHETIC_TE_001_1','Synthetic\t9001\tSYNTHETIC_TE_001_9001'));self.rebind()
        self.refused('ARCHIVED_PROFILE_CHANNEL_ROW_MISMATCH')

    def test_distant_requires_non_none_hit_name(self):
        self.raw.write_text(self.raw.read_text().replace('Synthetic\t1\tSYNTHETIC_TE_001_1','Synthetic\t9001\tSYNTHETIC_TE_001_9001'))
        self.receipt['output_channel']='distant';self.rebind()
        self.refused('ARCHIVED_PROFILE_CHANNEL_ROW_MISMATCH','distant')

    def test_distant_blank_hit_name_refused_even_after_rebinding(self):
        raw=self.raw.read_text().replace('Synthetic\t1\tSYNTHETIC_TE_001_1','Synthetic\t9001\tSYNTHETIC_TE_001_9001')
        fields=raw.splitlines()[1].split('\t');fields[8]=''
        self.raw.write_text('\t'.join(PROFILE['headers'])+'\n'+'\t'.join(fields)+'\n')
        self.receipt['output_channel']='distant';self.rebind()
        self.refused('ARCHIVED_PROFILE_CHANNEL_ROW_MISMATCH','distant')

    def test_distant_retained_row_import(self):
        text=self.raw.read_text().replace('Synthetic\t1\tSYNTHETIC_TE_001_1','Synthetic\t9001\tSYNTHETIC_TE_001_9001').replace('none\tnone\tnone','SYNTHETIC_RIPP_HMM\t1e-9\tsynthetic hit')
        self.raw.write_text(text);self.receipt['output_channel']='distant';self.rebind()
        data=self.run_import('distant')
        self.assertEqual(data['output_channel'],'distant')
        self.assertEqual(data['channel_validation']['hmm_collection_identity'],'UNVERIFIED_NOT_PRESENT_IN_TSV')
        self.assertEqual(data['channel_validation']['score_distance_validation'],'RAW_PRESERVED_NOT_SEMANTICALLY_VALIDATED')
        self.assertIn('HOLD_HMM_COLLECTION_PROVENANCE',data['channel_validation']['holds'])

    def test_contradictory_main_serial_refused_before_publication(self):
        self.raw.write_text(self.raw.read_text().replace('Synthetic\t1\t','Synthetic\t9001\t'));self.rebind()
        self.refused('ARCHIVED_PROFILE_SERIAL_ID_MISMATCH')

    def test_contradictory_distant_serial_refused_before_publication(self):
        self.raw.write_text(self.raw.read_text().replace('SYNTHETIC_TE_001_1','SYNTHETIC_TE_001_9001'))
        self.receipt['output_channel']='distant';self.rebind()
        self.refused('ARCHIVED_PROFILE_SERIAL_ID_MISMATCH','distant')

    def test_non_native_serial_encodings_refused(self):
        original=self.raw.read_text()
        for serial in ('0','-1','+1','01','1.0','1e0','',' 1','1 ','١'):
            with self.subTest(serial=serial):
                fields=original.splitlines()[1].split('\t');fields[2]=serial
                self.raw.write_text('\t'.join(PROFILE['headers'])+'\n'+'\t'.join(fields)+'\n');self.rebind()
                self.refused('ARCHIVED_PROFILE_SERIAL_INVALID')

    def test_padded_fasta_suffix_does_not_match_native_serial(self):
        self.raw.write_text(self.raw.read_text().replace('SYNTHETIC_TE_001_1','SYNTHETIC_TE_001_01'));self.rebind()
        self.refused('ARCHIVED_PROFILE_SERIAL_ID_MISMATCH')

    def test_valid_main_serial_pair_keeps_raw_values(self):
        self.raw.write_text(self.raw.read_text().replace('Synthetic\t1\tSYNTHETIC_TE_001_1','Synthetic\t3\tSYNTHETIC_TE_001_3'));self.rebind()
        data=self.run_import()
        self.assertEqual(data['candidates'][0]['raw_fields']['PPSerial'],'3')
        self.assertEqual(data['candidates'][0]['peptide_id'],'SYNTHETIC_TE_001_3')
        self.assertEqual(data['upstream_execution'],'NOT_EXECUTED_SYNTHETIC')

    def test_generic_tsv_does_not_apply_archived_serial_rules(self):
        self.raw.write_text(self.raw.read_text().replace('Synthetic\t1\tSYNTHETIC_TE_001_1','Synthetic\tnot_a_serial\tSYNTHETIC_TE_001_9001'));self.rebind()
        data=adapter.import_results(self.q,self.receipt_path,self.out,self.raw,self.columns,self.conf,self.log)
        self.assertEqual(data['candidates'][0]['raw_fields']['PPSerial'],'not_a_serial')
        self.assertIsNone(data['source_profile'])
        self.assertIsNone(data['channel_validation'])
        self.assertEqual(data['candidate_membership'],'UNVERIFIED')

    def test_query_fasta_identifier_cannot_replace_subject_id(self):
        self.raw.write_text(self.raw.read_text().replace('SYNTHETIC_TE_001_1','WRONG_QUERY_ID_1'));self.rebind()
        self.refused('ARCHIVED_PROFILE_SUBJECT_PEPTIDE_ID_MISMATCH')

    def test_profile_and_channel_must_be_paired(self):
        with self.assertRaisesRegex(ValueError,'REQUIRED_TOGETHER'):
            adapter.import_results(self.q,self.receipt_path,self.out,self.raw,self.columns,self.conf,self.log,PROFILE['id'])

    @unittest.skipUnless(os.environ.get('RIPPER_ARCHIVE_ROOT'),'supplied archived source verification is opt-in')
    def test_profile_headers_match_bound_archived_writer(self):
        p=Path(os.environ['RIPPER_ARCHIVE_ROOT'])/'mergeRidePfam.pl'
        text=p.read_text();head=re.search(r'my @head = qw\((.*?)\);',text,re.S).group(1).split()
        self.assertEqual(head,PROFILE['headers'])

    @unittest.skipUnless(os.environ.get('RIPPER_ARCHIVE_ROOT'),'supplied archived source verification is opt-in')
    def test_profile_sources_match_supplied_git_blobs(self):
        root=Path(os.environ['RIPPER_ARCHIVE_ROOT'])
        for entry in PROFILE['reviewed_sources']:
            raw=(root/entry['file']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),entry['sha256'])
            self.assertEqual(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),entry['sha1_git'])


if __name__=='__main__':unittest.main()
