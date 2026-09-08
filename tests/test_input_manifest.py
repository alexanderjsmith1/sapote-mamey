"""Behavior test for input_manifest.py (BB08). Proves: manifest pins inputs by sha256; a coverage GAP
exits 3 and is listed; full coverage exits 0. Self-contained (stdlib + subprocess)."""
import os, subprocess, sys, hashlib, tempfile, pathlib

def _find_root(name):
    # v9.7.356 seal fix: resolve the BUNDLE layout ("tools/") as well as the authoring
    # workspace ("Tools/"). The folded tests hardcoded "Tools/", which exists only in the
    # author's tree, so collection ERRORed in the shipped bundle and for every other user.
    for p in pathlib.Path(__file__).resolve().parents:
        for d in ("tools", "Tools"):
            if (p / d / name).exists():
                return p, d
    raise RuntimeError(f"tools/{name} not found above test")
ROOT, _TOOLDIR = _find_root("input_manifest.py")
TOOL = ROOT / _TOOLDIR / "input_manifest.py"
PY = ROOT / "Tools" / "bin" / "python3"
PY = str(PY) if PY.exists() else sys.executable


def _mk(d, name, content):
    p = pathlib.Path(d) / name
    p.write_text(content)
    return p


def test_manifest_pins_sha256_and_gap_exits_3(tmp_path):
    ins = tmp_path / "inputs"; ins.mkdir()
    _mk(ins, "AS-100.fna", ">x\nACGT\n")
    _mk(ins, "AS-200.fna", ">y\nTTTT\n")
    denom = tmp_path / "denom.txt"
    denom.write_text("AS-100\nAS-200\nAS-300\n")  # AS-300 missing -> gap
    out = tmp_path / "out"
    r = subprocess.run([PY, str(TOOL), "--label", "T", "--out", str(out),
                        "--inputs", str(ins), "--key-mode", "strain",
                        "--denominator", str(denom)], capture_output=True, text=True)
    assert r.returncode == 3, r.stderr
    man = (out / "T_INPUT_MANIFEST.tsv").read_text()
    assert "sha256" in man.splitlines()[0]
    # a real sha256 for AS-100.fna is present
    h = hashlib.sha256((ins / "AS-100.fna").read_bytes()).hexdigest()
    assert h in man
    cov = (out / "T_COVERAGE_REPORT.md").read_text()
    assert "AS-300" in cov and "GAP" in cov


def test_full_coverage_exits_0(tmp_path):
    ins = tmp_path / "inputs"; ins.mkdir()
    _mk(ins, "AS-100.fna", ">x\nACGT\n")
    denom = tmp_path / "denom.txt"; denom.write_text("AS-100\n")
    out = tmp_path / "out"
    r = subprocess.run([PY, str(TOOL), "--label", "T", "--out", str(out),
                        "--inputs", str(ins), "--key-mode", "strain",
                        "--denominator", str(denom)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "No gap" in (out / "T_COVERAGE_REPORT.md").read_text()
