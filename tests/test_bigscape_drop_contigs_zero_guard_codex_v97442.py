"""Generic decontamination drop-list validation controls."""
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile

PREP = Path(__file__).resolve().parents[1] / "tools" / "bigscape_prep.py"


def _run(tmp_path, removed_text, *extra):
    official = tmp_path / "official"
    official.mkdir()
    (official / "exclusions.json").write_text(json.dumps({"hard_excluded": []}))
    zips = tmp_path / "zips"
    zips.mkdir()
    with zipfile.ZipFile(zips / "QUERY.zip", "w") as z:
        z.writestr("QUERY.json", '{"strictness":"loose"}')
        z.writestr("NODE_1_length_100_cov_1.region001.gbk",
                   "LOCUS x\n     CDS             1..30\n//\n")
    removed = tmp_path / "removed.tsv"
    removed.write_text(removed_text)
    env = dict(os.environ, MAMEY_OFFICIAL_DATA=str(official), MAMEY_DATA_ROOT=str(tmp_path))
    cmd = [sys.executable, str(PREP), "--inputs", str(zips), "--out", str(tmp_path / "out"),
           "--strictness", "loose", "--drop-contigs", f"QUERY={removed}", *extra]
    return subprocess.run(cmd, env=env, text=True, capture_output=True)


def test_unmatched_list_refused(tmp_path):
    result = _run(tmp_path, "NODE_9_length_100_cov_1\tremoved\n")
    assert result.returncode == 2
    assert "ZERO_DROP_REFUSED" in result.stderr


def test_reviewed_zero_can_proceed(tmp_path):
    result = _run(tmp_path, "NODE_9_length_100_cov_1\tremoved\n", "--allow-zero-drop", "QUERY")
    assert result.returncode == 0, result.stderr
    assert "dropped 0 region(s)" in result.stderr


def test_empty_list_refused(tmp_path):
    result = _run(tmp_path, "# no contigs\n")
    assert result.returncode == 2
    assert "has no contig IDs" in result.stderr


def test_duplicate_strain_lists_refused(tmp_path):
    result = _run(tmp_path, "NODE_1_length_100_cov_1\n",
                  "--drop-contigs", str(tmp_path / "removed.tsv").join(["QUERY=", ""]))
    assert result.returncode == 2
    assert "duplicate --drop-contigs strain" in result.stderr
