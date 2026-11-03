import json
from tests.test_450_gap_rescue_current_maps import batch_maps
from tests.test_450_gap_rescue_fresh_split_families import fresh_saved_split


def test_batch_suppresses_gene_table_but_keeps_search_results(batch_maps, monkeypatch):
    b=batch_maps; f=b.f
    monkeypatch.setattr(f.table,'write_gene_table',lambda *a,**k: (_ for _ in ()).throw(AssertionError('unexpected table')))
    rows=b.allr.run_all(f.out.parent/'SYNTHETIC.zip','SYNTHETIC',f.out,f.reference.parent,
                        f.db,{},f.pfam,False,'sensitive',3,False,gene_table=False)
    assert len(rows)==1 and rows[0]['check']=='run'
    assert f.calls==['reference','search','splits','checks']
    assert (b.folder/'gap_rescue.tsv').exists() and (b.folder/'gap_rescue_split_genes.tsv').exists()
    assert not (b.folder/'gene_table.tsv').exists()
    assert json.loads((f.out/'run_receipt.json').read_text())['gene_table_enabled'] is False


def test_command_line_passes_no_gene_table(batch_maps, monkeypatch, tmp_path):
    b=batch_maps; seen={}
    monkeypatch.setattr(b.allr,'run_all',lambda *a,**k:seen.update(k) or [])
    monkeypatch.setattr(b.allr.gdr,'load_mibig_names',lambda _: {})
    out=tmp_path/'cli_out'
    assert b.allr.main(['--zip',str(tmp_path/'x.zip'),'--label','T','--out',str(out),
                         '--mibig-dir',str(tmp_path),'--no-figure','--no-gene-table'])==0
    assert seen['gene_table'] is False
