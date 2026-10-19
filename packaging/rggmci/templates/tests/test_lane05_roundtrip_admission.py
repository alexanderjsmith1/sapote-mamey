"""Offline identity, stale-output and logical-label regressions; standard library only."""
import contextlib
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock
import zipfile

from rggmci import blastp, cli
from rggmci._blastp_io import fasta_header


def snapshot(root):
    return {str(p.relative_to(root)): ('link', os.readlink(p)) if p.is_symlink() else
            ('file', hashlib.sha256(p.read_bytes()).hexdigest()) if p.is_file() else ('dir',)
            for p in root.rglob('*')}


class RoundtripAdmission(unittest.TestCase):
    def setUp(self):
        # Preserve synthetic artifacts for the lane inventory and failure review.
        self.root = Path(tempfile.mkdtemp(prefix='lane05-'))
        self.source = self.root / 'input.zip'
        with zipfile.ZipFile(self.source, 'x') as z:
            z.writestr('SYNTH_FULL.1.region001.gbk', '\n'.join([
                'LOCUS       SYNTH_FULL.1              120 bp    DNA     linear   BCT 01-JAN-2000',
                'DEFINITION  Synthetic nonfunctional metadata fixture.', 'ACCESSION   SYNTH_FULL',
                'VERSION     SYNTH_FULL.1', 'FEATURES             Location/Qualifiers',
                '     region          1..120', '                     /product="other"',
                '                     /region_number="1"', '                     /contig_edge="True"',
                'ORIGIN', '        1 ' + 'n' * 60, '       61 ' + 'n' * 60, '//', '']))
        self.row = {'bgc_id': 'BGC001', 'slot': 1, 'selection_role': 'core', 'locus_tag': 'gene1',
                    'node_id': 'SYNTH_FULL.1', 'antismash_region': 'region001',
                    'start': 1, 'end': 120, 'aa_len': 40, 'selection_reason': 'rggmci_core'}
        self.header = fasta_header('GENOME_A', self.row)[1:]
        self.manifest = self.root / 'manifest.json'
        self.manifest.write_text(json.dumps({'genome': 'GENOME_A', 'proteins': [
            {**self.row, 'query_header': self.header}], 'pairs': []}))

    def hit(self, header):
        path = self.root / 'hits.csv'
        path.write_text(f'{header},WP_9.1,81.5,40,3,0,1,40,1,40,1e-10,90,90.1\n')
        return path

    def test_exact_emitted_query_is_admitted(self):
        layer = blastp.blastp_layer(self.manifest, [self.hit(self.header)])
        self.assertEqual(layer['proteins'][0]['blastp_status'], 'HIT')
        self.assertEqual(layer['unmapped_queries'], [])

    def test_other_genome_same_alias_gene_is_unmapped(self):
        query = self.header.replace('GENOME_A|', 'GENOME_B|')
        layer = blastp.blastp_layer(self.manifest, [self.hit(query)])
        self.assertEqual(layer['proteins'][0]['blastp_status'], 'NOT_IN_RESULTS')
        self.assertEqual(layer['unmapped_queries'], [query])

    def test_other_locus_same_alias_gene_is_unmapped(self):
        query = self.header.replace('node=SYNTH_FULL.1', 'node=OTHER_FULL.1')
        layer = blastp.blastp_layer(self.manifest, [self.hit(query)])
        self.assertEqual(layer['proteins'][0]['blastp_status'], 'NOT_IN_RESULTS')
        self.assertEqual(layer['unmapped_queries'], [query])

    def test_other_genome_xml_cannot_supply_metadata_to_valid_hit(self):
        query = self.header.replace('GENOME_A|', 'GENOME_B|')
        xml = self.root / 'other.xml'
        xml.write_text('<BlastXML2><BlastOutput2><report><Report><results><Results><search><Search>'
            f'<query-title>{query}</query-title><query-len>40</query-len><hits><Hit><description>'
            '<HitDescr><id>ref|WP_9.1|</id><accession>WP_9.1</accession><title>foreign protein</title>'
            '<sciname>Foreign organism</sciname></HitDescr></description><len>40</len><hsps><Hsp>'
            '<bit-score>90</bit-score><evalue>1e-10</evalue><identity>32</identity><align-len>40</align-len>'
            '</Hsp></hsps></Hit></hits></Search></search></Results></results></Report></report>'
            '</BlastOutput2></BlastXML2>')
        layer = blastp.blastp_layer(self.manifest, [self.hit(self.header)], [xml])
        self.assertEqual(layer['proteins'][0]['blastp_status'], 'HIT')
        self.assertFalse(layer['proteins'][0].get('top_organism'))
        self.assertEqual(layer['unmapped_queries'], [query])

    def test_admitted_distinct_locus_does_not_cross_merge_xml(self):
        # Both headers are admitted; an XML hit for locus B still cannot enrich locus A.
        other = self.header.replace('node=SYNTH_FULL.1', 'node=OTHER_FULL.1')
        m = json.loads(self.manifest.read_text())
        m['proteins'].append({**self.row, 'node_id': 'OTHER_FULL.1', 'query_header': other})
        self.manifest.write_text(json.dumps(m))
        xml = self.root / 'second.xml'
        xml.write_text('<BlastXML2><Search>' + f'<query-title>{other}</query-title><query-len>40</query-len>' +
            '<hits><Hit><description><HitDescr><id>WP_9.1</id><accession>WP_9.1</accession>' +
            '<title>Other locus protein</title><sciname>Other locus organism</sciname>' +
            '</HitDescr></description><len>40</len><hsps><Hsp><bit-score>90</bit-score>' +
            '<identity>32</identity><align-len>40</align-len></Hsp></hsps></Hit></hits></Search></BlastXML2>')
        layer = blastp.blastp_layer(self.manifest, [self.hit(self.header)], [xml])
        self.assertFalse(layer['proteins'][0].get('top_organism'))
        self.assertEqual(layer['proteins'][1]['top_organism'], 'Other locus organism')

    def test_duplicate_manifest_headers_refuse(self):
        m = json.loads(self.manifest.read_text()); m['proteins'] *= 2
        self.manifest.write_text(json.dumps(m))
        with self.assertRaisesRegex(ValueError, 'MANIFEST_QUERY'):
            blastp.blastp_layer(self.manifest)

    def test_layer_occupied_directory_is_unchanged(self):
        out = self.root / 'layer'; out.mkdir()
        (out / 'blastp_pairs.tsv').write_bytes(b'earlier evidence\x00')
        before = snapshot(self.root)
        with self.assertRaises(FileExistsError):
            blastp.write_layer({'proteins': [], 'pairs': []}, out)
        self.assertEqual(snapshot(self.root), before)

    def test_fasta_partial_directory_is_unchanged(self):
        out = self.root / 'queries'; out.mkdir()
        (out / 'input_blastp_01.fasta').write_text('earlier query evidence')
        before = snapshot(self.root)
        with self.assertRaises(FileExistsError):
            blastp.emit_fasta(self.source, {'ranked_pairs': []}, out)
        self.assertEqual(snapshot(self.root), before)

    def test_layer_symlink_directory_refuses(self):
        real = self.root / 'real'; real.mkdir()
        out = self.root / 'alias'; out.symlink_to(real, target_is_directory=True)
        before = snapshot(self.root)
        with self.assertRaises(FileExistsError):
            blastp.write_layer({'proteins': [], 'pairs': []}, out)
        self.assertEqual(snapshot(self.root), before)

    def test_fresh_and_empty_layer_outputs_have_headers(self):
        for name, empty in [('fresh', False), ('empty', True)]:
            out = self.root / name
            if empty: out.mkdir()
            blastp.write_layer({'proteins': [], 'pairs': []}, out)
            for leaf in ('blastp_proteins.tsv', 'blastp_pairs.tsv'):
                with (out / leaf).open() as fh:
                    table = csv.DictReader(fh, delimiter='\t')
                    self.assertTrue(table.fieldnames); self.assertEqual(list(table), [])

    def test_late_layer_file_is_preserved(self):
        out = self.root / 'layer'
        original = blastp._tsv
        def racing(path, cols, rows):
            if path.name == 'blastp_proteins.tsv': path.write_bytes(b'late evidence')
            return original(path, cols, rows)
        with mock.patch.object(blastp, '_tsv', racing):
            with self.assertRaises(FileExistsError):
                blastp.write_layer({'proteins': [], 'pairs': []}, out)
        self.assertEqual((out / 'blastp_proteins.tsv').read_bytes(), b'late evidence')

    def test_logical_label_survives_aggregate_and_per_genome_summary(self):
        out = self.root / 'results'
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main([str(self.source), '--label', 'LOGICAL_STRAIN', '--out-dir',
                                      str(out), '--reference-completion', 'off', '--threads', '1']), 0)
        for leaf in ('SUMMARY.tsv', 'input_summary.tsv'):
            with (out / leaf).open() as fh:
                self.assertEqual(list(csv.DictReader(fh, delimiter='\t'))[0]['genome'], 'LOGICAL_STRAIN')

    def test_logical_label_survives_aggregate_groups(self):
        out = self.root / 'groups'
        result = {'input': {'label': 'LOGICAL_STRAIN'}, 'regions': [], 'ranked_pairs': [],
                  'reference_completion': {'completion_tier': 'OFF'}, 'candidate_groups': [{
                      'group': 'G1', 'n_regions': 2, 'n_contigs': 2, 'n_at_contig_ends': 2,
                      'high_pairs': 1, 'regions': [], 'pairs': [], 'possible_moderate_links': []}]}
        with mock.patch.object(cli, 'run', return_value=result), contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main([str(self.source), '--out-dir', str(out)]), 0)
        with (out / 'CANDIDATE_GROUPS.tsv').open() as fh:
            self.assertEqual(list(csv.DictReader(fh, delimiter='\t'))[0]['genome'], 'LOGICAL_STRAIN')

    def test_layer_cli_returns_typed_refusal_and_preserves_old_evidence(self):
        hits = self.hit(self.header)
        out = self.root / 'layer'; out.mkdir()
        (out / 'blastp_layer.json').write_bytes(b'old layer bytes')
        before = snapshot(self.root)
        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            code = cli.main(['blastp-layer', '--manifest', str(self.manifest), '--hits', str(hits),
                             '--out-dir', str(out)])
        self.assertEqual(code, 2); self.assertIn('refused:', error.getvalue())
        self.assertEqual(snapshot(self.root), before)


if __name__ == '__main__': unittest.main()
