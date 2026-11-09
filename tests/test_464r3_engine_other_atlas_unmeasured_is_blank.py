"""RG-GMCI rescue atlas: unmeasured reference values are blank, not zero.

Before: a reference whose roster never loaded showed `reference_total_proteins` 0 and coverage 0.0,
and a pair with no shared reference got a D row full of zero medians and rank 999, with a reason that
spoke of a "shared-reference signal". Tiers and scores are unchanged: an unmeasured value still gives
no credit in the calculation.
"""
import io
import tarfile

from mamey.rggmci_rescue_atlas import TIERS, build_atlas, read_mibig_rosters

A = "SYNTH-01 / contig_alpha_full / region001 / BGC001"
B = "SYNTH-01 / contig_beta_full / region002 / BGC002"
PAIR = [{"strain": "SYNTH-01", "pair": "BGC001+BGC002", "identity_a": A, "identity_b": B,
         "rggmci_score": "40", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE",
         "subject_tiling_verdict": "TERMINUS_TRUNCATION_SPLIT", "terminus_override_note": ""}]
LOCI = [{"complete_identity": A, "boundary": "Edge", "current_antismash_products": "RiPP"},
        {"complete_identity": B, "boundary": "Full-contig", "current_antismash_products": "RiPP"}]


def _hits(identity, proteins, accession="BGC0000001.1"):
    return [{"complete_identity": identity, "query_gene": f"q{i}", "subject_gene": protein,
             "mibig_accession": accession, "mibig_product": "synthetic comparator",
             "pct_identity": "60", "pct_coverage_interpretation": "90", "reference_rank": "1"}
            for i, protein in enumerate(proteins, 1)]


def _archive(path):
    text = "LOCUS       BGC0000001\n" + "".join(f'   /protein_id="P{i}"\n' for i in range(1, 13))
    with tarfile.open(path, "w:gz") as tar:
        data = text.encode()
        info = tarfile.TarInfo("BGC0000001.gbk")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))


def test_unloaded_roster_leaves_denominator_and_coverage_blank(tmp_path):
    hits = _hits(A, ["P1", "P2", "P3", "P4", "P5"]) + _hits(B, ["P6", "P7", "P8", "P9", "P10"])
    ranked, details = build_atlas(PAIR, LOCI, hits, rosters={})
    row = ranked[0]
    assert row["reference_roster_state"] == "REFERENCE_ROSTER_NOT_LOADED"
    assert row["reference_total_proteins"] == "" and row["reference_protein_coverage"] == ""
    assert "reference_protein_coverage" in row["unmeasured_fields"]
    assert "not measured" in row["tier_reason"]
    assert details[0]["reference_protein_coverage"] == ""
    # No credit for the unmeasured coverage: the strict tiers that need coverage stay out of reach.
    assert row["evidence_tier"] not in TIERS[:2]


def test_loaded_roster_still_reports_measured_values(tmp_path):
    archive = tmp_path / "mibig.tar.gz"
    _archive(archive)
    hits = _hits(A, ["P1", "P2", "P3", "P4", "P5"]) + _hits(B, ["P6", "P7", "P8", "P9", "P10"])
    row = build_atlas(PAIR, LOCI, hits, read_mibig_rosters(archive))[0][0]
    assert row["reference_total_proteins"] == 12 and row["reference_protein_coverage"] > 0
    assert row["unmeasured_fields"] == ""
    assert row["evidence_tier"] == TIERS[0]


def test_no_shared_reference_is_blank_and_says_what_was_not_found():
    hits = _hits(A, ["P1", "P2"], "BGC0000001.1") + _hits(B, ["Q1", "Q2"], "BGC0000002.1")
    row = build_atlas(PAIR, LOCI, hits, rosters={})[0][0]
    assert row["reference_tiling_topology"] == "NO_SHARED_EXACT_REFERENCE"
    for key in ("median_identity", "median_alignment_coverage", "reference_protein_coverage",
                "reference_total_proteins", "max_reference_rank", "subject_disjointness"):
        assert row[key] == "", key
    assert row["evidence_tier"] == TIERS[3]
    assert "shared-reference signal" not in row["tier_reason"]
    assert "not evidence that no shared reference exists" in row["tier_reason"]
