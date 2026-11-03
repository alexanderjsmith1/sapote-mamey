"""DREL-032: an input that fails part-way through staging leaves nothing behind and fails the run."""
import json
import os
import pathlib
import subprocess
import sys
import zipfile

BUNDLE = pathlib.Path(__file__).resolve().parents[1]
PREP = BUNDLE / "tools" / "bigscape_prep.py"
GBK = "LOCUS test\n     CDS             1..30\n//\n"


def _zip(path, members):
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(f"{path.stem}.json", json.dumps({"strictness": "loose"}))
        for m in members:
            z.writestr(m, GBK)
    return path


def _run(tmp_path, *inputs):
    official = tmp_path / "OFFICIAL_DATA"
    official.mkdir(exist_ok=True)
    (official / "exclusions.json").write_text(json.dumps({"hard_excluded": []}))
    out = tmp_path / "out"
    env = dict(os.environ, MAMEY_OFFICIAL_DATA=str(official), MAMEY_DATA_ROOT=str(tmp_path))
    cmd = [sys.executable, str(PREP), "--inputs", *map(str, inputs), "--out", str(out), "--strictness", "loose"]
    return subprocess.run(cmd, capture_output=True, text=True, env=env), out


def test_colliding_input_is_removed_and_run_fails(tmp_path):
    first = _zip(tmp_path / "a" / "SYN-1.zip", ["NODE_1.region001.gbk"])
    # Same strain name; its second member collides with the first input's staged file.
    second = _zip(tmp_path / "b" / "SYN-1.zip", ["NODE_2.region001.gbk", "NODE_1.region001.gbk"])
    r, out = _run(tmp_path, first, second)
    assert r.returncode == 2
    staged = sorted(p.name for p in out.glob("*.gbk"))
    assert staged == ["SYN-1_NODE_1.region001.gbk"]  # the failed input's NODE_2 file is gone
    manifest = (out / "STRICTNESS_MANIFEST.tsv").read_text()
    assert "ERROR:ValueError" in manifest


def test_clean_inputs_still_stage(tmp_path):
    first = _zip(tmp_path / "a" / "SYN-1.zip", ["NODE_1.region001.gbk"])
    second = _zip(tmp_path / "b" / "SYN-2.zip", ["NODE_1.region001.gbk"])
    r, out = _run(tmp_path, first, second)
    assert r.returncode == 0, r.stderr
    assert len(list(out.glob("*.gbk"))) == 2
