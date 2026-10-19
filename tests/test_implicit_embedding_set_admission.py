"""Implicit kit selection must admit exact embedding-set coverage before any panel draws."""
from pathlib import Path
import os,importlib.util
import pytest
SOURCE=Path(os.environ.get('LANE06_RENDERER_SOURCE',Path(__file__).resolve().parents[1]/'tools/protein_pcoa_render.py'))
spec=importlib.util.spec_from_file_location('implicit_set_renderer',SOURCE);ppr=importlib.util.module_from_spec(spec);spec.loader.exec_module(ppr)
@pytest.mark.parametrize('mapping',['missing','extra'])
def test_implicit_selected_sets_require_exact_embedding_mapping(tmp_path,monkeypatch,mapping):
    kit=tmp_path/'kit';kit.mkdir();rows='id\tPC1\tPC2\tn_represented\tsource\tstrain\nSYN_R1\t0\t0\t1\treference\tSYN_R\nSYN_R2\t1\t1\t1\treference\tSYN_R\nSYN_Q1\t2\t2\t1\tisolate\tSYN_Q\n';tables={}
    for name in ['KS','AT']:
        directory=kit/('out_'+name);directory.mkdir();(directory/f'PCOA_{name}.tsv').write_text(rows);table=tmp_path/(name+'.tsv');table.write_text('id\tTRIMAP1\tTRIMAP2\nSYN_R1\t0\t0\nSYN_R2\t1\t1\nSYN_Q1\t2\t2\n');tables[name]=table
    cohort=tmp_path/'cohort.tsv';cohort.write_text('strain\tcohort\nSYN_Q\tg\n');draws=[]
    monkeypatch.setattr(ppr,'build_panel',lambda *a,**kw:draws.append(a[1]) or dict(set=a[1],panel='query'))
    mapping_rows={'KS':tables['KS']} if mapping=='missing' else dict(tables,EXTRA=tmp_path/'unused.tsv')
    argv=['--kit',str(kit),'--out',str(tmp_path/'out'),'--cohort-table',str(cohort),'--panel','query=g','--layout','trimap','--renderer','matplotlib']
    for name,path in mapping_rows.items():argv+=['--embedding-table',name+'='+str(path)]
    assert ppr.main(argv)==2
    assert not draws and not (tmp_path/'out/render_receipt.json').exists()
