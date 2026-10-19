"""Reuse requires exact admitted bytes; CLI failure consolidation preserves observable outcomes."""
from pathlib import Path
import hashlib,os,importlib.util
import pytest
SOURCE=Path(os.environ.get('LANE06_PACKET_QC',Path(__file__).resolve().parents[1]/'tools/figure_render_qc.py'))
spec=importlib.util.spec_from_file_location('snapshot_reuse_qc',SOURCE);qc=importlib.util.module_from_spec(spec);spec.loader.exec_module(qc)

def fixture(tmp_path,form):
    raw=b'self-authored admitted image format fixture';image=tmp_path/'image.png';image.write_bytes(raw);digest=hashlib.sha256(raw).hexdigest();cache=tmp_path/'cache';cache.mkdir();directory=cache/'admitted_pngs';directory.mkdir();snapshot=directory/(digest+'.png');foreign=tmp_path/'foreign.txt';foreign.write_text('Foreign evidence.\n')
    if form=='same':snapshot.write_bytes(raw)
    elif form=='different':snapshot.write_bytes(b'X'*len(raw))
    elif form=='symlink':snapshot.symlink_to(foreign)
    elif form=='dangling':snapshot.symlink_to(tmp_path/'absent')
    ocr=qc.Ocr.__new__(qc.Ocr);ocr.bin=tmp_path/'fake_ocr';ocr.cache_file=cache/'ocr.tsv';ocr.cache={};ocr.reason=''
    return image,raw,digest,snapshot,foreign,ocr

@pytest.mark.parametrize('form',['new','same'])
def test_new_and_exact_existing_snapshots_bind_actual_OCR_input(tmp_path,monkeypatch,form):
    image,raw,digest,snapshot,foreign,ocr=fixture(tmp_path,form);calls=[]
    def run(command,**kwargs):
        assert Path(command[1])==snapshot and snapshot.read_bytes()==raw;calls.append(command)
        return qc.subprocess.CompletedProcess(command,0,str(snapshot)+'\tAdmitted text\n','')
    monkeypatch.setattr(qc.subprocess,'run',run)
    assert ocr.read({image:digest},admitted_bytes={image:raw})[image]==['Admitted text']
    assert len(calls)==1 and snapshot.read_bytes()==raw and foreign.read_text()=='Foreign evidence.\n'

@pytest.mark.parametrize('form',['different','symlink','dangling'])
def test_conflicting_existing_snapshot_refuses_without_overwrite_or_OCR(tmp_path,monkeypatch,form):
    image,raw,digest,snapshot,foreign,ocr=fixture(tmp_path,form);before=bytes(snapshot.read_bytes()) if form=='different' else os.readlink(snapshot)
    monkeypatch.setattr(qc.subprocess,'run',lambda *a,**kw:pytest.fail('Unadmitted snapshot reached OCR'))
    with pytest.raises(qc.RenderPacketAdmissionRefusal,match='snapshot refused'):
        ocr.read({image:digest},admitted_bytes={image:raw})
    assert (snapshot.read_bytes() if form=='different' else os.readlink(snapshot))==before
    assert foreign.read_text()=='Foreign evidence.\n' and not ocr.cache_file.exists()

@pytest.mark.parametrize('case,code,message',[('missing',1,'not found: '),('empty',1,'no figures found (PNG files that are not *_plot_only.png)'),('admission',2,'Synthetic exact refusal')])
def test_cli_failure_stdout_stderr_exit_and_report_timing(tmp_path,monkeypatch,capsys,case,code,message):
    source=tmp_path/'source'
    if case!='missing':source.mkdir()
    if case=='admission':
        def refused(*a,**kw):raise qc.RenderPacketAdmissionRefusal(message)
        monkeypatch.setattr(qc,'run',refused)
    monkeypatch.setattr(qc,'write_reports',lambda *a,**kw:pytest.fail('Report writer reached after terminal failure'))
    assert qc.main([str(source),'--out',str(tmp_path/'qa'),'--ocr','off'])==code
    actual=capsys.readouterr();assert actual.out==''
    assert actual.err==(message+str(source)+'\n' if case=='missing' else message+'\n')
    assert not (tmp_path/'qa/RENDER_QC.md').exists() and not (tmp_path/'qa/RENDER_QC.tsv').exists()
