"""Optional input semantics; all sequences synthetic, no RiPPER process launched."""
import builtins
import copy
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location('ripper_semantic_adapter',ROOT/'tools/ripper_adapter.py')
adapter=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(adapter)
FIX=ROOT/'tests/fixtures/ripper_semantic'
PROFILE='archived-e90b3e6-mergeRidePfam'
try:
    from Bio import SeqIO
    from Bio.Seq import Seq
    from Bio.SeqFeature import FeatureLocation,CompoundLocation,BeforePosition
    HAVE_BIO=True
except ImportError:
    HAVE_BIO=False


class OptionalSemanticModeTests(unittest.TestCase):
    def setUp(self):
        root=Path(os.environ.get('RIPPER_TEST_ROOT',tempfile.gettempdir()));root.mkdir(parents=True,exist_ok=True)
        self.work=Path(tempfile.mkdtemp(prefix=self._testMethodName+'-',dir=root));self.out=self.work/'output'

    def call(self,semantic):
        return adapter.local_plan(FIX/'synthetic_query_context.json',FIX/'synthetic_single_record.gbk',
            FIX/'synthetic_single_query.faa',FIX/'fresh_run.conf.template',self.out,PROFILE,semantic)

    def test_default_text_only_stays_held_and_explicit(self):
        data=self.call(False)
        self.assertEqual(data['semantic_validation']['status'],'NOT_REQUESTED_TEXT_ONLY')
        self.assertEqual(data['plan_status'],'HOLD');self.assertEqual(data['upstream_execution'],'NOT_EXECUTED')

    def test_missing_dependency_emits_hold_never_false_pass(self):
        original=builtins.__import__
        def unavailable(name,*args,**kwargs):
            if name=='Bio' or name.startswith('Bio.'):raise ModuleNotFoundError('simulated missing optional Bio')
            return original(name,*args,**kwargs)
        with patch('builtins.__import__',side_effect=unavailable):data=self.call(True)
        self.assertEqual(data['semantic_validation']['status'],'HOLD_DEPENDENCY_UNAVAILABLE')
        self.assertEqual(data['upstream_execution'],'NOT_EXECUTED')
        self.assertEqual(data['candidate_membership'],'UNVERIFIED')
        self.assertTrue((self.out/'LOCAL_PLAN.json').is_file())

    def test_cli_optin_uses_existing_logging_route(self):
        original=builtins.__import__
        def unavailable(name,*args,**kwargs):
            if name=='Bio' or name.startswith('Bio.'):raise ImportError('simulated optional dependency')
            return original(name,*args,**kwargs)
        with patch('builtins.__import__',side_effect=unavailable),self.assertLogs(adapter.LOG,level='INFO') as captured:
            result=adapter.main(['local-plan','--queries',str(FIX/'synthetic_query_context.json'),
                '--genbank',str(FIX/'synthetic_single_record.gbk'),'--query-fasta',str(FIX/'synthetic_single_query.faa'),
                '--config',str(FIX/'fresh_run.conf.template'),'--profile',PROFILE,'--semantic-validation','--out',str(self.out)])
        self.assertEqual(result,0)
        self.assertIn('semantic_validation=HOLD_DEPENDENCY_UNAVAILABLE',' '.join(captured.output))
        self.assertEqual(json.loads((self.out/'LOCAL_PLAN.json').read_text())['semantic_validation']['status'],'HOLD_DEPENDENCY_UNAVAILABLE')


