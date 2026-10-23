import csv
import os
from pathlib import Path
import shutil
import subprocess
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
TOOL=ROOT/'tools/taxonomy_T06_figures.py'
@pytest.mark.parametrize('layout',['bee','moss'])
@pytest.mark.needs_arial
def test_printed_layout_stamp_numbers(tmp_path,layout):
    if not shutil.which('Rscript'): pytest.skip('Rscript not installed')
    cohort=tmp_path/'cohort.tsv'; data=tmp_path/'data.tsv'
    cohort.write_text('strain\tgenus\tblock\nSYN-971\tStreptomyces\tisolates\nSYN-972\tNocardia\tisolates\nSYN-973\tNocardia\tisolates\n')
    data.write_text('strain\tsimilarity\td4\td4_ci_low\td4_ci_high\ttype_strain\nSYN-971\t99\t77.6\t76\t79\tStreptomyces example\nSYN-972\t98\t30\t29\t31\tNocardia example\nSYN-973\t\t40\t39\t41\tNocardia example\n')
    command=[sys.executable,str(TOOL),'--cohort',str(cohort),'--data',str(data),'--out',str(tmp_path/'figure'),'--layout',layout,'--dpi','72']
    if layout=='moss': command+=['--palette-set','moss']
    result=subprocess.run(command,capture_output=True,text=True,timeout=120)
    assert result.returncode==0,result.stdout+result.stderr
    for suffix in ['png','pdf']: assert b'Sapote-Mamey taxonomy_T06_figures' in (tmp_path/f'figure.{suffix}').read_bytes()
    with (tmp_path/'figure_numbers.tsv').open() as f: nums={r['metric']:int(r['count']) for r in csv.DictReader(f,delimiter='\t')}
    assert nums['cohort_rows']==3
    assert nums['plotted_rows']==(3 if 'T06'=='T05' else 2)
    if 'T06'!='T01': assert nums['d4_at_least_70']==1
    else: assert nums['similarity_below_98.65']==1
    again=subprocess.run(command,capture_output=True,text=True)
    assert again.returncode!=0 and 'overwrite' in again.stderr

def test_portable_palette_source():
    text=TOOL.read_text()
    import re
    assert not re.search(r'#[0-9A-Fa-f]{6}',text.split('R_SCRIPT =')[0])
    assert '/Users/' not in text
