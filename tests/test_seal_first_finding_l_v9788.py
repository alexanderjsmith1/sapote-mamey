"""v9.7.88 Finding L (Option A): the deterministic core seals BEFORE the brief renders, so a
render hang can never block or un-seal the core."""
from __future__ import annotations
import json, os, subprocess, glob, tempfile
import pytest

REF = next((p for p in ["/mnt/user-data/uploads/BGC0000093.zip",
                        "/mnt/user-data/uploads/BGC0000218.zip"] if os.path.exists(p)), None)
pytestmark = pytest.mark.skipif(REF is None, reason="no public reference cluster present")


def _run(outdir, extra_env=None):
    env = dict(os.environ, PYTHONPATH=".")
    if extra_env:
        env.update(extra_env)
    subprocess.run(
        ["python3", "-m", "mamey", "run", "--strain", "SEALX", "--display", "ref",
         "--input-zip", REF, "--taxonomy", "Streptomyces", "--source", "test",
         "--outdir", outdir, "--mode", "standard", "--release", "PUBLIC",
         "--json-evidence", "bounded", "--brief", "standard"],
        check=True, capture_output=True, timeout=300, env=env)
    return glob.glob(os.path.join(outdir, "**", "package"), recursive=True)[0]


def _phase_order(pkg):
    rows = [json.loads(l) for l in open(os.path.join(pkg, "run_phase_receipts.jsonl")) if l.strip()]
    seal_end = next((i for i, r in enumerate(rows)
                     if r["phase"] == "package_seal" and r["status"] == "END"), None)
    brief_start = next((i for i, r in enumerate(rows)
                        if r["phase"] == "brief_render" and r["status"] == "START"), None)
    return seal_end, brief_start


def test_seal_before_brief_default():
    out = tempfile.mkdtemp(prefix="sealf_")
    pkg = _run(out)
    seal_end, brief_start = _phase_order(pkg)
    assert seal_end is not None, "package must seal"
    if brief_start is not None:
        assert seal_end < brief_start, "core must seal BEFORE the brief renders"
    # supplementary marker present when brief rendered post-seal
    assert os.path.exists(os.path.join(pkg, "FIGURES_SUPPLEMENTARY.md"))


def test_core_zip_exists_regardless():
    out = tempfile.mkdtemp(prefix="sealz_")
    pkg = _run(out)
    # the Complete Package ZIP (the deterministic core) must exist
    zips = glob.glob(os.path.join(os.path.dirname(pkg), "*Complete_Package.zip"))
    assert zips, "the sealed core ZIP must exist"
