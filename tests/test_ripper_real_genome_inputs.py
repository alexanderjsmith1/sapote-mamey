"""Real-genome input scope for the RiPPER adapter: alternative bacterial start codons,
per-CDS exclusion of invalid translations, and the LOCUS-name contig identity.

All sequences are synthetic and built here; no RiPPER process is launched.
"""
import importlib.util
import json
import os
import random
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('ripper_real_genome_adapter', ROOT / 'tools/ripper_adapter.py')
adapter = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(adapter)
CONF = ROOT / 'tests/fixtures/ripper_semantic/fresh_run.conf.template'
PROFILE = 'archived-e90b3e6-mergeRidePfam'
try:
    from Bio import SeqIO
    from Bio.Seq import Seq
    from Bio.SeqFeature import SeqFeature, FeatureLocation
    from Bio.SeqRecord import SeqRecord
    HAVE_BIO = True
except ImportError:
    HAVE_BIO = False

CODON = {'A': 'GCG', 'C': 'TGC', 'D': 'GAC', 'E': 'GAA', 'F': 'TTC', 'G': 'GGC', 'H': 'CAC', 'I': 'ATC', 'K': 'AAA',
         'L': 'CTG', 'M': 'ATG', 'N': 'AAC', 'P': 'CCG', 'Q': 'CAG', 'R': 'CGC', 'S': 'AGC', 'T': 'ACC', 'V': 'GTG',
         'W': 'TGG', 'Y': 'TAC'}
CONTIG = 'NODE_1_length_457136_cov_55.054054'
MANGLED = 'NODE_1_length_457136_cov_55.54054'


def cds_dna(start, protein):
    """Start codon, then codons for protein[1:], then TAA. The first residue is M by rule."""
    return start + ''.join(CODON[a] for a in protein[1:]) + 'TAA'


def build_record(cdses, record_id=CONTIG, locus=CONTIG, length=12000):
    """cdses: list of (locus_tag, start_0based, dna, strand, translation)."""
    rng = random.Random(455)
    seq = list(''.join(rng.choice('ACGT') for _ in range(length)))
    features = []
    for tag, start, dna, strand, translation in cdses:
        placed = dna if strand == 1 else str(Seq(dna).reverse_complement())
        seq[start:start + len(placed)] = list(placed)
        f = SeqFeature(FeatureLocation(start, start + len(placed), strand=strand), type='CDS')
        f.qualifiers = {'locus_tag': [tag], 'transl_table': ['11'], 'translation': [translation]}
        features.append(f)
    record = SeqRecord(Seq(''.join(seq)), id=record_id, name=locus, description='synthetic real-genome scope fixture',
                       annotations={'molecule_type': 'DNA'}, features=features)
    return record


P_GTG = 'M' + 'ACDEFGHIKLNPQRSTVWY' * 4
P_TTG = 'M' + 'WYVTSRQPNLKIHGFEDCA' * 4
P_BAD = 'M' + 'KLMNPQRSTV' * 6


def standard_cdses():
    bad = cds_dna('ATG', P_BAD)
    bad = bad[:30] + 'TAG' + bad[33:]  # internal stop: the /translation qualifier cannot be computed
    return [('TE_GTG', 1000, cds_dna('GTG', P_GTG), 1, P_GTG),
            ('TE_TTG', 4000, cds_dna('TTG', P_TTG), -1, P_TTG),
            ('BAD_CDS', 8000, bad, 1, P_BAD)]


