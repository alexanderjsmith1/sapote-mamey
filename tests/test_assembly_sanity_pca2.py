"""PC-A2 (v9.7.101): non-blocking assembly-sanity / contamination gate.

Two VERY_POOR drafts passed as MAMEY_COMPLETE with no flag despite bimodal-GC /
foreign-content pathology. assembly_sanity_check must flag the bimodal case and
leave a clean unimodal high-GC genome alone.
"""
from mamey.assembly import assembly_sanity_check


# AMBER-03-3: the synthetic "clean genome" below used to total 300 kb — smaller than
# any actinomycete, and therefore now (correctly) caught by the partial-submission
# size floor. Scaled ~10x to a realistic ~3.2 Mb. GC ratios, and every assertion in
# this file, are unchanged; only the fixture's size is realistic now.
def _hi_gc_contig(gc_blocks=380000, at_blocks=150000):
    # ~72% GC
    return "GC" * gc_blocks + "AT" * at_blocks


def _lo_gc_contig(at_blocks=300000, gc_blocks=220000):
    # ~46% GC (foreign for a high-GC actinomycete)
    return "AT" * at_blocks + "GC" * gc_blocks


def test_clean_unimodal_high_gc_not_flagged():
    seqs = {"c1": _hi_gc_contig(), "c2": _hi_gc_contig(), "c3": _hi_gc_contig()}
    res = assembly_sanity_check(seqs)
    assert res["flags"] == [], f"clean genome should not be flagged: {res}"
    assert res["per_contig_gc_sd"] is not None and res["per_contig_gc_sd"] < 2.0


def test_bimodal_gc_flagged_contamination_suspect():
    seqs = {"c1": _hi_gc_contig(), "c2": _hi_gc_contig(), "foreign": _lo_gc_contig()}
    res = assembly_sanity_check(seqs)
    assert "CONTAMINATION_SUSPECT" in res["flags"], f"bimodal GC should flag: {res}"
    assert res["per_contig_gc_sd"] >= 5.0


def test_gc_prior_deviation_flags_sanity():
    # a genome-wide GC far from a taxon prior fires ASSEMBLY_SANITY even if unimodal
    seqs = {"c1": _lo_gc_contig(), "c2": _lo_gc_contig()}
    res = assembly_sanity_check(seqs, expected_gc=72.0)
    assert "ASSEMBLY_SANITY" in res["flags"]


def test_size_outside_range_flags_sanity():
    seqs = {"c1": _hi_gc_contig(), "c2": _hi_gc_contig()}
    # claim an expected range far below the assembled size
    res = assembly_sanity_check(seqs, expected_size_bp=(1_000, 2_000))
    assert "ASSEMBLY_SANITY" in res["flags"]


def test_non_blocking_returns_stats():
    res = assembly_sanity_check({"c1": _hi_gc_contig()})
    assert "overall_gc" in res and "genome_bp" in res and "claim_safety" in res
