import re, shutil, subprocess
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
THEME = ROOT / "tools" / "bioassay_paper_theme.R"


def _sp_md(text, tmp_path):
    src = THEME.read_text()
    line = next(l for l in src.splitlines() if l.startswith("sp_md <- function"))
    script = tmp_path / "sp_md.R"
    script.write_text(line + '\ncat(sp_md(%s))\n' % ('"' + text + '"'))   # a file, not -e: -e mangles backslashes
    return subprocess.run(["Rscript", str(script)], capture_output=True, text=True, check=True).stdout


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
def test_species_names_get_italics(tmp_path):
    assert _sp_md("Best inhibition of P. larvae (either strain), crude extract", tmp_path) == "Best inhibition of <i>P. larvae</i> (either strain), crude extract"
    assert _sp_md("Candida sp.", tmp_path) == "<i>Candida</i> sp."
    assert _sp_md("C. albicans and C. auris", tmp_path) == "<i>C. albicans</i> and <i>C. auris</i>"


@pytest.mark.skipif(shutil.which("Rscript") is None, reason="Rscript not installed")
def test_non_species_text_is_unchanged(tmp_path):
    assert _sp_md("Isolates tested, crude extracts", tmp_path) == "Isolates tested, crude extracts"
    assert _sp_md("MRSA (15 isolates)", tmp_path) == "MRSA (15 isolates)"


def test_strip_and_axis_titles_are_markdown_elements():
    src = THEME.read_text()
    assert "strip.text=element_markdown" in src and "axis.title=element_markdown" in src
