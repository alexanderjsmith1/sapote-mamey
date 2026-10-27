import copy
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("scope", Path(__file__).parents[1] / "tools/retained_rescue_search_scope.py")
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
IDENTITY = 'DEMO / NODE_1_length_5000_cov_20 / region001 / BGC001'


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.h = hashlib.sha256(b'ACDE').hexdigest()
        self.receipt = {'core': IDENTITY, 'reference': 'BGC0001792.gbk', 'reference_genes': 1,
                        'present_in_core': 1, 'missing_found_clear': 0, 'missing_found_ambiguous': 0, 'missing_not_found': 0}
        self.rows = [{'reference_gene': '1', 'name': 'refGene', 'reference_len_aa': '10', 'status': 'PRESENT_IN_CORE',
                      'best_protein': 'q1', 'best_locus': 'ctg1_1', 'best_len_aa': '4', 'best_region_identity': IDENTITY,
                      'best_identity_pct': '50', 'best_coverage_pct': '60'}]
        self.inv = [{'identity': IDENTITY, 'locus_tag': 'ctg1_1', 'protein_sha256': self.h},
                    {'identity': IDENTITY, 'locus_tag': 'ctg1_2', 'protein_sha256': self.h}]
        self.subjects = {'q1': {'length': 4, 'sha256': self.h}}
        self.ref = [{'reference_id': 'BGC0001792', 'reference_gene_id': '1', 'reference_name': 'refGene', 'reference_length_aa': '10'}]

    def run_case(self): return m.account(self.receipt, self.rows, self.inv, self.subjects, self.ref)

    def test_positive_pair_bound_without_inventing_other_outcomes(self):
        observed, positive, summary = self.run_case()
        self.assertEqual(len(positive), 1)
        self.assertEqual(positive[0]['state'], 'MATCHED')
        self.assertEqual(summary['AS_genes_not_evaluated_from_selected_outcomes'], 1)
        self.assertEqual(summary['searched_no_hit_AS_genes_exported'], 0)

    def test_reference_missing_not_found_never_inverts_to_AS_nohit(self):
        self.rows[0]['status'] = 'MISSING_NOT_FOUND'; self.receipt['present_in_core'] = 0; self.receipt['missing_not_found'] = 1
        observed, positive, summary = self.run_case()
        self.assertFalse(positive)
        self.assertIn('never inverted', observed[0]['reason'])

    def test_external_ambiguous_rows_stay_candidates(self):
        for status in ['MISSING_FOUND_CLEAR', 'MISSING_FOUND_AMBIGUOUS']:
            self.rows[0]['status'] = status
            self.receipt.update(present_in_core=0, missing_found_clear=int(status.endswith('CLEAR')),
                                missing_found_ambiguous=int(status.endswith('AMBIGUOUS')))
            observed, positive, summary = self.run_case()
            self.assertFalse(positive)

    def test_current_sequence_change_holds_pair(self):
        self.inv[0]['protein_sha256'] = '0' * 64
        observed, positive, summary = self.run_case()
        self.assertFalse(positive)
        self.assertEqual(summary['pair_binding_holds'][0]['reason'], 'CURRENT_GENE_SEQUENCE_DIFFERS_FROM_SAVED_SUBJECT')

    def test_current_reference_roster_change_holds_pair(self):
        self.ref[0]['reference_name'] = 'different'
        _, positive, summary = self.run_case()
        self.assertFalse(positive)
        self.assertEqual(summary['pair_binding_holds'][0]['reason'], 'CURRENT_REFERENCE_ROSTER_HOLD')

    def test_invalid_metric_or_subject_length_holds(self):
        for key, value in [('best_identity_pct', 'nan'), ('best_coverage_pct', '101'), ('best_len_aa', '5')]:
            saved = self.rows[0][key]; self.rows[0][key] = value
            _, positive, summary = self.run_case(); self.assertFalse(positive)
            self.rows[0][key] = saved

    def test_wrong_focal_location_not_adopted(self):
        self.rows[0]['best_region_identity'] = IDENTITY.replace('region001', 'region002')
        _, positive, summary = self.run_case(); self.assertFalse(positive)

    def test_duplicate_or_missing_reference_outcomes_fail(self):
        self.rows.append(dict(self.rows[0])); self.receipt['reference_genes'] = 2
        with self.assertRaisesRegex(ValueError, 'REFERENCE_ROW_ID_HOLD'): self.run_case()
        self.rows = []; self.receipt['reference_genes'] = 1
        with self.assertRaisesRegex(ValueError, 'DENOMINATOR'): self.run_case()

    def test_unknown_status_and_receipt_count_mismatch_fail(self):
        self.rows[0]['status'] = 'NO_HIT'
        with self.assertRaisesRegex(ValueError, 'UNKNOWN_SOURCE_STATUS'): self.run_case()
        self.rows[0]['status'] = 'PRESENT_IN_CORE'; self.receipt['present_in_core'] = 0
        with self.assertRaisesRegex(ValueError, 'RECEIPT_STATUS_COUNTS_HOLD'): self.run_case()

    def test_malformed_protein_pin_and_identity_fail(self):
        self.inv[0]['protein_sha256'] = 'x'
        with self.assertRaisesRegex(ValueError, 'INVENTORY_BINDING_HOLD'): self.run_case()
        self.inv[0]['protein_sha256'] = self.h; self.receipt['core'] = 'DEMO / BGC001'
        with self.assertRaisesRegex(ValueError, 'FOCAL_IDENTITY_HOLD'): self.run_case()

    def test_saved_fasta_normalization_and_invalid_strings(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'saved.faa'; p.write_text('>q1\nac de*\n')
            self.assertEqual(m.read_fasta(p), self.subjects)
            p.write_text('>q1\nACDE\n>q1\nACDE\n')
            with self.assertRaisesRegex(ValueError, 'DUPLICATE_FASTA_IDENTIFIER'): m.read_fasta(p)
            p.write_text('>q1\nAC*DE\n')
            with self.assertRaisesRegex(ValueError, 'INVALID_SAVED_PROTEIN_STRING'): m.read_fasta(p)

    def test_source_pin_mismatch_fails_before_export(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / 'source.json'; p.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'SOURCE_PIN_HOLD'):
                m.build({'sources': {'receipt': {'path': str(p), 'sha256': '0' * 64}}})


if __name__ == '__main__': unittest.main()
