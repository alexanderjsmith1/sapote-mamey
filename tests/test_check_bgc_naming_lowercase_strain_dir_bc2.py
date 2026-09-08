"""BC2-CASE-01 (v9.7.395): tools/check_bgc_naming.py scan() must not go blind on a lowercase (or
mixed-case) AS-strain directory.

scan()'s strain-detection line used a bare `re.search(r"AS-\\d+", dirpath)` with no
re.IGNORECASE, while BASENAME_STRAIN_RE (used two lines above, for the actual per-basename
governance check inside _basename_violates()) and crosswalk()'s own strain lookup are both
case-insensitive — crosswalk() additionally normalizes with .upper(). A strain directory named
"as-40" (lowercase) failed the bare regex, so `strain` came back None and the entire subtree hit
`continue` — every file under it, including a real bare-"BGCnn" governance violation, went
completely unscanned. scan() reported "0 violation(s) ... exit code 0" (a clean CI pass) for a
tree that actually contained a violation this tool exists to catch.

Reproduced live against the unpatched tools/check_bgc_naming.py before this fix.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path


def _module():
    path = Path(__file__).parents[1] / "tools" / "check_bgc_naming.py"
    spec = importlib.util.spec_from_file_location("check_bgc_naming", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def _make_violation_tree(root: Path, strain_dirname: str) -> None:
    bgc_dir = root / strain_dirname / "NODE_13_length_178295_cov_71.region001"
    bgc_dir.mkdir(parents=True)
    # A bare "BGC016" token with no strain/node/region in its OWN basename — a real governance
    # violation per check_bgc_naming.py's own module docstring.
    (bgc_dir / "BGC016_summary.md").write_text("placeholder\n")


def test_lowercase_strain_dir_violation_is_caught(tmp_path):
    _make_violation_tree(tmp_path, "as-40")
    mod = _module()
    exit_code = mod.scan(str(tmp_path), None, None)
    assert exit_code == 1, (
        "a bare-BGCnn violation under a lowercase 'as-40' strain directory must be caught "
        "(scan() must not report a clean CI pass for an unscanned subtree)"
    )


def test_uppercase_strain_dir_violation_still_caught(tmp_path):
    # Regression guard: the existing uppercase-strain path must keep working.
    _make_violation_tree(tmp_path, "AS-41")
    mod = _module()
    exit_code = mod.scan(str(tmp_path), None, None)
    assert exit_code == 1


def test_mixed_case_strains_both_counted_and_grouped_uppercase(tmp_path, capsys):
    _make_violation_tree(tmp_path, "as-40")
    _make_violation_tree(tmp_path, "AS-41")
    mod = _module()
    exit_code = mod.scan(str(tmp_path), None, None)
    out = capsys.readouterr().out
    assert exit_code == 1
    assert "2 violation(s)" in out
    assert "across 2 strain(s)" in out
    # normalized to uppercase for consistent grouping/filtering, matching crosswalk()'s convention
    assert "AS-40" in out
    assert "AS-41" in out


def test_cli_end_to_end_lowercase_strain_dir(tmp_path):
    # End-to-end via the actual CLI entry point, matching how validate/CI invoke this tool.
    _make_violation_tree(tmp_path, "as-40")
    script = Path(__file__).parents[1] / "tools" / "check_bgc_naming.py"
    result = subprocess.run(
        [sys.executable, str(script), "scan", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert result.returncode == 1, (
        f"CLI must exit non-zero on a real violation under a lowercase strain dir; "
        f"stdout={result.stdout!r}"
    )
    assert "0 violation(s)" not in result.stdout
