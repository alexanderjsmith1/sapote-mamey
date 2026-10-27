from pathlib import Path
import subprocess,sys
import pytest
SCRIPT=Path(__file__).resolve().parents[1]/'mamey/data/literature/_corpus/curate_kb.py'

@pytest.mark.parametrize('only',['UnknownTarget','Nocardia,UnknownTarget','nocardia'])
def test_unknown_only_refuses_before_any_output(tmp_path,only):
    corpus=tmp_path/'empty.jsonl';corpus.write_text('');output=tmp_path/'literature'
    result=subprocess.run([sys.executable,str(SCRIPT),str(corpus),str(output),'--only',only],capture_output=True,text=True)
    assert result.returncode==2
    assert 'unknown --only target' in result.stderr
    assert ('UnknownTarget' if 'UnknownTarget' in only else 'nocardia') in result.stderr
    assert not output.exists()

def test_known_selector_keeps_existing_output_contract(tmp_path):
    corpus=tmp_path/'empty.jsonl';corpus.write_text('');output=tmp_path/'literature'
    result=subprocess.run([sys.executable,str(SCRIPT),str(corpus),str(output),'--only','Nocardia'],capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert (output/'Nocardia.md').is_file()
    assert not (output/'Streptomyces.md').exists()
