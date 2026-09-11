"""Regression — v9.7.412: bigscape_prep skips ruled hard-excluded strains.

Exists because on 2026-09-04 a curated BiG-SCAPE run silently staged AS-260 (hard_excluded in
OFFICIAL_DATA/exclusions.json, 174 region GBKs) — bigscape_prep honoured antiSMASH strictness but
NOT the exclusion ledger, so a contaminated assembly's BGCs entered the GCF network. This test pins
the fix: a hard-excluded strain is skipped-and-reported at stage time; a governed strain stages.

Hermetic: builds a temp OFFICIAL_DATA/exclusions.json + two fake antiSMASH zips, points the engine's
exclusion resolver at it via MAMEY_OFFICIAL_DATA, and runs the real tool as a subprocess.
Place in tests/: `pytest tests/test_bigscape_prep_exclusions_v97412.py`.
"""
import json
import os
import pathlib
import subprocess
import sys
import zipfile

BUNDLE = pathlib.Path(__file__).resolve().parents[1]
PREP = BUNDLE / "tools" / "bigscape_prep.py"


def _fake_antismash_zip(path, strain):
    # minimal: one region GBK so stage_zip has something to extract
    gbk = f"{strain}_contig1.region001.gbk"
    with zipfile.ZipFile(path, "w") as z:
        z.writestr(gbk, "LOCUS test\n//\n")


def _run(tmp_path, allow_excluded=False):
    official = tmp_path / "OFFICIAL_DATA"
    official.mkdir(parents=True, exist_ok=True)
    (official / "exclusions.json").write_text(json.dumps({"hard_excluded": ["AS-999"]}))
    indir = tmp_path / "zips"; indir.mkdir(exist_ok=True)
    _fake_antismash_zip(indir / "AS-999.zip", "AS-999")   # hard-excluded
    _fake_antismash_zip(indir / "AS-001.zip", "AS-001")   # governed
    out = tmp_path / "out"
    env = dict(os.environ, MAMEY_OFFICIAL_DATA=str(official), MAMEY_DATA_ROOT=str(tmp_path))
    cmd = [sys.executable, str(PREP), "--inputs", str(indir), "--out", str(out), "--allow-mixed"]
    if allow_excluded:
        cmd.append("--allow-excluded")
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    staged = {p.name.split("_")[0] for p in out.glob("*.gbk")} if out.exists() else set()
    manifest = (out / "STRICTNESS_MANIFEST.tsv").read_text() if (out / "STRICTNESS_MANIFEST.tsv").exists() else ""
    return staged, manifest, r.stderr


def test_hard_excluded_strain_is_skipped(tmp_path):
    staged, manifest, err = _run(tmp_path)
    assert "AS-001" in staged, f"governed strain must stage; staged={staged}"
    assert "AS-999" not in staged, f"hard-excluded strain must NOT stage; staged={staged}"
    assert "SKIP_HARD_EXCLUDED" in manifest and "AS-999" in manifest
    assert "hard-excluded" in err


def test_allow_excluded_override_stages_it(tmp_path):
    staged, _manifest, _err = _run(tmp_path, allow_excluded=True)
    assert "AS-999" in staged and "AS-001" in staged, f"override should stage both; staged={staged}"


def test_governed_strain_unaffected(tmp_path):
    staged, _m, _e = _run(tmp_path)
    assert "AS-001" in staged
