"""Fresh output paths must preserve source trees, annotations and earlier records."""
import os,subprocess,sys
from pathlib import Path
import pytest
SCRIPT=Path(__file__).resolve().parents[1]/'tools/collapse_query_groups.py'
@pytest.mark.parametrize('collision',['tree_source','annotation_source','old_groups','symlink_tree','broken_symlink'])
def test_existing_output_refused_before_any_write(tmp_path,collision):
 prefix=tmp_path/'result';tree=tmp_path/'source.nwk';ann=tmp_path/'source.tsv'
 tree.write_text('CONTROL_A:0.1;\n');ann.write_text('tip\tkind\nCONTROL_A\treference\n')
 if collision=='tree_source':tree=tmp_path/'result_pruned.nwk';tree.write_text('CONTROL_A:0.1;\n')
 if collision=='annotation_source':ann=tmp_path/'result_ggtree_annotation.tsv';ann.write_text('tip\tkind\nCONTROL_A\treference\n')
 if collision=='old_groups':(tmp_path/'result_groups.tsv').write_text('preserve earlier output\n')
 if collision=='symlink_tree':(tmp_path/'result_pruned.nwk').symlink_to(tree)
 if collision=='broken_symlink':(tmp_path/'result_pruned.nwk').symlink_to(tmp_path/'absent target')
 before={p.name:('symlink',os.readlink(p)) if p.is_symlink() else ('file',p.read_bytes()) for p in tmp_path.iterdir()}
 result=subprocess.run([sys.executable,'-B',str(SCRIPT),str(tree),str(ann),str(prefix)],capture_output=True,text=True)
 assert result.returncode==2 and 'COLLAPSE_OUTPUT_EXISTS' in result.stderr
 after={p.name:('symlink',os.readlink(p)) if p.is_symlink() else ('file',p.read_bytes()) for p in tmp_path.iterdir()}
 assert after==before

def test_fresh_prefix_still_writes(tmp_path):
 tree=tmp_path/'source.nwk';tree.write_text('CONTROL_A:0.1;\n');ann=tmp_path/'source.tsv';ann.write_text('tip\tkind\nCONTROL_A\treference\n')
 p=subprocess.run([sys.executable,'-B',str(SCRIPT),str(tree),str(ann),str(tmp_path/'fresh')],capture_output=True,text=True)
 assert p.returncode==0 and len(list(tmp_path.glob('fresh*')))==3
 assert tree.read_text()=='CONTROL_A:0.1;\n'
