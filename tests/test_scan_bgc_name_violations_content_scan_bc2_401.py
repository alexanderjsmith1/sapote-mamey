"""BC2 .401 audit: hooks/scan_bgc_name_violations.py — the offline/census sibling of
hooks/bgc_node_name_guard.sh (the live PostToolUse hook, fixed this same round for the
identical gap). This scanner only ever checked file/directory NAMES for a bare
strain+BGC-number citation with no node token; a genuinely-named file (e.g. "notes.md") whose
own CONTENT bare-cites strain+BGC was invisible to a census run.

Reproduced live against the real pristine script: a real, seeded content-only citation under a
synthetic strain_data root reports 0 violations.

Extended to reuse the bundle's own authoritative gate
(`mamey.bgc_citation_gate.find_nodeless_bgc_citations`, the same logic backing `mamey
verify-citations` and the sibling hook's own fix) for .md/.csv files, adding a new "CONTENT"
violation kind with a 4th `detail` TSV column. DIR/FILE rows and their 3-column meaning are
unchanged.

No prior test existed for this script at all (confirmed) -- first coverage.

Reproduces behavior via subprocess against the real script (no logic reimplementation).
"""
from __future__ import annotations

import csv
import subprocess
import sys
import pathlib

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "hooks" / "scan_bgc_name_violations.py"


def _run(root: pathlib.Path, out: pathlib.Path) -> tuple[str, int]:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root), "--out", str(out)],
        capture_output=True, text=True,
    )
    return proc.stdout, proc.returncode


def _read_tsv(out: pathlib.Path) -> list[dict]:
    with out.open(newline="") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def test_script_present():
    assert SCRIPT.is_file(), "hooks/scan_bgc_name_violations.py not found"


# -- the actual regression this extension closes ------------------------------------------------

def test_content_only_bare_citation_now_caught(tmp_path):
    root = tmp_path / "strain_data"
    strain_dir = root / "AS-001"
    strain_dir.mkdir(parents=True)
    (strain_dir / "notes.md").write_text("AS-001 / BGC016 shows strong T1PKS signal.\n")
    out = tmp_path / "violations.tsv"
    stdout, rc = _run(root, out)
    assert rc == 0
    rows = _read_tsv(out)
    content_rows = [r for r in rows if r["kind"] == "CONTENT"]
    assert len(content_rows) == 1, f"expected one CONTENT violation; got {rows!r}"
    assert content_rows[0]["strain"] == "AS-001"
    assert "notes.md" in content_rows[0]["path"]
    assert "BGC016" in content_rows[0]["detail"]
    assert "VIOLATIONS" in stdout and "1" in stdout


def test_content_scan_only_applies_to_md_and_csv(tmp_path):
    root = tmp_path / "strain_data"
    strain_dir = root / "AS-001"
    strain_dir.mkdir(parents=True)
    (strain_dir / "notes.txt").write_text("AS-001 / BGC016 shows strong T1PKS signal.\n")
    out = tmp_path / "violations.tsv"
    _run(root, out)
    rows = _read_tsv(out)
    assert rows == [], f"a non-md/csv file must not trigger the content scan; got {rows!r}"


# -- no regression on the original name-only checks ----------------------------------------------

def test_bare_bgc_directory_name_still_caught(tmp_path):
    root = tmp_path / "strain_data"
    strain_dir = root / "AS-001"
    (strain_dir / "BGC011_folder").mkdir(parents=True)
    out = tmp_path / "violations.tsv"
    _run(root, out)
    rows = _read_tsv(out)
    assert any(r["kind"] == "DIR" and "BGC011_folder" in r["path"] for r in rows)


def test_bare_bgc_filename_still_caught(tmp_path):
    root = tmp_path / "strain_data"
    strain_dir = root / "AS-001"
    strain_dir.mkdir(parents=True)
    (strain_dir / "BGC022_summary.txt").write_text("clean prose\n")
    out = tmp_path / "violations.tsv"
    _run(root, out)
    rows = _read_tsv(out)
    assert any(r["kind"] == "FILE" and "BGC022_summary.txt" in r["path"] for r in rows)


def test_dir_and_file_rows_have_empty_detail_column(tmp_path):
    """The 4th `detail` column is additive -- DIR/FILE rows (unchanged meaning) leave it empty."""
    root = tmp_path / "strain_data"
    strain_dir = root / "AS-001"
    strain_dir.mkdir(parents=True)
    (strain_dir / "BGC022_summary.txt").write_text("clean prose\n")
    out = tmp_path / "violations.tsv"
    _run(root, out)
    rows = _read_tsv(out)
    file_rows = [r for r in rows if r["kind"] == "FILE"]
    assert file_rows and file_rows[0]["detail"] == ""


# -- content-scan negative controls ---------------------------------------------------------------

def test_content_with_proper_node_token_passes(tmp_path):
    root = tmp_path / "strain_data"
    strain_dir = root / "AS-001"
    strain_dir.mkdir(parents=True)
    (strain_dir / "clean.md").write_text(
        "AS-001 / NODE_162_length_5000_cov_12 / region001 / BGC016 is strong.\n"
    )
    out = tmp_path / "violations.tsv"
    _run(root, out)
    rows = _read_tsv(out)
    assert rows == [], f"expected a properly node-cited body to pass clean; got {rows!r}"


def test_count_phrase_does_not_false_positive(tmp_path):
    root = tmp_path / "strain_data"
    strain_dir = root / "AS-001"
    strain_dir.mkdir(parents=True)
    (strain_dir / "summary.md").write_text("AS-001 has 37 BGCs total across the assembly.\n")
    out = tmp_path / "violations.tsv"
    _run(root, out)
    rows = _read_tsv(out)
    assert rows == [], f"a count phrase must not false-positive; got {rows!r}"


def test_missing_root_reports_error_not_crash(tmp_path):
    missing = tmp_path / "does_not_exist"
    out = tmp_path / "violations.tsv"
    stdout, rc = _run(missing, out)
    assert rc == 2
