"""Synthetic adapter-contract tests, not live RiPPER validation."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('ripper_adapter', ROOT / 'tools/ripper_adapter.py')
adapter = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(adapter)
FIXTURE = ROOT / 'tests/fixtures/ripper'


class AdapterTests(unittest.TestCase):
    def setUp(self):
        root = Path(os.environ.get('RIPPER_TEST_ROOT', tempfile.gettempdir()))
        root.mkdir(parents=True, exist_ok=True)
        self.work = Path(tempfile.mkdtemp(prefix=self._testMethodName+'-', dir=root))
        self.queries = FIXTURE / 'queries.json'
        self.receipt = FIXTURE / 'complete.json'
        self.raw = FIXTURE / 'synthetic.tsv'
        self.columns = FIXTURE / 'columns.json'
        self.config = FIXTURE / 'synthetic.conf'
        self.log = FIXTURE / 'synthetic_completion.log'
        self.out = self.work / 'output'

    def write(self, name, value):
        p = self.work / name
        p.write_text(json.dumps(value) if isinstance(value, (dict,list)) else value)
        return p

    def changed_receipt(self, **changes):
        data = json.loads(self.receipt.read_text())
        data.update(changes)
        self.receipt = self.write('receipt.json', data)

    def changed_raw(self, raw):
        self.raw = self.write('raw.tsv', raw)
        self.changed_receipt(raw_sha256=hashlib.sha256(raw.encode()).hexdigest())

    def run_import(self):
        return adapter.import_results(self.queries, self.receipt, self.out, self.raw, self.columns, self.config, self.log)

    def refused(self, message):
        with self.assertRaisesRegex(ValueError, message):
            self.run_import()
        self.assertFalse(self.out.exists())

    def test_plan_never_executes(self):
        with patch('subprocess.run', side_effect=AssertionError('execution forbidden')):
            data = adapter.plan(self.queries, self.out)
        self.assertEqual(data['plan_status'], 'PLANNED')
        self.assertEqual(data['upstream_execution'], 'NOT_EXECUTED')
        self.assertEqual((self.out / 'enzyme_accessions.txt').read_text(), 'SYNTHETIC_TE_001\nSYNTHETIC_TE_002\n')

    def test_candidates_keep_query_context_raw_fields_and_no_hit_query(self):
        data = self.run_import()
        self.assertEqual(data['candidate_count'], 1)
        self.assertEqual(data['candidates'][0]['query_identity'], 'SYNTHETIC / NODE_SYNTHETIC_full_contig_001 / region001 / SYNTHETIC_BGC_001')
        self.assertEqual(data['candidates'][0]['raw_fields']['uncalibrated_score'], '-2.5')
        self.assertEqual(data['assessments'][1]['assessment_status'], 'SYNTHETIC_NO_RETAINED_CANDIDATES')
        self.assertEqual(data['provenance_verification'], 'DECLARED_NOT_INDEPENDENTLY_ATTESTED')
        self.assertEqual(len(data['sources']), 6)

    def test_header_only_with_completion_is_scoped_no_hit(self):
        self.changed_raw('accession\tpid\taa\tuncalibrated_score\n')
        data = self.run_import()
        self.assertEqual(data['candidate_count'], 0)
        self.assertTrue(all(x['assessment_status'] == 'SYNTHETIC_NO_RETAINED_CANDIDATES' for x in data['assessments']))

    def test_noncomplete_states_do_not_report_zero_hits(self):
        for state in ('FAILED', 'UNAVAILABLE', 'NOT_RUN'):
            receipt = self.write(state+'.json', dict(schema_version='ripper-run/1', upstream=adapter.PROJECT,
                evidence_kind='synthetic_fixture', state=state, reason='Synthetic test of unavailable evidence'))
            data = adapter.import_results(self.queries, receipt, self.work / state)
            self.assertIsNone(data['candidate_count'])
            self.assertTrue(all(x['retained_candidate_count'] is None for x in data['assessments']))

    def test_failed_cannot_admit_stale_rows(self):
        self.changed_receipt(state='FAILED')
        self.refused('NONCOMPLETE_RESULTS_NOT_ADMITTED')

    def test_complete_needs_all_inputs(self):
        self.log = None
        self.refused('COMPLETE_REQUIRES_RAW_COLUMNS_CONFIG_LOG')

    def test_complete_needs_zero_exit(self):
        self.changed_receipt(exit_code=1)
        self.refused('COMPLETE_REQUIRES_ZERO_EXIT')

    def test_boolean_exit_is_not_zero(self):
        self.changed_receipt(exit_code=False)
        self.refused('COMPLETE_REQUIRES_ZERO_EXIT')

    def test_partial_coverage_is_not_no_hit(self):
        self.changed_receipt(completed_accessions=['SYNTHETIC_TE_001'])
        self.refused('COMPLETE_QUERY_COVERAGE_REQUIRED')

    def test_unknown_completion_state_refused(self):
        self.changed_receipt(state='UNKNOWN_SUCCESS')
        self.refused('RUN_RECEIPT_SCHEMA_INVALID')

    def test_unknown_provenance_kind_refused(self):
        self.changed_receipt(evidence_kind='inferred_live_success')
        self.refused('RUN_PROVENANCE_INVALID')

    def test_wrong_project_is_rejected(self):
        self.changed_receipt(upstream='https://example.invalid/rule-learning-ripper')
        self.refused('RUN_PROVENANCE_INVALID')

    def test_exact_raw_hash_is_required(self):
        self.changed_receipt(raw_sha256='0'*64)
        self.refused('RUN_RAW_OR_CONFIG_BINDING_MISMATCH')

    def test_exact_config_hash_is_required(self):
        self.changed_receipt(config_sha256='0'*64)
        self.refused('RUN_RAW_OR_CONFIG_BINDING_MISMATCH')

    def test_completion_log_hash_is_required(self):
        self.changed_receipt(completion_log_sha256='0'*64)
        self.refused('COMPLETION_LOG_BINDING_MISMATCH')

    def test_runtime_versions_required(self):
        self.changed_receipt(runtime_versions={})
        self.refused('DECLARED_RUNTIME_VERSIONS_REQUIRED')

    def test_revision_is_required(self):
        self.changed_receipt(upstream_revision='latest')
        self.refused('UPSTREAM_COMMIT_OR_IMAGE_DIGEST_REQUIRED')

    def test_unknown_headers_cannot_be_guessed(self):
        self.changed_raw('unknown\tpid\taa\n')
        self.refused('UPSTREAM_TSV_HEADER_MISMATCH')

    def test_duplicate_headers_refused(self):
        self.changed_raw('accession\tpid\taa\taa\n')
        self.refused('UPSTREAM_TSV_HEADER_MISMATCH')

    def test_unbound_accession_refused(self):
        self.changed_raw('accession\tpid\taa\nOTHER\tpep1\tMAGC\n')
        self.refused('UNBOUND_ENZYME_ACCESSION')

    def test_invalid_sequence_refused(self):
        self.changed_raw('accession\tpid\taa\nSYNTHETIC_TE_001\tpep1\tMAG*\n')
        self.refused('PEPTIDE_ID_OR_SEQUENCE_INVALID')

    def test_duplicate_peptide_refused(self):
        self.changed_raw('accession\tpid\taa\nSYNTHETIC_TE_001\tpep1\tMAGC\nSYNTHETIC_TE_001\tpep1\tMAGC\n')
        self.refused('DUPLICATE_QUERY_PEPTIDE')

    def test_ragged_row_refused(self):
        self.changed_raw('accession\tpid\taa\nSYNTHETIC_TE_001\tpep1\n')
        self.refused('UPSTREAM_TSV_ROW_INVALID')

    def test_full_identity_required(self):
        queries = json.loads(self.queries.read_text())
        queries['queries'][0]['full_contig'] = ''
        self.queries = self.write('queries.json', queries)
        self.refused('QUERY_FULL_LOCUS_IDENTITY_REQUIRED')

    def test_duplicate_query_mapping_refused(self):
        queries = json.loads(self.queries.read_text())
        queries['queries'].append(queries['queries'][0])
        self.queries = self.write('queries.json', queries)
        self.refused('QUERY_ACCESSION_MISSING_OR_DUPLICATE')

    def test_existing_output_preserved(self):
        self.out.mkdir()
        marker = self.out / 'owner.txt'
        marker.write_text('keep')
        with self.assertRaises(FileExistsError):
            self.run_import()
        self.assertEqual(marker.read_text(), 'keep')

    def test_output_inside_source_refused(self):
        self.out = ROOT / 'refused-output'
        self.refused('OUTPUT_MUST_BE_EXTERNAL_TO_SOURCE_TREE')

    def test_input_drift_refused_before_output(self):
        original = adapter.load_bytes
        counts = {}
        def drift(path):
            p = str(Path(path).resolve())
            counts[p] = counts.get(p, 0) + 1
            raw = original(path)
            return raw+b' ' if counts[p] > 1 else raw
        with patch.object(adapter, 'load_bytes', side_effect=drift):
            self.refused('INPUT_CHANGED_DURING_IMPORT')

    def test_oversize_is_bounded(self):
        with patch.object(adapter, 'MAX_BYTES', 20):
            self.refused('INPUT_TOO_LARGE')

    def test_symlink_input_refused(self):
        self.queries = self.work / 'linked.json'
        self.queries.symlink_to(FIXTURE / 'queries.json')
        self.refused('INPUT_NOT_REGULAR')

    def test_synthetic_revision_cannot_claim_live_operator_run(self):
        self.changed_receipt(evidence_kind='operator_supplied')
        self.refused('SYNTHETIC_REVISION_NOT_LIVE_PROVENANCE')

    def test_output_symlink_refused(self):
        self.out.symlink_to(self.work / 'target', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'OUTPUT_SYMLINK_REFUSED'):
            self.run_import()
        self.assertFalse((self.work / 'target').exists())

    def test_query_context_never_establishes_candidate_membership(self):
        data = self.run_import()
        candidate = data['candidates'][0]
        self.assertEqual(data['candidate_membership'], 'UNVERIFIED')
        self.assertEqual(candidate['candidate_membership'], 'UNVERIFIED')
        self.assertEqual(candidate['attribution_status'], 'HOLD_COORDINATE_ASSEMBLY_MAPPING')
        self.assertEqual(set(candidate['query_context']), set(adapter.IDENTITY))
        self.assertFalse(set(adapter.IDENTITY) & set(candidate))
        self.assertNotIn('identity', candidate)
        self.assertNotIn('state', candidate)

    def test_changed_query_locus_with_same_accessions_is_refused(self):
        for field in adapter.IDENTITY:
            with self.subTest(field=field):
                data = json.loads((FIXTURE / 'queries.json').read_text())
                data['queries'][0][field] += '_CHANGED'
                self.queries = self.write('changed_'+field+'.json', data)
                self.refused('RUN_QUERIES_BINDING_MISMATCH')

    def test_missing_query_hash_refused(self):
        self.changed_receipt(queries_sha256=None)
        self.refused('RUN_QUERIES_BINDING_MISMATCH')

    def test_changed_columns_mapping_refused(self):
        self.columns = self.write('changed_columns.json', dict(enzyme_accession='accession', peptide_id='uncalibrated_score', sequence='aa'))
        self.refused('RUN_COLUMNS_BINDING_MISMATCH')

    def test_missing_columns_hash_refused(self):
        self.changed_receipt(columns_sha256=None)
        self.refused('RUN_COLUMNS_BINDING_MISMATCH')

    def test_query_hash_binds_exact_bytes_even_when_semantics_unchanged(self):
        self.queries = self.write('reformatted_queries.json', self.queries.read_text()+'\n')
        self.refused('RUN_QUERIES_BINDING_MISMATCH')

    def test_columns_hash_binds_exact_bytes_even_when_semantics_unchanged(self):
        self.columns = self.write('reformatted_columns.json', self.columns.read_text()+'\n')
        self.refused('RUN_COLUMNS_BINDING_MISMATCH')

    def test_synthetic_complete_is_explicit_and_not_execution(self):
        data = self.run_import()
        self.assertEqual(data['schema_version'], 'ripper-evidence/2')
        self.assertEqual(data['import_status'], 'ADMITTED_SYNTHETIC')
        self.assertEqual(data['declared_upstream_state'], 'COMPLETE')
        self.assertEqual(data['evidence_kind'], 'synthetic_fixture')
        self.assertEqual(data['upstream_execution'], 'NOT_EXECUTED_SYNTHETIC')
        self.assertNotIn('state', data)
        for item in data['assessments']+data['candidates']:
            self.assertEqual(item['evidence_kind'], 'synthetic_fixture')
            self.assertEqual(item['upstream_execution'], 'NOT_EXECUTED_SYNTHETIC')
            self.assertNotIn('state', item)
        self.assertEqual(data['assessments'][0]['assessment_status'], 'SYNTHETIC_RETAINED_CANDIDATES')
        self.assertEqual(data['assessments'][1]['assessment_status'], 'SYNTHETIC_NO_RETAINED_CANDIDATES')

    def test_operator_complete_remains_unattested_at_every_level(self):
        # Artificial receipt exercises the branch; it is not a live execution claim.
        self.changed_receipt(evidence_kind='operator_supplied', upstream_revision='a'*40)
        data = self.run_import()
        self.assertEqual(data['import_status'], 'ADMITTED_OPERATOR_DECLARATION')
        self.assertEqual(data['upstream_execution'], 'OPERATOR_DECLARED_UNATTESTED')
        for item in data['assessments']+data['candidates']:
            self.assertEqual(item['evidence_kind'], 'operator_supplied')
            self.assertEqual(item['upstream_execution'], 'OPERATOR_DECLARED_UNATTESTED')
        self.assertEqual(data['assessments'][0]['assessment_status'], 'OPERATOR_DECLARED_RETAINED_CANDIDATES')
        self.assertEqual(data['assessments'][1]['assessment_status'], 'OPERATOR_DECLARED_NO_RETAINED_CANDIDATES')

    def test_noncomplete_declarations_are_qualified_and_null(self):
        for kind in ('synthetic_fixture', 'operator_supplied'):
            for state in ('FAILED', 'UNAVAILABLE', 'NOT_RUN'):
                receipt = self.write(kind+'_'+state+'.json', dict(schema_version='ripper-run/1', upstream=adapter.PROJECT,
                    evidence_kind=kind, state=state, reason='Artificial receipt for contract test only'))
                data = adapter.import_results(self.queries, receipt, self.work / (kind+'_'+state))
                self.assertEqual(data['declared_upstream_state'], state)
                self.assertIsNone(data['candidate_count'])
                for item in data['assessments']:
                    self.assertIsNone(item['retained_candidate_count'])
                    self.assertEqual(item['upstream_execution'], data['upstream_execution'])
                    self.assertTrue(item['assessment_status'].endswith('_DECLARED_'+state))

    def test_cli_synthetic_and_operator_import_disclose_execution(self):
        for kind, revision, expected in (('synthetic_fixture', '0'*40, 'NOT_EXECUTED_SYNTHETIC'),
                                         ('operator_supplied', 'a'*40, 'OPERATOR_DECLARED_UNATTESTED')):
            self.changed_receipt(evidence_kind=kind, upstream_revision=revision)
            with self.assertLogs(adapter.LOG, level='INFO') as captured:
                code = adapter.main(['import', '--queries', str(self.queries), '--receipt', str(self.receipt),
                    '--raw', str(self.raw), '--columns', str(self.columns), '--config', str(self.config),
                    '--completion-log', str(self.log), '--out', str(self.work / kind)])
            self.assertEqual(code, 0)
            line = '\n'.join(captured.output)
            self.assertIn('evidence_kind='+kind, line)
            self.assertIn('upstream_execution='+expected, line)
            self.assertIn('declared_upstream_state=COMPLETE', line)
            self.assertNotIn('adapter COMPLETE', line)

    def test_cli_failure_is_nonzero(self):
        self.assertEqual(adapter.main(['import', '--queries', str(self.queries), '--receipt', str(self.receipt), '--out', str(self.out)]), 2)
        self.assertFalse(self.out.exists())


if __name__ == '__main__':
    unittest.main()