@unittest.skipUnless(HAVE_BIO, 'optional Biopython unavailable')
class RealGenomeInputScope(unittest.TestCase):
    def setUp(self):
        root = Path(os.environ.get('RIPPER_TEST_ROOT', tempfile.gettempdir())); root.mkdir(parents=True, exist_ok=True)
        self.work = Path(tempfile.mkdtemp(prefix=self._testMethodName + '-', dir=root)); self.out = self.work / 'output'

    def plan(self, record, subject, protein, full_contig=CONTIG):
        gbk = self.work / 'input.gbk'; faa = self.work / 'query.faa'; q = self.work / 'context.json'
        SeqIO.write(record, gbk, 'genbank'); faa.write_text('>query\n' + protein + '\n')
        q.write_text(json.dumps({'schema_version': 'ripper-queries/1', 'queries': [
            {'enzyme_accession': subject, 'strain': 'AS-SYN', 'full_contig': full_contig, 'region': 'region001', 'bgc_alias': 'SYN_BGC_1'}]}) + '\n')
        return adapter.local_plan(q, gbk, faa, CONF, self.out, PROFILE, True)['semantic_validation']

    def test_gtg_start_subject_is_admitted_and_translated_as_m(self):
        """Fail-before: the .463 adapter refuses any non-ATG CDS (UNAMBIGUOUS_ATG_CDS_REQUIRED)."""
        s = self.plan(build_record(standard_cdses()[:2]), 'TE_GTG', P_GTG)
        self.assertEqual(s['status'], 'PASS_INPUT_BINDING_ONLY')
        self.assertEqual(s['selected_subject_cds']['start_codon'], 'GTG')
        self.assertEqual(s['selected_subject_cds']['start_codon_rule'], 'TABLE_11_START_TRANSLATED_AS_M')
        self.assertEqual(s['query_relation'], 'EXACT_SEQUENCE_SELF_MATCH_ONLY')
        self.assertEqual(s['start_codon_counts'], {'GTG': 1, 'TTG': 1})

    def test_ttg_start_reverse_strand_subject_is_admitted(self):
        s = self.plan(build_record(standard_cdses()[:2]), 'TE_TTG', P_TTG)
        self.assertEqual(s['selected_subject_cds']['strand'], -1)
        self.assertEqual(s['selected_subject_cds']['start_codon'], 'TTG')

    def test_rare_table11_starts_admitted(self):
        for start in ('CTG', 'ATT', 'ATC', 'ATA'):
            with self.subTest(start=start):
                self.work = Path(tempfile.mkdtemp(prefix='rare-' + start + '-', dir=self.work)); self.out = self.work / 'output'
                s = self.plan(build_record([('TE_RARE', 1000, cds_dna(start, P_GTG), 1, P_GTG)]), 'TE_RARE', P_GTG)
                self.assertEqual(s['selected_subject_cds']['start_codon'], start)

    def test_gtg_is_not_a_start_under_table_1(self):
        record = build_record([('TE_GTG', 1000, cds_dna('GTG', P_GTG), 1, P_GTG)])
        record.features[0].qualifiers['transl_table'] = ['1']
        with self.assertRaisesRegex(ValueError, 'CDS_TRANSLATION_INVALID: subject CDS TE_GTG'):
            self.plan(record, 'TE_GTG', P_GTG)
        self.assertFalse(self.out.exists())

    def test_invalid_non_subject_cds_is_excluded_and_listed(self):
        """Fail-before: one invalid CDS anywhere refused the whole record."""
        s = self.plan(build_record(standard_cdses()), 'TE_GTG', P_GTG)
        self.assertEqual(s['status'], 'PASS_INPUT_BINDING_ONLY')
        self.assertEqual(s['cds_count'], 2)
        self.assertEqual(s['excluded_cds_count'], 1)
        bad = s['excluded_cds'][0]
        self.assertEqual((bad['subject_cds_id'], bad['reason']), ('BAD_CDS', 'LOCAL_SEMANTIC_CDS_TRANSLATION_INVALID'))
        self.assertIn('stop', bad['detail'])
        self.assertNotIn('BAD_CDS', [row['subject_cds_id'] for row in s['cds']])
        self.assertEqual(s['candidate_membership'], 'UNVERIFIED')

    def test_invalid_subject_cds_still_refuses(self):
        with self.assertRaisesRegex(ValueError, 'CDS_TRANSLATION_INVALID: subject CDS BAD_CDS'):
            self.plan(build_record(standard_cdses()), 'BAD_CDS', P_BAD)
        self.assertFalse(self.out.exists())

    def test_mismatched_translation_is_excluded_not_rewritten(self):
        cdses = standard_cdses()[:2] + [('MISMATCH', 8000, cds_dna('ATG', P_BAD), 1, 'M' + 'A' * 60)]
        s = self.plan(build_record(cdses), 'TE_GTG', P_GTG)
        self.assertEqual([(x['subject_cds_id'], x['reason']) for x in s['excluded_cds']],
                         [('MISMATCH', 'LOCAL_SEMANTIC_CDS_TRANSLATION_MISMATCH')])

    def test_excluded_cds_still_counts_for_exact_query_ambiguity(self):
        bad = cds_dna('ATG', P_GTG); bad = bad[:30] + 'TAG' + bad[33:]
        cdses = standard_cdses()[:1] + [('COPY_BAD', 8000, bad, 1, P_GTG)]
        with self.assertRaisesRegex(ValueError, 'AMBIGUOUS_EXACT_QUERY_MATCH'):
            self.plan(build_record(cdses), 'TE_GTG', P_GTG)

    def test_locus_name_identity_accepted_when_version_lost_leading_zero(self):
        """Fail-before: record.id is the VERSION form, so the real contig name was refused."""
        s = self.plan(build_record(standard_cdses()[:2], record_id=MANGLED, locus=CONTIG), 'TE_GTG', P_GTG, full_contig=CONTIG)
        self.assertEqual((s['record_id'], s['record_locus_name'], s['contig_identity_source']), (MANGLED, CONTIG, 'locus_name'))

    def test_contig_name_not_in_record_still_refused(self):
        with self.assertRaisesRegex(ValueError, 'RECORD_QUERY_CONTEXT_MISMATCH'):
            self.plan(build_record(standard_cdses()[:2]), 'TE_GTG', P_GTG, full_contig='NODE_1_length_457136_cov_55')


if __name__ == '__main__':
    unittest.main()
