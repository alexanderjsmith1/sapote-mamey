from mamey.compat_v941 import compatibility_fields_for_bgc, EFLS_CEILING, DKP_CEILING
from mamey.models import BGCRecord, SourceScanBundle


def _ss():
    return SourceScanBundle(
        chitinase={}, tfbs={}, blda_tta={}, regulators={}, transporters={}, resistance={},
        cctt={
            "bgc_coupling": {"BGC001": ["T43-DKP_cdps"], "BGC002": ["T43-HAL_halogenase"]},
            "dkp_cdps_context": {"calls": [{"bgc_id":"BGC001", "cdps_loci":"albC", "cdo_adjacent":"yes", "cdo_loci":"albA", "tailoring_context":"no"}]},
        },
        flbr={}, cassettes={}, umed={},
        efls={"candidate_pairs": [{"bgc_a":"BGC002", "bgc_b":"BGC003", "score":3}]},
        domain_architecture={},
        resistance_tiers={"per_bgc": {}}, wetlab_rows={}, qs_signals={}, glycosylation_arms={},
        per_bgc_dss={"per_bgc":{"BGC001":{"dss":3}, "BGC002":{"dss":1}}}, rggmci={},
    )


def test_v941_dkp_a_and_claim_ceiling():
    bgc = BGCRecord("BGC001", "ctg", 1, 1, 100, 1000, products=["CDPS", "NRPS"], edge_status="Interior")
    bgc.closest_product_provenance = "MIBIG_REFERENCE_LINE"
    bgc.closest_mibig_accession = "BGC0001986.3"
    fields = compatibility_fields_for_bgc(bgc, None, _ss())
    assert fields["dkp_rank"] == "DKP-A"
    assert fields["dkp_claim_ceiling"] == DKP_CEILING
    assert fields["claim_confidence"] in {"HIGH", "MODERATE"}
    assert "requires isolation" in fields["safe_claim"]
    assert fields["efls_status"] == "NOT_APPLICABLE_INTERIOR"


def test_v941_efls_edge_fields_do_not_claim_merge():
    bgc = BGCRecord("BGC002", "ctg2", 2, 1, 100, 1000, products=["NRPS"], edge_status="Edge")
    fields = compatibility_fields_for_bgc(bgc, None, _ss())
    assert fields["efls_status"] == "FLANK_REVIEWED"
    assert fields["cross_contig_candidate_set"] == "BGC003"
    assert fields["efls_claim_ceiling"] == EFLS_CEILING
    assert fields["claim_ceiling"] == bgc.product_claim_ceiling
