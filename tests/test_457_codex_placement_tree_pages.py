import json
import pytest
from tools import placement_tree_pages as p

def inputs(tmp_path,args):
    f=tmp_path/'tree.nwk';f.write_text('(SYN_A:1,SYN_B:1);')
    a=tmp_path/'args.json';a.write_text(json.dumps(args))
    i=tmp_path/'inputs.tsv';i.write_text('path\ntree.nwk\n')
    return a,i

def test_reuses_display_route_and_preserves_caption(tmp_path):
    a,i=inputs(tmp_path,['SYN-run','--name','SYN-page','--caption-note','A supplied caption.'])
    cmd,paths=p.plan(a,i,tmp_path/'out')
    assert any(x.endswith('placement_display.py') for x in cmd)
    assert '--plot-only' in cmd and 'A supplied caption.' in cmd
    assert tmp_path/'tree.nwk' in paths

@pytest.mark.parametrize('bad',[['SYN-run','--out=/tmp/escape'],['SYN-run','--python','other'],['SYN-run','--rscript=other']])
def test_output_and_executable_override_refuse(tmp_path,bad):
    a,i=inputs(tmp_path,bad)
    with pytest.raises(ValueError):p.plan(a,i,tmp_path/'out')
