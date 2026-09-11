"""Parse shipped R scripts without loading plotting dependencies or rendering PDFs."""
from pathlib import Path
import shutil
import subprocess
import pytest
ROOT = Path(__file__).resolve().parents[1]
R = shutil.which("Rscript")
pytestmark = pytest.mark.skipif(R is None, reason="Rscript required for R syntax validation")
@pytest.mark.parametrize("script", sorted((ROOT / "tools").glob("*.R")), ids=lambda p:p.name)
def test_shipped_r_script_parses(script):
    run = subprocess.run([R, "-e", "parse(commandArgs(TRUE)[1])", str(script)], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr

def test_r_parser_rejects_detached_else(tmp_path):
    source = tmp_path / "bad.R"
    source.write_text("x <- if (TRUE) 1\n  else 2\n")
    run = subprocess.run([R, "-e", "parse(commandArgs(TRUE)[1])", str(source)], capture_output=True, text=True)
    assert run.returncode != 0
    assert "else" in run.stderr
