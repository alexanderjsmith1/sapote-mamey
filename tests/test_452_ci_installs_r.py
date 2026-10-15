"""CI installs R and the figure packages before the test suite, and the installer lists every package the shipped R
scripts load (.452; Linux test of the .451 candidate and its review: 32 R tests could not run on CI)."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_R = {"base", "stats", "utils", "grDevices", "graphics", "grid", "methods", "tools", "parallel", "compiler",
          "splines", "BiocManager"}


def _installer_packages():
    s = (ROOT / "bundle_support" / "install_r_figure_packages.R").read_text(encoding="utf-8")
    cran = re.search(r'^cran <- c\(([^)]*)\)', s, re.M).group(1)
    bioc = re.search(r'^bioc <- c\(([^)]*)\)', s, re.M).group(1)
    return set(re.findall(r'"([^"]+)"', cran + bioc))


def _shipped_r_packages():
    pkgs = set()
    for p in ROOT.rglob("*.R"):
        if "tests" in p.relative_to(ROOT).parts:
            continue
        s = p.read_text(encoding="utf-8", errors="replace")
        # quoted names in library/require/requireNamespace; unquoted only as library(x)/require(x) (a variable such as
        # requireNamespace(p, ...) is not a package); pkg:: not preceded by "/" or "." (XPath axes, "file.py::test")
        pkgs |= set(re.findall(r'\b(?:library|require|requireNamespace)\(\s*["\']([A-Za-z][A-Za-z0-9.]*)["\']', s))
        pkgs |= set(re.findall(r'\b(?:library|require)\(\s*([A-Za-z][A-Za-z0-9.]*)\s*\)', s))
        code = re.sub(r'"[^"\n]*"|\'[^\'\n]*\'', '""', s)          # string contents (e.g. XPath "ancestor::g") are not code
        pkgs |= set(re.findall(r'(?<![\w/.])([A-Za-z][A-Za-z0-9.]*)::(?!:)', code))
    return pkgs - BASE_R


def test_installer_covers_every_package_the_shipped_r_scripts_load():
    missing = sorted(_shipped_r_packages() - _installer_packages())
    assert not missing, f"add to bundle_support/install_r_figure_packages.R: {missing}"


def test_ci_installs_r_and_packages_before_the_suite():
    wf = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    test_job = wf.split("\n  gates:")[0]
    i_setup, i_inst, i_suite = (test_job.find("r-lib/actions/setup-r@"),
                                test_job.find("Rscript bundle_support/install_r_figure_packages.R"),
                                test_job.find("run: pytest -q"))
    assert -1 not in (i_setup, i_inst, i_suite) and i_setup < i_inst < i_suite
