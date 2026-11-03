from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import gap_directed_rescue as gdr
import gap_rescue_all_regions as batch

@pytest.mark.parametrize('name',['gene_table.png','gene_table.pdf','map_and_table.png','map_and_table.pdf'])
def test_direct_refuses_stale_table_figure_before_writing(tmp_path,name):
    old=tmp_path/name;old.write_bytes(b'prior figure')
    with pytest.raises(ValueError,match='GAP_RESCUE_STALE_TABLE_FIGURE'):
        gdr.analyse_region('T',{},[],{},'unused.gbk','','',tmp_path,render_gene_table=False)
    assert old.read_bytes()==b'prior figure' and sorted(p.name for p in tmp_path.iterdir())==[name]

@pytest.mark.parametrize('flag',['--no-gene-table','--no-gene-table-figure'])
def test_batch_cli_refuses_stale_before_receipt(tmp_path,flag):
    out=tmp_path/'out';folder=out/'BGC001_vs_BGC0000001';folder.mkdir(parents=True)
    old=folder/'gene_table.png';old.write_bytes(b'prior figure')
    with pytest.raises(ValueError,match='GAP_RESCUE_STALE_TABLE_FIGURE'):
        batch.main(['--zip',str(tmp_path/'genome.zip'),'--label','T','--out',str(out),
                    '--mibig-dir',str(tmp_path),flag])
    assert old.read_bytes()==b'prior figure' and not (out/'run_receipt.json').exists()

def test_broken_figure_symlink_is_also_a_collision(tmp_path):
    (tmp_path/'gene_table.png').symlink_to(tmp_path/'missing')
    with pytest.raises(ValueError,match='GAP_RESCUE_STALE_TABLE_FIGURE'):
        gdr.assert_no_stale_table_figures(tmp_path)

def test_clean_folder_passes(tmp_path):
    gdr.assert_no_stale_table_figures(tmp_path)
    gdr.assert_no_stale_table_figures(tmp_path,batch=True)
