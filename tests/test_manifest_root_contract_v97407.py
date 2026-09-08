from __future__ import annotations

from mamey import BUNDLE_VERSION
from mamey.models import AssemblyMetrics, BGCRecord, MameyRun, RunContext


def _run(*, second_release: str | None = None) -> MameyRun:
    bgcs = [BGCRecord(
        bgc_id="BGC001",
        contig="NODE_1_length_1000_cov_1",
        region_number=1,
        start=10,
        end=900,
        contig_length=1000,
        products=["RiPP"],
        antismash_region="region001",
        node_id="NODE_1_length_1000_cov_1",
        release="PRIVATE",
        privacy_tier="RESTRICTED",
        privacy_assignment_state="EXACT",
    )]
    if second_release is not None:
        bgcs.append(BGCRecord(
            bgc_id="BGC002",
            contig="NODE_2_length_1000_cov_1",
            region_number=2,
            start=10,
            end=900,
            contig_length=1000,
            products=["NRPS"],
            antismash_region="region002",
            node_id="NODE_2_length_1000_cov_1",
            release=second_release,
            privacy_tier="RESTRICTED",
            privacy_assignment_state="EXACT",
        ))
    return MameyRun(
        context=RunContext(
            strain_id="SYNTHETIC-001",
            display_name="Synthetic 001",
            version="1.9.146",
            analysis_mode="gold",
            input_zip="synthetic.zip",
            outdir="out",
        ),
        assembly=AssemblyMetrics(
            genome_bp=2000, contigs=2, n50=1000, gc_pct=70.0, largest_contig=1000,
        ),
        bgcs=bgcs,
        scan_status={},
    )


def test_full_manifest_carries_reader_owned_release_privacy_and_bundle_fields():
    manifest = _run().to_dict()
    assert manifest["bundle_version"] == BUNDLE_VERSION
    assert manifest["release"] == "PRIVATE"
    assert manifest["privacy_tier"] == "RESTRICTED"
    assert manifest["privacy_assignment_state"] == "EXACT"


def test_full_manifest_fails_closed_on_mixed_release_values():
    manifest = _run(second_release="PUBLIC").to_dict()
    assert manifest["release"] == "UNRESOLVED_MIXED"
