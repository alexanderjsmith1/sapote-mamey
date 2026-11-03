"""Policy errors are clear at the CLI and preserve the callable contract."""
from pathlib import Path
import os, shutil, subprocess, sys, zipfile
import pytest
ROOT=Path(__file__).resolve().parents[1]

@pytest.mark.parametrize("policy",["duplicate","broken"])
def test_cli_reports_policy_hold_without_traceback(tmp_path,policy):
    tools=tmp_path/"tools";tools.mkdir()
    for name in ("preflight_zip_hygiene.py","zip_hygiene_allowlist.py","_console.py"):
        shutil.copyfile(ROOT/"tools"/name,tools/name)
    path=tools/"zip_hygiene_allowlist.tsv"
    if policy=="duplicate":path.write_text("docs/item.pdf\t1\tfirst\ndocs/item.pdf\t2\tsecond\n")
    else:path.symlink_to(tools/"missing.tsv")
    archive=tmp_path/"fixture.zip"
    with zipfile.ZipFile(archive,"w") as z:z.writestr("docs/item.pdf",b"synthetic")
    env=os.environ.copy();env["PYTHONDONTWRITEBYTECODE"]="1"
    result=subprocess.run([sys.executable,"-B",str(tools/"preflight_zip_hygiene.py"),str(archive)],env=env,capture_output=True,text=True)
    assert result.returncode==2 and "ZIP_HYGIENE_ALLOWLIST_HOLD" in result.stderr
    assert "Traceback" not in result.stderr and result.stdout==""
