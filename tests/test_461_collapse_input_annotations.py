"""Annotation admission must not turn missing roles into reference metadata."""
import os,subprocess,sys
from pathlib import Path
import pytest
SCRIPT=Path(__file__).resolve().parents[1]/'tools/collapse_query_groups.py'
@pytest.mark.parametrize('text',[
 '', 'tip\tkind\n', 'tip\nCONTROL_A\n',
 'tip\tkind\nOTHER\treference\n',
 'tip\tkind\nCONTROL_A\treference\nCONTROL_A\treference\n',
 'tip\tkind\nCONTROL_A\tunknown\n',
 'tip\tkind\n\treference\n',
])
def test_invalid_annotations_refuse_before_output(tmp_path,text):
 tree=tmp_path/'control.nwk';tree.write_text('CONTROL_A:0.1;\n')
 ann=tmp_path/'source annotations.tsv';ann.write_text(text)
 p=subprocess.run([sys.executable,'-B',str(SCRIPT),str(tree),str(ann),str(tmp_path/'result')],capture_output=True,text=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
 assert p.returncode==2 and 'COLLAPSE_ANNOTATION' in p.stderr
 assert not list(tmp_path.glob('result*'))
 assert tree.read_text()=='CONTROL_A:0.1;\n' and ann.read_text()==text

def test_explicit_reference_annotation_stays_valid(tmp_path):
 tree=tmp_path/'control.nwk';tree.write_text('CONTROL_A:0.1;\n')
 ann=tmp_path/'annotations.tsv';ann.write_text('tip\tkind\nCONTROL_A\treference\n')
 p=subprocess.run([sys.executable,'-B',str(SCRIPT),str(tree),str(ann),str(tmp_path/'result')],capture_output=True,text=True)
 assert p.returncode==0
 assert '\treference\t' in (tmp_path/'result_ggtree_annotation.tsv').read_text()
