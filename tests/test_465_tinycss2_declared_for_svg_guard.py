"""465 06: the SVG CSS guard's parser is declared where CI and users install it.

tools/prepare_pdf_resources.py imports tinycss2 to check CSS url() and @import in SVG figures,
and refuses the SVG when it is missing. The guard tests need it. The 9.7.464 CI installed
.[figures,bio,documents,test], which did not bring tinycss2, so 23 guard tests failed there.
"""
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _extra(name):
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    reqs = data["project"]["optional-dependencies"][name]
    return {re.split(r"[<>=!~\[; ]", r, maxsplit=1)[0].lower() for r in reqs}


def test_preparer_still_imports_tinycss2():
    assert "import tinycss2" in (ROOT / "tools/prepare_pdf_resources.py").read_text(encoding="utf-8")


def test_tinycss2_in_test_extra():
    assert "tinycss2" in _extra("test")


def test_tinycss2_in_render_and_all():
    assert "tinycss2" in _extra("render")
    assert "tinycss2" in _extra("all")


def test_ci_installs_the_test_extra():
    ci = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    lines = [l for l in ci.splitlines() if "pip install -e" in l and "[" in l]
    assert lines and all("test" in l for l in lines), lines
