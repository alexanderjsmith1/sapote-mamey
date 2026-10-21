"""R figure packages come in groups: core is required, the others add one figure family each (.456)."""
import importlib.util
import re
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "bundle_support" / "install_r_figure_packages.R"
spec = importlib.util.spec_from_file_location("optional_r_456", ROOT / "mamey" / "optional_r.py")
optional_r = importlib.util.module_from_spec(spec); spec.loader.exec_module(optional_r)
spec = importlib.util.spec_from_file_location("ci_installs_r_452", ROOT / "tests" / "test_452_ci_installs_r.py")
ci_452 = importlib.util.module_from_spec(spec); spec.loader.exec_module(ci_452)


def _installer_groups():
    s = INSTALLER.read_text(encoding="utf-8")
    body = re.search(r"^groups <- list\((.*?)\)\)\s*$", s, re.M | re.S).group(1) + ")"
    return {name: tuple(re.findall(r'"([^"]+)"', pkgs)) for name, pkgs in re.findall(r"(\w+)\s*=\s*c\(([^)]*)\)", body)}


def test_installer_groups_match_the_python_list():
    assert _installer_groups() == optional_r.R_FIGURE_GROUPS
    assert set(optional_r.R_GROUP_ADDS) == set(optional_r.R_FIGURE_GROUPS)


def test_every_installed_package_is_in_exactly_one_group():
    grouped = [p for pkgs in optional_r.R_FIGURE_GROUPS.values() for p in pkgs]
    assert len(grouped) == len(set(grouped))
    assert set(grouped) == ci_452._installer_packages()


def test_every_package_a_shipped_r_script_loads_is_in_a_group():
    grouped = {p for pkgs in optional_r.R_FIGURE_GROUPS.values() for p in pkgs}
    assert not sorted(ci_452._shipped_r_packages() - grouped)


def _fake_rscript(tmp_path, missing=()):
    names = sorted({p for pkgs in optional_r.R_FIGURE_GROUPS.values() for p in pkgs})
    lines = "".join(f'echo "SAPOTE_R {p} {"FALSE" if p in missing else "TRUE"}"\n' for p in names)
    script = tmp_path / "Rscript"
    script.write_text("#!/bin/sh\n" + lines)
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return str(script)


def test_doctor_reports_each_group_ready(tmp_path):
    report = optional_r.r_group_report(_fake_rscript(tmp_path))
    assert len(report) == len(optional_r.R_FIGURE_GROUPS) and all(ok for ok, _ in report)


def test_doctor_names_the_missing_packages_and_the_fix(tmp_path):
    report = dict((line.split()[1], (ok, line)) for ok, line in optional_r.r_group_report(_fake_rscript(tmp_path, {"ggtree", "treeio"})))
    ok, line = report["trees"]
    assert not ok and "ggtree, treeio" in line and "tree figures unavailable" in line and "--require trees" in line
    assert report["core"][0] and report["bioassay"][0]


def test_missing_core_fix_has_no_require_flag(tmp_path):
    line = dict((l.split()[1], l) for _, l in optional_r.r_group_report(_fake_rscript(tmp_path, {"ggplot2"})))["core"]
    assert "ggplot2" in line and line.endswith("install_r_figure_packages.R")


def test_no_rscript_is_one_clear_line():
    report = optional_r.r_group_report("/nonexistent/Rscript")
    assert len(report) == 1 and not report[0][0]


def test_ci_requires_every_group():
    wf = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "Rscript bundle_support/install_r_figure_packages.R --require all" in wf


def test_prerequisites_name_every_group_and_package():
    section = (ROOT / "docs" / "PREREQUISITES.md").read_text(encoding="utf-8").split("## R figure stack", 1)[1].split("\n## ", 1)[0]
    for group, pkgs in optional_r.R_FIGURE_GROUPS.items():
        row = next(l for l in section.splitlines() if l.startswith(f"| `{group}` |"))
        assert all(f"`{p}`" in row for p in pkgs), group
