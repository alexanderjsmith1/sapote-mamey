"""Fail closed when an existing source directory cannot be traversed."""
from pathlib import Path
import json,os,subprocess,sys
import pytest
GATE=Path(__file__).resolve().parents[1]/"tools/check_regex_interpolation.py"
def run(root):
    return subprocess.run([sys.executable,"-B",str(GATE),"--root",str(root),"--json"],capture_output=True,text=True)
def test_unreadable_directory_refuses_even_with_other_clean_files(tmp_path):
    (tmp_path/"clean.py").write_text("VALUE=1\n")
    hidden=tmp_path/"hidden";hidden.mkdir();(hidden/"bad.py").write_text('import re\nCHOICES="cat|dog"\nPAT=re.compile(rf"^{CHOICES}$")\n')
    assert run(tmp_path).returncode==1
    hidden.chmod(0)
    try:
        try:
            list(os.scandir(hidden))
        except PermissionError:
            pass
        else:
            pytest.skip("effective credentials can still read chmod-000 directory")
        result=run(tmp_path)
        assert result.returncode==2 and result.stdout=="" and "could not be scanned" in result.stderr
    finally:
        hidden.chmod(0o700)
def test_skipped_unreadable_directory_is_not_scanned(tmp_path):
    (tmp_path/"clean.py").write_text("VALUE=1\n")
    hidden=tmp_path/"_vendor";hidden.mkdir();(hidden/"bad.py").write_text('import re\nCHOICES="cat|dog"\nPAT=re.compile(rf"^{CHOICES}$")\n');hidden.chmod(0)
    try:
        result=run(tmp_path);assert result.returncode==0
        assert json.loads(result.stdout)["files_scanned"]==1
    finally:
        hidden.chmod(0o700)
def test_direct_file_root_still_reports_findings(tmp_path):
    p=tmp_path/"bad.py";p.write_text('import re\nCHOICES="cat|dog"\nPAT=re.compile(rf"^{CHOICES}$")\n');result=run(p)
    assert result.returncode==1 and len(json.loads(result.stdout)["new"])==1
