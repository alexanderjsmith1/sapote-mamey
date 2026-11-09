"""bigscape_prep: an admitted input with no region GBK is recorded EMPTY, never STAGED."""
import json
import os
import pathlib
import subprocess
import sys
import zipfile

PREP = pathlib.Path(__file__).resolve().parents[1] / "tools" / "bigscape_prep.py"


def _zip(path, regions=True):
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(f"{path.stem}.json", json.dumps({"strictness": "loose"}))
        if regions:
            z.writestr("NODE_1.region001.gbk", "LOCUS test\n     CDS             1..30\n//\n")
        else:
            z.writestr(f"{path.stem}.gbk", "LOCUS whole\n//\n")
    return path


def _run(tmp_path, *inputs):
    official = tmp_path / "OFFICIAL_DATA"
    official.mkdir(exist_ok=True)
    (official / "exclusions.json").write_text(json.dumps({"hard_excluded": []}))
    out = tmp_path / "out"
    env = dict(os.environ, MAMEY_OFFICIAL_DATA=str(official), MAMEY_DATA_ROOT=str(tmp_path))
    r = subprocess.run([sys.executable, str(PREP), "--inputs", *map(str, inputs), "--out", str(out),
                        "--strictness", "loose"], capture_output=True, text=True, env=env)
    rows = [line.split("\t") for line in (out / "STRICTNESS_MANIFEST.tsv").read_text().splitlines()[1:]]
    return r, {row[0]: row for row in rows}


def test_zero_region_input_is_empty_not_staged(tmp_path):
    r, rows = _run(tmp_path, _zip(tmp_path / "SYN-1.zip"), _zip(tmp_path / "SYN-2.zip", regions=False))
    assert r.returncode == 0, r.stderr
    assert rows["SYN-1"][2] == "STAGED" and rows["SYN-1"][3] == "1"
    assert rows["SYN-2"][2] == "EMPTY_NO_REGION_GBKS" and rows["SYN-2"][3] == "0"
    assert "EMPTY_INPUTS: 1" in r.stderr
    assert "not a biological absence" in r.stderr
