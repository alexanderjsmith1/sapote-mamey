"""The reference-panel ledger has no workspace-specific default and fails on no rows.

It used to default to /mnt/user-data/uploads and /mnt/user-data/outputs, and printed
"no rows produced" and exited 0 when nothing was extracted. A caller could not tell an
empty run from a good one.
"""
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
TOOL = HERE / "tools" / "reference_panel_ledger.py"
FIX = HERE / "tests" / "fixtures" / "domain_level_minimal_antismash.zip"


def run(*args):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)], cwd=HERE, capture_output=True, text=True)


def test_source_and_help_name_no_workspace_path():
    assert "/mnt/user-data" not in TOOL.read_text()
    assert "/mnt/user-data" not in run("--help").stdout


def test_both_paths_are_required(tmp_path):
    for args in ([], [tmp_path]):
        r = run(*args)
        assert r.returncode == 2, (args, r.returncode)
        assert "required" in r.stderr
    assert not list(tmp_path.iterdir())


def test_missing_source_directory_is_a_usage_error(tmp_path):
    r = run(tmp_path / "absent", tmp_path / "out.csv")
    assert r.returncode == 2 and "not a directory" in r.stderr
    assert not (tmp_path / "out.csv").exists()


def test_no_zips_exits_nonzero_and_writes_nothing(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "notes.txt").write_text("not a zip")
    out = tmp_path / "out.csv"
    r = run(src, out)
    assert r.returncode == 1
    assert "NO_ROWS" in r.stderr
    assert not out.exists()


def test_unreadable_zip_yielding_no_rows_exits_nonzero(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "broken.zip").write_bytes(b"not a zip archive")
    out = tmp_path / "out.csv"
    r = run(src, out)
    assert r.returncode == 1 and "NO_ROWS" in r.stderr
    assert not out.exists()


def test_good_input_still_exits_zero_and_writes_rows(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    shutil.copy(FIX, src / "SYN-970.zip")
    out = tmp_path / "out.csv"
    r = run(src, out)
    assert r.returncode == 0, r.stderr
    assert out.read_text().count("\n") >= 2
