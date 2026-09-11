"""v9.7.88 Finding L (Option A): the deterministic core seals BEFORE the brief renders, so a
render hang can never block or un-seal the core."""
from __future__ import annotations
import json, os, subprocess, glob, tempfile
import pytest
import sys
from pathlib import Path

BUNDLE_ROOT = Path(__file__).resolve().parents[1]



def _run(outdir, synthetic_single_contig_full_locus_zip, extra_env=None):
    env = dict(os.environ, PYTHONPATH=str(BUNDLE_ROOT))
    if extra_env:
        env.update(extra_env)
    subprocess.run(
        [sys.executable, str(BUNDLE_ROOT / "mamey_run.py"), "run", "--strain", "SEALX", "--display", "ref",
         "--input-zip", str(synthetic_single_contig_full_locus_zip), "--taxonomy", "Streptomyces", "--source", "test",
         "--outdir", outdir, "--mode", "gold", "--release", "PUBLIC",
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


def test_seal_before_brief_default(tmp_path, synthetic_single_contig_full_locus_zip):
    out = str(tmp_path / "run")
    pkg = _run(out, synthetic_single_contig_full_locus_zip)
    seal_end, brief_start = _phase_order(pkg)
    assert seal_end is not None, "package must seal"
    if brief_start is not None:
        assert seal_end < brief_start, "core must seal BEFORE the brief renders"
    # supplementary marker present when brief rendered post-seal
    assert os.path.exists(os.path.join(pkg, "FIGURES_SUPPLEMENTARY.md"))


def test_core_zip_exists_regardless(tmp_path, synthetic_single_contig_full_locus_zip):
    out = str(tmp_path / "run")
    pkg = _run(out, synthetic_single_contig_full_locus_zip)
    # the Complete Package ZIP (the deterministic core) must exist
    zips = glob.glob(os.path.join(os.path.dirname(pkg), "*Complete_Package.zip"))
    assert zips, "the sealed core ZIP must exist"
