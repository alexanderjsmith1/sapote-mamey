"""Software-only channel reader admission; no sequence analysis."""
import importlib.util
import os
from pathlib import Path
import pytest
TARGET=Path(__file__).resolve().parents[1]/'mamey/roster_v2.py'
spec=importlib.util.spec_from_file_location('roster_channel_candidate',TARGET)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

@pytest.mark.parametrize('layout',['overlay','top10'])
@pytest.mark.parametrize('entry',['helper','public'])
def test_present_unreadable_channel_refused(tmp_path,monkeypatch,layout,entry):
    directory=tmp_path/('blastp_online' if layout=='overlay' else 'blastp_nr');directory.mkdir()
    path=directory/('SOFTWARE_online_blastp.csv' if layout=='overlay' else 'SOFTWARE_top10.csv')
    path.write_text('channel,gene,bgc_id\nnr,software_gene,SOFTWARE\n')
    before=path.read_bytes();real=Path.open
    def denied(selected,*args,**kwargs):
        if selected==path:raise PermissionError('synthetic denial')
        return real(selected,*args,**kwargs)
    monkeypatch.setattr(Path,'open',denied)
    with pytest.raises(ValueError,match='ROSTER_CHANNEL_READ_ERROR.*nr.*PermissionError'):
        if entry=='helper':mod._read_channel_store(tmp_path,'nr')
        else:mod.build_gene_roster(tmp_path,strain_id='SOFTWARE')
    monkeypatch.undo();assert path.read_bytes()==before

def test_absent_and_header_only_store_remain_empty(tmp_path):
    assert mod._read_channel_store(tmp_path,'nr')=={}
    directory=tmp_path/'blastp_nr';directory.mkdir();(directory/'SOFTWARE_top10.csv').write_text('gene,bgc_id\n')
    assert mod._read_channel_store(tmp_path,'nr')=={}
    assert mod.build_gene_roster(tmp_path,strain_id='SOFTWARE')['strain']=='SOFTWARE'

def test_valid_overlay_precedence_unchanged(tmp_path):
    online=tmp_path/'blastp_online';online.mkdir();(online/'SOFTWARE_online_blastp.csv').write_text('channel,query_bgc,locus_tag,subject_acc\nnr,SOFTWARE,gene1,OVERLAY\n')
    top=tmp_path/'blastp_nr';top.mkdir();(top/'SOFTWARE_top10.csv').write_text('bgc_id,gene,subject_acc\nSOFTWARE,gene1,TOP10\nSOFTWARE,gene2,SECOND\n')
    result=mod._read_channel_store(tmp_path,'nr')
    assert result[('SOFTWARE','gene1')]['subject_acc']=='OVERLAY'
    assert result[('SOFTWARE','gene2')]['subject_acc']=='SECOND'
