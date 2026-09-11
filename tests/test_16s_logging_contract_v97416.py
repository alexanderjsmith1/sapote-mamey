"""CLI status uses diagnostic logging; completion semantics remain separate."""
from pathlib import Path
import subprocess
import sys


def test_helper_selfcheck_uses_stderr_logging():
    tool=Path(__file__).resolve().parents[1]/'tools/_phylo16s.py'
    result=subprocess.run([sys.executable,str(tool),'--test'],capture_output=True,text=True,timeout=30)
    assert result.returncode==0
    assert not result.stdout
    assert 'PASS _phylo16s selftest' in result.stderr
