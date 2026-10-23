import csv,json
from pathlib import Path
import pytest
from tools import bioassay_paper_set as b
from tools._figure_route_common import sha

def spec(tmp_path, **overrides):
    for n in ('table','roster','aliases','lock'):(tmp_path/n).write_text('synthetic '+n)
    r=dict(name='SYN-panel',layout='bee',panel='a03',material='Crude extract',table='table',roster='roster',aliases='aliases',lock='lock',table_sha256=sha(tmp_path/'table'),lock_sha256=sha(tmp_path/'lock'),point_labels='genus',repel_seed='3')
    r.update(overrides)
    p=tmp_path/'spec.tsv'
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,list(r),delimiter='\t');w.writeheader();w.writerow(r)
    return p

def test_preserves_material_and_uses_bound_files(tmp_path):
    p=spec(tmp_path);jobs,inputs=b.plan(p,tmp_path/'out')
    n,cmd,env=jobs[0]
    assert cmd[cmd.index('--material')+1]=='Crude extract'
    assert cmd[cmd.index('--table')+1]==str(tmp_path/'table')
    assert env['BIOASSAY_REPEL_SEED']=='3'
    assert (tmp_path/'table') in inputs

@pytest.mark.parametrize('changes',[{'name':'../escape'},{'panel':'a05'},{'material':'negative'},{'table_sha256':'0'*64},{'bar_labels':'yes'}])
def test_refuses_invalid_or_unbound_jobs(tmp_path,changes):
    with pytest.raises(ValueError):b.plan(spec(tmp_path,**changes),tmp_path/'out')

def test_dry_run_never_executes_renderer(tmp_path,monkeypatch):
    p=spec(tmp_path)
    monkeypatch.setattr(b,'execute',lambda *a,**k:pytest.fail('renderer executed'))
    assert b.main(['--spec',str(p),'--out',str(tmp_path/'out'),'--dry-run'])==0
    r=json.loads((tmp_path/'out/ROUTE_RECEIPT.json').read_text())
    assert r['runtime_state']=='DRY_RUN_ONLY' and r['visual_qa']=='NOT_PERFORMED'


def test_svg_geometry_preserves_source_overlap_rule(tmp_path):
    from tools.bioassay_route_records import overlaps
    f=tmp_path/'scatter.svg'
    f.write_text("<svg><text x='10' y='10' style='font-size: 8px; font-family: Arial;' textLength='15px'>SYN_A</text><circle cx='15' cy='7' r='2' style='stroke: #17212E;'/></svg>")
    result=overlaps(f,['SYN_A'])
    assert result['detected_labels']==1 and result['detected_point_marks']==1 and len(result['problems'])==1
    assert result['visual_qa']=='NOT_PERFORMED'

def test_render_requires_approved_methods_context(tmp_path):
    p=spec(tmp_path)
    with pytest.raises(ValueError,match='methods-context'):
        b.main(['--spec',str(p),'--out',str(tmp_path/'out')])
    assert not (tmp_path/'out').exists()
