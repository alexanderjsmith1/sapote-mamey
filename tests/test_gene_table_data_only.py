import json
from tests.test_450_gap_rescue_current_maps import batch_maps
from tests.test_450_gap_rescue_fresh_split_families import fresh_saved_split


def test_batch_retains_tables_without_rendering(batch_maps, monkeypatch):
    b=batch_maps; f=b.f
    monkeypatch.setattr(f.table,'_draw',lambda *a,**k: (_ for _ in ()).throw(AssertionError('unexpected draw')))
    rows=b.allr.run_all(f.out.parent/'SYNTHETIC.zip','SYNTHETIC',f.out,f.reference.parent,
                       f.db,{},f.pfam,False,'sensitive',3,False,render_gene_table=False)
    assert len(rows)==1 and rows[0]['check']=='run'
    assert (b.folder/'gene_table.tsv').exists() and (b.folder/'gene_table_counts.tsv').exists()
    assert not (b.folder/'gene_table.png').exists() and not (b.folder/'gene_table.pdf').exists()
    receipt=json.loads((f.out/'run_receipt.json').read_text())
    assert receipt['gene_table_enabled'] is True and receipt['gene_table_figure_enabled'] is False


def test_cli_propagates_data_only_flag(batch_maps,monkeypatch,tmp_path):
    b=batch_maps;seen={}
    monkeypatch.setattr(b.allr,'run_all',lambda *a,**k:seen.update(k) or [])
    monkeypatch.setattr(b.allr.gdr,'load_mibig_names',lambda _: {})
    assert b.allr.main(['--zip',str(tmp_path/'x.zip'),'--label','T','--out',str(tmp_path/'out'),
                        '--mibig-dir',str(tmp_path),'--no-figure','--no-gene-table-figure'])==0
    assert seen['gene_table'] is True and seen['render_gene_table'] is False


def test_direct_cli_refuses_data_only_flag_for_redraw(monkeypatch,tmp_path):
    import sys,importlib,pytest
    monkeypatch.syspath_prepend(str(__import__('pathlib').Path(__file__).resolve().parents[1]/'tools'))
    gdr=importlib.import_module('gap_directed_rescue')
    with pytest.raises(SystemExit,match='for fresh analysis, not --redraw'):
        gdr.main(['--zip',str(tmp_path/'x.zip'),'--label','T','--redraw',str(tmp_path/'prior'),
                  '--no-gene-table-figure'])
