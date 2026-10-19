"""Optional source identifier diagnostics; names alone require no universal admission.

Exact role semantics remain testable through the diagnostic helper. Genuine names and
strain/class associations alone are permitted. This scanner grants neither synthetic
identity nor publication authority. T06 label nudges remain figure-side behavior.
"""
import csv
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _identifier_role_policy import reviewed_public_sites
POLICY = Path(__file__).with_name("reviewed_public_reference_sites.json")

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC = {l.strip() for l in (ROOT / 'tools/test_synthetic_ids.txt').read_text().splitlines()
             if l.strip() and not l.startswith('#')}


def _unreviewed_code_ids(root, allowed, policy_path):
    found = {}
    for top in ('tools', 'mamey', 'deliverable_tools'):
        for p in (root / top).rglob('*'):
            if p.is_file() and p.suffix in ('.py', '.R', '.sh'):
                raw = p.read_bytes()
                text = raw.decode(errors='replace')
                public = reviewed_public_sites(root, p, raw, policy_path)
                ids = set()
                for match in re.finditer(r'\bAS-\d{2,}\b', text):
                    start = len(text[:match.start()].encode())
                    end = len(text[:match.end()].encode())
                    if match[0] not in allowed and (start, end) not in public:
                        ids.add(match[0])
                if ids:
                    found[str(p.relative_to(root))] = sorted(ids)
    return found




def test_t06_label_nudges_are_read_from_the_cohort_table(tmp_path):
    if not shutil.which('Rscript'):
        pytest.skip('Rscript not installed')
    cohort = tmp_path / 'cohort.tsv'; data = tmp_path / 'data.tsv'
    cohort.write_text('strain\tgenus\tblock\tlabel_suffix\tnudge_x\tnudge_y\n'
                      'AS-971\tStreptomyces\tisolates\t\t-0.35\t14\nAS-972\tNocardia\tisolates\t\t0\t0\n')
    data.write_text('strain\tsimilarity\td4\nAS-971\t99\t77.6\nAS-972\t98\t30\n')
    out = tmp_path / 'figure'
    r = subprocess.run([sys.executable, str(ROOT / 'tools/taxonomy_T06_figures.py'), '--cohort', str(cohort), '--data', str(data),
                        '--out', str(out), '--layout', 'bee', '--dpi', '72'], capture_output=True, text=True, timeout=180)
    assert r.returncode == 0, r.stdout + r.stderr
    rows = {x['strain']: x for x in json.loads((tmp_path / 'figure_run.json').read_text())['plotted_values']}
    assert (rows['AS-971']['nudge_x'], rows['AS-971']['nudge_y']) == (-0.35, 14.0)
    assert (rows['AS-972']['nudge_x'], rows['AS-972']['nudge_y']) == (0.0, 0.0)
