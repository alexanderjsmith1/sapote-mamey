"""Synthetic metadata regression; no phylogenetic computation or figure rendering."""
import csv
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'tools/build_placement_panel_inputs.py'
spec = importlib.util.spec_from_file_location('placement_under_test', TARGET)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def write_tsv(path, columns, rows):
    with path.open('w', newline='') as h:
        writer = csv.DictWriter(h, fieldnames=columns, delimiter='\t')
        writer.writeheader()
        writer.writerows(rows)


def read_tsv(path):
    with path.open() as handle:
        return list(csv.DictReader(handle, delimiter='\t'))


class MissingHost(unittest.TestCase):
    def test_missing_matrix(self):
        for value in ('', 'not recorded', 'missing', 'n/a', 'na', 'none', 'unknown', 'not applicable', 'not collected'):
            for prefix in ('', 'host:', ' HOST:  '):
                with self.subTest(value=value, prefix=prefix):
                    self.assertEqual(mod.bin_source(prefix + value.upper() + ' '), ('', False))

    def test_documented_rules_unchanged(self):
        for value, expected in [('Apis mellifera', ('Honeybee', True)), ('soil', ('Soil', True)), ('unlisted substrate', ('Other documented', False)), ('unknown bacterium', ('Other documented', False))]:
            self.assertEqual(mod.bin_source(value), expected)
            self.assertEqual(mod.bin_source('host: ' + value), expected)

    def test_main_omits_missing_host_and_preserves_documented_verbatim(self):
        with tempfile.TemporaryDirectory(prefix='placement_host_', dir=os.path.realpath(tempfile.gettempdir())) as raw:
            p = Path(raw)
            tips = ['AB123_1_missing', 'AB124_1_documented', 'AB125_1_unknown_documented', 'AB126_1_reviewed']
            (p/'tree').write_text('(' + ','.join(tips) + ');\n')
            write_tsv(p/'labels', ['safe','original'], [dict(safe=t, original=t.split('_')[0]+'.1 Streptomyces example strain X 16S rRNA') for t in tips])
            write_tsv(p/'owner', ['tip','label','source_category','geography_category'], [])
            write_tsv(p/'resolved', ['exact_accession','verification_status','isolation_source','host','location'], [dict(exact_accession='AB'+str(123+i)+'.1', verification_status='STRAIN_CONFIRMED', isolation_source='', host=h, location='Canada') for i,h in enumerate(['unknown', 'Apis mellifera', 'unlisted substrate', 'not recorded'])])
            write_tsv(p/'reviewed', ['accession','source_category','isolation_source','evidence_url'], [dict(accession='AB126.1', source_category='Soil', isolation_source='reviewed soil record', evidence_url='https://example.org/review')])
            receipt = mod.main(['--genus','Synthetic','--tree',str(p/'tree'),'--labelmap',str(p/'labels'),'--owner-table',str(p/'owner'),'--resolved',str(p/'resolved'),'--reviewed',str(p/'reviewed'),'--out',str(p/'output')])
            self.assertEqual(receipt['kept'], 3)
            self.assertEqual(receipt['omitted_tips'], [tips[0]])
            out=p/'output/Synthetic'
            rows=read_tsv(out/'metadata.tsv')
            self.assertEqual({r['tip']:r['source_category'] for r in rows}, {tips[1]:'Honeybee', tips[2]:'Other documented', tips[3]:'Soil'})
            prov=read_tsv(out/'METADATA_PROVENANCE.tsv')
            self.assertTrue(any(r['tip']==tips[1] and r['verbatim']=='host: Apis mellifera' for r in prov))
            self.assertFalse(any(r['tip']==tips[0] and r['field']=='source' for r in prov))
            omitted=read_tsv(out/'OMITTED_TIPS.tsv')
            self.assertIn('no deposited or reviewed isolation source', omitted[0]['reason'])

if __name__ == '__main__':
    unittest.main(verbosity=2)
