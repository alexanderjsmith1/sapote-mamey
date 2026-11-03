"""DREL-034: every requested bigscape_prep input is accounted for; unreadable ones fail the run."""
import json
import os
import pathlib
import subprocess
import sys
import zipfile

BUNDLE = pathlib.Path(__file__).resolve().parents[1]
PREP = BUNDLE / "tools" / "bigscape_prep.py"


def _zip(path, strictness="loose"):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(f"{path.stem}.json", json.dumps({"strictness": strictness}))
        z.writestr("NODE_1.region001.gbk", "LOCUS test\n     CDS             1..30\n//\n")
    return path


def _run(tmp_path, *inputs):
    official = tmp_path / "OFFICIAL_DATA"
    official.mkdir(exist_ok=True)
    (official / "exclusions.json").write_text(json.dumps({"hard_excluded": []}))
    out = tmp_path / "out"
    env = dict(os.environ, MAMEY_OFFICIAL_DATA=str(official), MAMEY_DATA_ROOT=str(tmp_path))
    cmd = [sys.executable, str(PREP), "--inputs", *map(str, inputs), "--out", str(out), "--strictness", "loose"]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    rows = (out / "STRICTNESS_MANIFEST.tsv").read_text().splitlines()[1:] if (out / "STRICTNESS_MANIFEST.tsv").exists() else []
    return r, rows


def test_good_input_alone_still_passes(tmp_path):
    r, rows = _run(tmp_path, _zip(tmp_path / "SYN-1.zip"))
    assert r.returncode == 0, r.stderr
    assert any("\tSTAGED\t" in row for row in rows)


def test_missing_directory_is_an_error_not_a_silent_drop(tmp_path):
    r, rows = _run(tmp_path, _zip(tmp_path / "SYN-1.zip"), tmp_path / "missing_dir")
    assert r.returncode == 2
    assert any("ERROR:MISSING_INPUT" in row and "missing_dir" in row for row in rows)


def test_missing_zip_is_an_error_not_undetectable(tmp_path):
    r, rows = _run(tmp_path, _zip(tmp_path / "SYN-1.zip"), tmp_path / "SYN-2.zip")
    assert r.returncode == 2
    assert any("ERROR:MISSING_INPUT" in row for row in rows)
    assert not any("SKIP_UNDETECTABLE" in row for row in rows)


def test_corrupt_zip_is_an_error(tmp_path):
    bad = tmp_path / "SYN-2.zip"
    bad.write_bytes(b"not a zip")
    r, rows = _run(tmp_path, _zip(tmp_path / "SYN-1.zip"), bad)
    assert r.returncode == 2
    assert any("ERROR:UNREADABLE_ZIP" in row for row in rows)


def test_unsupported_file_is_recorded_not_dropped(tmp_path):
    other = tmp_path / "SYN-3.gbk"
    other.write_text("LOCUS x\n//\n")
    r, rows = _run(tmp_path, _zip(tmp_path / "SYN-1.zip"), other)
    assert r.returncode == 0, r.stderr
    assert any("SKIP_UNSUPPORTED_INPUT" in row for row in rows)
