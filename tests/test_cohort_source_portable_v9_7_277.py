"""v9.7.277 (engine 1.9.110): the gold run bakes the cross-strain cohort-source CSVs into
package/cohort_source/, and cohort-precompute assembles non-empty tables from a folder of
packages alone -- no re-parse of the antiSMASH source, no original zips. This is what makes
a sealed package a standalone, portable unit for cross-strain work.

Two independent checks:
  1. the gold run WIRES the emission (cohort_source/ + its receipt land in the sealed package);
  2. cohort-precompute RESOLVES sources from the portable package layout and fills the tables.
Check 2 uses a synthetic package so it does not depend on the smoke fixture carrying domains.
"""
from __future__ import annotations
import csv
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
ZIP = ROOT / "examples" / "test_data" / "smoke_antismash_small.zip"

ARCH_HEADER = ["Strain", "Rank", "BGC_ID", "Assembly_Locator", "Products",
               "architecture_archetype", "archetype_note", "n_domains",
               "domain_architecture_string"]


@pytest.mark.skipif(not ZIP.exists(), reason="smoke fixture stripped from the analysis-free tier")
def test_gold_run_wires_cohort_source_emission(tmp_path):
    """The gold run creates package/cohort_source/ (mechanism wired; non-blocking)."""
    out = tmp_path / "runs"
    r = subprocess.run(
        [sys.executable, "-m", "mamey.cli", "run", "--input-zip", str(ZIP),
         "--mode", "gold", "--outdir", str(out), "--strain", "SMOKE-A"],
        cwd=str(ROOT), capture_output=True, text=True, timeout=300,
    )
    assert r.returncode == 0, (r.stdout + r.stderr)[-2000:]
    cs = out / "SMOKE-A" / "package" / "cohort_source"
    assert cs.is_dir(), "cohort_source/ was not baked into the package"
    assert (cs / "domain_level_receipt.json").is_file(), "cohort_source receipt missing"


def _write_synthetic_package(strain_dir: Path, strain: str) -> None:
    """A minimal portable package: package/cohort_source/ with one architecture row."""
    cs = strain_dir / "package" / "cohort_source"
    cs.mkdir(parents=True)
    with open(cs / "ordered_domain_architectures_by_bgc.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(ARCH_HEADER)
        w.writerow([strain, "1", "BGC001", "NODE_1_length_10000_cov_50 region001",
                    "NRPS", "hybrid", "", "3", "A-PCP-C"])


def test_cohort_precompute_resolves_portable_baked_sources(tmp_path):
    """cohort-precompute reads sources from the baked package/cohort_source/ layout and
    produces a non-empty cohort table -- no source zip anywhere in the runs-dir."""
    cohort = tmp_path / "cohort"
    for sid in ("STRAIN-A", "STRAIN-B"):
        _write_synthetic_package(cohort / sid, sid)
    tables = tmp_path / "tables"
    r = subprocess.run(
        [sys.executable, "-m", "mamey.cli", "cohort-precompute",
         "--runs-dir", str(cohort), "--out", str(tables)],
        cwd=str(ROOT), capture_output=True, text=True, timeout=200,
    )
    assert r.returncode == 0, (r.stdout + r.stderr)[-2000:]
    arch = tables / "COHORT_domain_architecture_by_bgc.csv"
    assert arch.is_file(), "cohort domain-architecture table not written"
    with open(arch, encoding="utf-8") as fh:
        rows = list(csv.reader(fh))[1:]
    assert len(rows) == 2, f"expected 2 baked rows (one per strain), got {len(rows)}"