@unittest.skipUnless(HAVE_BIO,'optional Biopython unavailable; dependency-HOLD tests still run')
class SemanticBindingTests(unittest.TestCase):
    def setUp(self):
        root=Path(os.environ.get('RIPPER_TEST_ROOT',tempfile.gettempdir()));root.mkdir(parents=True,exist_ok=True)
        self.work=Path(tempfile.mkdtemp(prefix=self._testMethodName+'-',dir=root));self.out=self.work/'output'
        self.record=SeqIO.read(FIX/'synthetic_single_record.gbk','genbank')
        self.query=json.loads((FIX/'synthetic_query_context.json').read_text())
        self.protein=SeqIO.read(FIX/'synthetic_single_query.faa','fasta')

    def run_plan(self):
        gbk=self.work/'input.gbk';faa=self.work/'query.faa';q=self.work/'context.json'
        SeqIO.write(self.record,gbk,'genbank');SeqIO.write(self.protein,faa,'fasta');q.write_text(json.dumps(self.query)+'\n')
        return adapter.local_plan(q,gbk,faa,FIX/'fresh_run.conf.template',self.out,PROFILE,True)

    def refuse(self,code):
        with self.assertRaisesRegex(ValueError,code):self.run_plan()
        self.assertFalse(self.out.exists())

    def test_de_novo_readiness_fixture_binds_subject_not_function(self):
        data=self.run_plan();semantic=data['semantic_validation']
        self.assertEqual(semantic['status'],'PASS_INPUT_BINDING_ONLY')
        self.assertEqual(semantic['selected_subject_cds']['start_0based'],20000)
        self.assertEqual(semantic['selected_subject_cds']['end_exclusive'],20903)
        self.assertEqual(semantic['query_fasta_id'],'SYNTHETIC_QUERY_NOT_SUBJECT_ID')
        self.assertEqual(semantic['query_relation'],'EXACT_SEQUENCE_SELF_MATCH_ONLY')
        self.assertEqual(semantic['gene_function'],'UNASSESSED')
        self.assertEqual(semantic['blast_selection'],'UNASSESSED')
        self.assertEqual(data['plan_status'],'HOLD');self.assertEqual(data['candidate_membership'],'UNVERIFIED')

    def test_reverse_strand_cds_is_sequence_checked(self):
        feature=self.record.features[0];dna=feature.extract(self.record.seq)
        start,end=int(feature.location.start),int(feature.location.end)
        self.record.seq=self.record.seq[:start]+dna.reverse_complement()+self.record.seq[end:]
        feature.location=FeatureLocation(start,end,strand=-1)
        result=self.run_plan()['semantic_validation']
        self.assertEqual(result['selected_subject_cds']['strand'],-1)
        self.assertTrue(result['selected_subject_cds']['query_exact_match'])

    def test_complete_left_edge_cds_is_valid(self):
        feature=self.record.features[0];dna=feature.extract(self.record.seq)
        self.record.seq=dna+self.record.seq[len(dna):];feature.location=FeatureLocation(0,len(dna),strand=1)
        self.assertEqual(self.run_plan()['semantic_validation']['selected_subject_cds']['start_0based'],0)

    def test_complete_right_edge_cds_is_valid(self):
        feature=self.record.features[0];dna=feature.extract(self.record.seq);start=len(self.record)-len(dna)
        self.record.seq=self.record.seq[:start]+dna;feature.location=FeatureLocation(start,len(self.record),strand=1)
        self.assertEqual(self.run_plan()['semantic_validation']['selected_subject_cds']['end_exclusive'],len(self.record))

    def test_duplicate_source_priority_id_refused(self):
        self.record.features.append(copy.deepcopy(self.record.features[0]));self.refuse('DUPLICATE_CDS_ID')

    def test_two_exact_query_subjects_refused(self):
        other=copy.deepcopy(self.record.features[0]);other.qualifiers['locus_tag']=['OTHER_CDS'];self.record.features.append(other)
        self.refuse('AMBIGUOUS_EXACT_QUERY_MATCH')

    def test_compound_cds_refused(self):
        f=self.record.features[0];a,b=int(f.location.start),int(f.location.end)
        f.location=CompoundLocation([FeatureLocation(a,a+300,strand=1),FeatureLocation(a+300,b,strand=1)])
        self.refuse('COMPOUND_OR_MISSING_CDS_LOCATION')

    def test_out_of_range_cds_refused(self):
        f=self.record.features[0];f.location=FeatureLocation(f.location.start,len(self.record)+3,strand=1)
        self.refuse('CDS_COORDINATES_INVALID')

    def test_remote_cds_location_refused(self):
        f=self.record.features[0];f.location=FeatureLocation(f.location.start,f.location.end,strand=1,ref='OTHER_RECORD')
        self.refuse('REMOTE_CDS_LOCATION')

    def test_partial_cds_refused(self):
        f=self.record.features[0];f.location=FeatureLocation(BeforePosition(int(f.location.start)),f.location.end,strand=1)
        self.refuse('PARTIAL_CDS_LOCATION')

    def test_missing_explicit_cds_identifier_refused(self):
        f=self.record.features[0];f.qualifiers.pop('locus_tag');f.qualifiers.pop('protein_id');self.refuse('EXPLICIT_SAFE_CDS_ID_REQUIRED')

    def test_ambiguous_identifier_qualifier_refused(self):
        self.record.features[0].qualifiers['locus_tag']=['SYNTHETIC_TE_001','OTHER'];self.refuse('AMBIGUOUS_OR_EMPTY_QUALIFIER')

    def test_whitespace_identifier_not_silently_normalized(self):
        self.record.features[0].qualifiers['locus_tag']=['SYNTHETIC TE'];self.refuse('EXPLICIT_SAFE_CDS_ID_REQUIRED')

    def test_source_priority_protein_id_fallback_binds(self):
        f=self.record.features[0];f.qualifiers.pop('locus_tag');self.query['queries'][0]['enzyme_accession']='SYNTHETIC_TE_001.1'
        self.assertEqual(self.run_plan()['semantic_validation']['selected_subject_cds']['source_id_qualifier'],'protein_id')

    def test_context_record_mismatch_refused(self):
        self.query['queries'][0]['full_contig']='OTHER_RECORD';self.refuse('RECORD_QUERY_CONTEXT_MISMATCH')

    def test_expected_subject_missing_refused(self):
        self.query['queries'][0]['enzyme_accession']='OTHER';self.refuse('EXPECTED_SUBJECT_CDS_NOT_BOUND')

    def test_translation_mismatch_refused(self):
        self.record.features[0].qualifiers['translation']=['M'+'A'*299];self.refuse('CDS_TRANSLATION_MISMATCH')

    def test_empty_translation_refused(self):
        self.record.features[0].qualifiers['translation']=[''];self.refuse('AMBIGUOUS_OR_EMPTY_QUALIFIER')

    def test_missing_translation_refused(self):
        self.record.features[0].qualifiers.pop('translation');self.refuse('VALID_TRANSLATION_REQUIRED')

    def test_invalid_translation_alphabet_refused(self):
        self.record.features[0].qualifiers['translation']=['MXXX'];self.refuse('VALID_TRANSLATION_REQUIRED')

    def test_pseudogene_refused(self):
        self.record.features[0].qualifiers['pseudo']=[''];self.refuse('UNSUPPORTED_CDS_EXCEPTION')

    def test_unsupported_genetic_code_refused(self):
        self.record.features[0].qualifiers['transl_table']=['4'];self.refuse('UNSUPPORTED_TRANSLATION_TABLE')

    def test_bacterial_code11_atg_passes(self):
        self.record.features[0].qualifiers['transl_table']=['11']
        self.assertEqual(self.run_plan()['semantic_validation']['selected_subject_cds']['translation_table'],11)

    def test_unsupported_codon_start_refused(self):
        self.record.features[0].qualifiers['codon_start']=['2'];self.refuse('UNSUPPORTED_CODON_START')

    def test_nonexact_query_does_not_invent_homology(self):
        self.protein.seq=Seq('M'+'A'*299)
        data=self.run_plan()['semantic_validation'];self.assertEqual(data['query_relation'],'HOMOLOGY_UNASSESSED')
        self.assertEqual(data['blast_selection'],'UNASSESSED')

    def test_ambiguous_cds_nucleotide_refused(self):
        start=int(self.record.features[0].location.start)
        self.record.seq=self.record.seq[:start+6]+Seq('N')+self.record.seq[start+7:]
        self.refuse('UNAMBIGUOUS_ATG_CDS_REQUIRED')

    def test_internal_stop_refused(self):
        start=int(self.record.features[0].location.start)
        self.record.seq=self.record.seq[:start+6]+Seq('TAA')+self.record.seq[start+9:]
        self.refuse('CDS_TRANSLATION_INVALID')

    def test_missing_terminal_stop_refused(self):
        end=int(self.record.features[0].location.end)
        self.record.seq=self.record.seq[:end-3]+Seq('GCG')+self.record.seq[end:]
        self.refuse('CDS_TRANSLATION_INVALID')

    def test_frame_length_refused(self):
        feature=self.record.features[0]
        feature.location=FeatureLocation(feature.location.start,int(feature.location.end)-1,strand=1)
        self.refuse('CDS_TRANSLATION_INVALID')

    def test_unsupported_start_codon_refused(self):
        start=int(self.record.features[0].location.start)
        self.record.seq=self.record.seq[:start]+Seq('GTG')+self.record.seq[start+3:]
        self.refuse('UNAMBIGUOUS_ATG_CDS_REQUIRED')

    def test_empty_cds_inventory_refused_before_publication(self):
        self.record.features=[];self.refuse('GENBANK_STRUCTURE_INVALID')

    def test_declared_subject_conflicts_with_other_exact_query_refused(self):
        f=copy.deepcopy(self.record.features[0]);dna=Seq('ATG'+'GCG'*299+'TAA');start=10000
        self.record.seq=self.record.seq[:start]+dna+self.record.seq[start+len(dna):]
        f.location=FeatureLocation(start,start+len(dna),strand=1);f.qualifiers['locus_tag']=['DECLARED_OTHER'];f.qualifiers['translation']=['M'+'A'*299]
        self.record.features.append(f);self.query['queries'][0]['enzyme_accession']='DECLARED_OTHER'
        self.refuse('DECLARED_SUBJECT_CONFLICTS_WITH_EXACT_QUERY')


if __name__=='__main__':unittest.main()
