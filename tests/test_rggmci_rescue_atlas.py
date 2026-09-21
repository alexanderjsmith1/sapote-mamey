import io
import tarfile
from pathlib import Path

import pytest

from mamey.rggmci_rescue_atlas import (
    CLAIM_CEILING, build_atlas, exact_identity_parts, read_mibig_rosters, write_atlas,
)


A = "SYNTH-01 / contig_alpha_full / region001 / BGC001"
B = "SYNTH-01 / contig_beta_full / region002 / BGC002"


def _archive(path: Path):
    text = "LOCUS       BGC0000001\nFEATURES             Location/Qualifiers\n" + "".join(
        f"     CDS             1..3\n                     /protein_id=\"P{i}\"\n" for i in range(1, 13)
    )
    with tarfile.open(path, "w:gz") as tar:
        data = text.encode()
        info = tarfile.TarInfo("BGC0000001.gbk")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))


def _hits(identity, proteins, rank=1):
    return [{"complete_identity": identity, "query_gene": f"q{i}", "subject_gene": protein,
             "mibig_accession": "BGC0000001.1", "mibig_product": "synthetic comparator",
             "pct_identity": "60", "pct_coverage_interpretation": "90", "reference_rank": str(rank)}
            for i, protein in enumerate(proteins, 1)]


def test_complete_identity_fails_closed():
    assert exact_identity_parts(A) == ("SYNTH-01", "contig_alpha_full", "region001", "BGC001")
    with pytest.raises(ValueError, match="IDENTITY_HOLD"):
        exact_identity_parts("SYNTH-01 / BGC001")


def test_complementary_pair_is_transparent_and_non_promoting(tmp_path):
    archive = tmp_path / "mibig.tar.gz"
    _archive(archive)
    pair = [{"strain": "SYNTH-01", "pair": "BGC001+BGC002", "identity_a": A, "identity_b": B,
             "rggmci_score": "40", "rggmci_confidence": "HIGH_RG_GMCI_RESCUE",
             "subject_tiling_verdict": "TERMINUS_TRUNCATION_SPLIT", "terminus_override_note": ""}]
    loci = [{"complete_identity": A, "boundary": "Edge", "current_antismash_products": "RiPP"},
            {"complete_identity": B, "boundary": "Full-contig", "current_antismash_products": "RiPP"}]
    hits = _hits(A, ["P1", "P2", "P3", "P4", "P5"]) + _hits(B, ["P6", "P7", "P8", "P9", "P10"])
    ranked, details = build_atlas(pair, loci, hits, read_mibig_rosters(archive))
    assert len(ranked) == 1 and len(details) == 1
    row = ranked[0]
    assert row["reference_tiling_topology"] == "DISJOINT_ADJACENT_SEGMENTS"
    assert row["evidence_tier"] == "A_CONTROL_GRADE_COMPLEMENTARY_RESCUE"
    assert row["rggmci_confidence"] == pair[0]["rggmci_confidence"]
    receipt = write_atlas(tmp_path / "out", ranked, details)
    assert receipt["status"] == "PASS"
    assert CLAIM_CEILING in (tmp_path / "out/RGGMCI_RESCUE_ATLAS.md").read_text()


def test_same_reference_proteins_are_held(tmp_path):
    archive = tmp_path / "mibig.tar.gz"
    _archive(archive)
    pair = [{"strain": "SYNTH-01", "identity_a": A, "identity_b": B,
             "rggmci_confidence": "HIGH_RG_GMCI_RESCUE", "subject_tiling_verdict": "OVERLAPPING_PARALOG"}]
    loci = [{"complete_identity": A, "boundary": "Interior"}, {"complete_identity": B, "boundary": "Interior"}]
    hits = _hits(A, ["P1", "P2", "P3"]) + _hits(B, ["P1", "P2", "P3"])
    ranked, _ = build_atlas(pair, loci, hits, read_mibig_rosters(archive))
    assert ranked[0]["evidence_tier"] == "D_SHARED_REFERENCE_OR_GENERIC_HOLD"
    assert ranked[0]["shared_subjects"] == 3
