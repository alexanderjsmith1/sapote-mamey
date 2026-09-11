import csv, os, shutil, subprocess
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
@pytest.fixture
def render_case(tmp_path):
    r=shutil.which('Rscript')
    if not r: pytest.skip('R graphics stack not installed')
    probe=subprocess.run([r,'-e','quit(status=if(all(sapply(c("ape","ggtree","ggplot2","aplot","treeio","patchwork"),requireNamespace,quietly=TRUE))) 0 else 1)'],capture_output=True)
    if probe.returncode:pytest.skip('R graphics packages not installed')
    tree=tmp_path/'tree with spaces.nwk';tree.write_text('((REF_A:0.02,REF_B:0.02):0.02,(QUERY_A:0.02,REF_C:0.02):0.02,OUTGROUP_REF:0.02);')
    meta=tmp_path/'labels.tsv'
    with meta.open('w') as f:
        w=csv.writer(f,delimiter='\t');w.writerow(['tip','label','category','source'])
        for key in ['REF_A','REF_B','QUERY_A','REF_C','OUTGROUP_REF']:w.writerow([key,key+' [plant] (NR_123456.1)','plant','recorded region'])
    def run(**env):
        target=tmp_path/'figure'
        cp=subprocess.run([r,str(ROOT/'tools/ggtree_rect_heatmap.R'),str(tree),str(meta),str(target),'QUERY_A'],capture_output=True,text=True,env=dict(os.environ,SAPOTE_PYTHON=shutil.which('python3'),**env),timeout=120)
        return cp,target
    return run,meta,tree

def test_renderer_runs_with_titled_optional_strips(render_case):
    run,_,_=render_case
    cp,out=run(GG_STRIPS='2',GG_FIGID='Figure display test',GG_STRIP1_TITLE='Habitat',GG_STRIP2_TITLE='Location')
    assert cp.returncode==0,cp.stdout+cp.stderr
    assert out.with_suffix('.pdf').stat().st_size>1000
    assert Path(str(out)+'.session.txt').exists()

def test_missing_metadata_row_refuses(render_case):
    run,meta,_=render_case;lines=meta.read_text().splitlines();meta.write_text('\n'.join(lines[:-1])+'\n')
    cp,out=run();assert cp.returncode!=0;assert 'tip sets must match exactly' in cp.stderr
    assert not out.with_suffix('.pdf').exists()

def test_unbound_parent_cannot_authorize_another_tree(render_case):
    run,_,tree=render_case;parent=tree.with_name('other.nwk');parent.write_text(tree.read_text())
    cp,out=run(GG_GATE_TREE=str(parent));assert cp.returncode!=0
    assert 'hash-bound display receipt' in cp.stderr;assert not out.with_suffix('.pdf').exists()
