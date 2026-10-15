"""Bundle code carries no real isolate IDs, and T06 label nudges come from the figure-side cohort table.

Codex's T06 card named four isolates (two of them not in tools/test_synthetic_ids.txt) in a comment inside the
embedded R script, next to label nudges that the tool in fact reads from the cohort table's nudge_x/nudge_y
columns. The nudge values belong to the figure's input table, never to bundle code. Single-digit placeholders
(AS-1 ... AS-9) used in docstrings and examples are not isolate IDs; any AS ID of two or more digits in code must
be one of the listed synthetic IDs.
"""
import csv
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SYNTHETIC = {l.strip() for l in (ROOT / 'tools/test_synthetic_ids.txt').read_text().splitlines()
             if l.strip() and not l.startswith('#')}


def test_bundle_code_holds_no_non_synthetic_isolate_ids():
    found = {}
    for top in ('tools', 'mamey', 'deliverable_tools'):
        for p in (ROOT / top).rglob('*'):
            if p.is_file() and p.suffix in ('.py', '.R', '.sh'):
                ids = set(re.findall(r'\bAS-\d{2,}\b', p.read_text(errors='replace'))) - SYNTHETIC
                if ids:
                    found[str(p.relative_to(ROOT))] = sorted(ids)
    assert not found, found


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
