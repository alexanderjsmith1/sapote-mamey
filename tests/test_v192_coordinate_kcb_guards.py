"""v1.9.2 regression guards: absolute region coordinates + KCB-not-accession-tail.

Historically these two guards only ran against a local-only philanthi antiSMASH
fixture (`/mnt/data/...`), so the public tiers never exercised them. They now run
everywhere against a small shipped synthetic single-contig fixture
(`examples/test_data/synthetic_single_contig_antismash.zip`, 3 interior regions with
antiSMASH `Orig. start/end` absolute coords and distinct knownclusterblast scores).
The philanthi exact-value checks are retained below as a deeper local-only guard.
"""
from pathlib import Path
from collections import Counter

import pytest

from mamey.parsers import parse_bgcs_from_zip, assembly_metrics_from_zip

ROOT = Path(__file__).resolve().parents[1]
SYNTH = ROOT / "tests" / "fixtures" / "synthetic_single_contig_antismash.zip"
PHILANTHI = Path("/mnt/data/Streptomyces_philanthi_GCA_018114805.1_ASM1811480v1_antiSMASH(1).zip")


# ---- shipped synthetic fixture: runs in EVERY tier --------------------------------
@pytest.mark.skipif(not SYNTH.exists(), reason="synthetic fixture missing from bundle")
def test_single_contig_region_gbks_use_absolute_coordinates_synthetic(
    synthetic_single_contig_admitted_zip,
):
    ass = assembly_metrics_from_zip(synthetic_single_contig_admitted_zip)
    bgcs = parse_bgcs_from_zip(synthetic_single_contig_admitted_zip)
    assert ass.contigs == 1
    assert ass.n50 == ass.genome_bp
    # absolute coords recovered from Orig. start/end -> no region starts at 1, none Edge
    assert all(b.start > 1 for b in bgcs), "region starts collapsed to 1 (relative coords)"
    assert Counter(b.edge_status for b in bgcs) == {"Interior": len(bgcs)}
    assert all(b.contig_length == ass.genome_bp for b in bgcs)


@pytest.mark.skipif(not SYNTH.exists(), reason="synthetic fixture missing from bundle")
def test_kcb_scores_not_contig_accession_tail_synthetic(
    synthetic_single_contig_admitted_zip,
):
    bgcs = parse_bgcs_from_zip(synthetic_single_contig_admitted_zip)
    kcbs = [b.kcb_cumulative for b in bgcs if b.kcb_cumulative is not None]
    # 73042.1 is the numeric tail of the header accession "CP073042.1" — must NOT be a score
    assert all(v != 73042.1 for v in kcbs), "KCB read the contig-accession tail as a score"
    assert len(set(kcbs)) >= 2, "KCB scores collapsed to a single value"
    assert any(b.kcb_top for b in bgcs)


# ---- philanthi exact-value deep guard: local-only (skips in public tiers) ----------
@pytest.mark.skipif(not PHILANTHI.exists(), reason="philanthi antiSMASH fixture not present (local-only data file)")
def test_philanthi_absolute_coordinates_exact():
    ass = assembly_metrics_from_zip(PHILANTHI)
    bgcs = parse_bgcs_from_zip(PHILANTHI)
    assert ass.contigs == 1 and ass.n50 == ass.genome_bp
    assert len(bgcs) == 38 and Counter(b.edge_status for b in bgcs) == {"Interior": 38}
    assert all(b.start > 1 for b in bgcs)
    assert all(b.contig_length == ass.genome_bp for b in bgcs)


@pytest.mark.skipif(not PHILANTHI.exists(), reason="philanthi antiSMASH fixture not present (local-only data file)")
def test_philanthi_kcb_not_accession_tail_exact():
    bgcs = parse_bgcs_from_zip(PHILANTHI)
    assert all(b.kcb_cumulative != 73042.1 for b in bgcs)
    assert len({b.kcb_cumulative for b in bgcs if b.kcb_cumulative is not None}) > 10
    assert any(b.kcb_top for b in bgcs)
