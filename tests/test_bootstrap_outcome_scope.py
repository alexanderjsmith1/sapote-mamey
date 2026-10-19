from pathlib import Path
import os,subprocess,sys
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize("mode",["all","core_only","core_failed","smoke_failed","pytest_failed"])
def test_install_scope_and_next_step_are_truthful(tmp_path,mode):
    shim=tmp_path/"fake python"
    shim.write_text("#!"+sys.executable+"\nimport os,sys\na=sys.argv[1:];m=os.environ['INSTALL_TEST_MODE']\nif a==['--version']:print('Python 3.13.13')\nif '.[all]' in a and m in ['core_only','core_failed']:sys.exit(1)\nif a[-2:]==['-e','.'] and m=='core_failed':sys.exit(1)\nif a[-1:]==['pytest'] and m=='pytest_failed':sys.exit(1)\nif a[:2]==['-m','pytest'] and m=='smoke_failed':sys.exit(1)\n")
    shim.chmod(0o755)
    r=subprocess.run(["bash",str(ROOT/'bootstrap.sh')],env=dict(os.environ,PYTHON=str(shim),INSTALL_TEST_MODE=mode),capture_output=True,text=True,timeout=15)
    text=r.stdout+r.stderr
    if mode=='all':assert r.returncode==0 and 'bootstrap done: ALL_EXTRAS' in text
    elif mode=='core_only':assert r.returncode==0 and 'bootstrap done: CORE_ONLY' in text and 'Next:' in text
    elif mode=='core_failed':assert r.returncode!=0 and 'bootstrap HOLD: core installation failed' in text and 'Next:' in text and 'bootstrap done' not in text
    elif mode=='pytest_failed':assert r.returncode!=0 and 'bootstrap HOLD: test dependency installation failed' in text and 'Next:' in text and 'bootstrap done' not in text
    else:assert r.returncode!=0 and 'smoke test FAILED' in text and 'bootstrap done' not in text
