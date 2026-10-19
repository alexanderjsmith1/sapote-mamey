"""CI installs the system libraries the R figure packages compile against on Linux.

The v9.7.451 CI run failed at the R install step: `fs` needs libuv and `gdtools` needs cairo, so
`yulab.utils`, `ggfun`, `ggplotify`, `aplot` and `ggtree` could not build and the suite never ran.
"""
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
CI = ROOT / ".github" / "workflows" / "ci.yml"


def _apt_packages():
    text = CI.read_text(encoding="utf-8")
    m = re.search(r"apt-get install -y((?:[^\n]*\\\n)*[^\n]*)", text)
    assert m, "ci.yml has no apt-get install step"
    body = re.sub(r"#[^\n]*", "", m.group(1)).replace("\\\n", " ")
    return set(body.split())


def test_ci_installs_libuv_and_cairo_for_the_r_figure_packages():
    pkgs = _apt_packages()
    assert "libuv1-dev" in pkgs, "fs (needed by yulab.utils, ggfun, aplot) cannot build without libuv"
    assert "libcairo2-dev" in pkgs, "gdtools (needed by ggtree) cannot build without cairo"


def test_ci_keeps_the_earlier_r_system_libraries():
    pkgs = _apt_packages()
    for p in ("libcurl4-openssl-dev", "libxml2-dev", "libfontconfig1-dev", "libfreetype-dev",
              "libharfbuzz-dev", "libfribidi-dev", "libpng-dev", "libjpeg-dev", "libtiff5-dev"):
        assert p in pkgs, p
