"""DREL-049: conflicting strictness declarations inside one input refuse it, whatever their sizes."""
import json
import os
import pathlib
import subprocess
import sys
import zipfile

BUNDLE = pathlib.Path(__file__).resolve().parents[1]
PREP = BUNDLE / "tools" / "bigscape_prep.py"
GBK = "LOCUS test\n     CDS             1..30\n//\n"


def _zip(path, declarations):
    with zipfile.ZipFile(path, "w") as z:
        for i, (flavor, padding) in enumerate(declarations):
            z.writestr(f"run{i}.json", json.dumps({"strictness": flavor, "pad": "x" * padding}))
        z.writestr("NODE_1.region001.gbk", GBK)
    return path


def _run(tmp_path, zpath, *extra):
    official = tmp_path / "OFFICIAL_DATA"
    official.mkdir(exist_ok=True)
    (official / "exclusions.json").write_text(json.dumps({"hard_excluded": []}))
    out = tmp_path / "out"
    env = dict(os.environ, MAMEY_OFFICIAL_DATA=str(official), MAMEY_DATA_ROOT=str(tmp_path))
    cmd = [sys.executable, str(PREP), "--inputs", str(zpath), "--out", str(out), "--strictness", "loose", *extra]
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    return r, out


def test_larger_loose_member_does_not_win(tmp_path):
    r, out = _run(tmp_path, _zip(tmp_path / "SYN-1.zip", [("loose", 5000), ("strict", 10)]))
    assert r.returncode == 2
    assert not list(out.glob("*.gbk"))
    assert "ERROR:CONFLICTING_STRICTNESS" in (out / "STRICTNESS_MANIFEST.tsv").read_text()


def test_larger_strict_member_does_not_win_either(tmp_path):
    r, out = _run(tmp_path, _zip(tmp_path / "SYN-1.zip", [("strict", 5000), ("loose", 10)]))
    assert r.returncode == 2
    assert "ERROR:CONFLICTING_STRICTNESS" in (out / "STRICTNESS_MANIFEST.tsv").read_text()


def test_assume_strictness_does_not_override_a_conflict(tmp_path):
    r, out = _run(tmp_path, _zip(tmp_path / "SYN-1.zip", [("loose", 10), ("strict", 10)]),
                  "--assume-strictness", "loose")
    assert r.returncode == 2


def test_agreeing_declarations_still_stage(tmp_path):
    r, out = _run(tmp_path, _zip(tmp_path / "SYN-1.zip", [("loose", 5000), ("loose", 10)]))
    assert r.returncode == 0, r.stderr
    assert len(list(out.glob("*.gbk"))) == 1
