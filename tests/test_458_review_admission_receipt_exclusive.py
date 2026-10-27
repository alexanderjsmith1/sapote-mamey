from pathlib import Path
import importlib.util
import os
ROOT=Path(os.environ.get('ADMISSION_REVIEW_BASE',Path(__file__).resolve().parents[1]))
spec=importlib.util.spec_from_file_location('admission_publication_fixture',ROOT/'tests/test_458_phylo_admission_cli_refusal_and_receipt.py')
fx=importlib.util.module_from_spec(spec);spec.loader.exec_module(fx)

def test_receipt_created_after_precheck_is_preserved(tmp_path,monkeypatch,capsys):
    roster,fasta=fx._inputs(tmp_path,'A'*1400)
    out=tmp_path/'receipt.json';original=Path.exists;seen=[]
    def exists(path):
        if path==out and not seen:
            seen.append(True);out.write_text('earlier racing evidence');return False
        return original(path)
    monkeypatch.setattr(Path,'exists',exists)
    assert fx.adm.main(['--roster',str(roster),'--fasta',str(fasta),'--json',str(out)])==2
    assert out.read_text()=='earlier racing evidence'
    capture=capsys.readouterr();assert 'already exists' in capture.err and 'ADMISSION_PASS' not in capture.out

def test_dangling_receipt_symlink_is_refused(tmp_path,capsys):
    roster,fasta=fx._inputs(tmp_path,'A'*1400)
    out=tmp_path/'receipt.json';target=tmp_path/'uncreated-target.json';out.symlink_to(target)
    assert fx.adm.main(['--roster',str(roster),'--fasta',str(fasta),'--json',str(out)])==2
    assert out.is_symlink() and not target.exists()
    capture=capsys.readouterr();assert 'already exists' in capture.err and 'ADMISSION_PASS' not in capture.out
