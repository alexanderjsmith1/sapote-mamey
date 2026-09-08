from mamey.dkp_cdps import classify_query_gene, scan_dkp_cdps
from mamey.models import BGCRecord, CDSFeature


def test_dkp_cdps_detects_product_call_and_cdo_context():
    bgc = BGCRecord("BGC001", "ctg1", 1, 100, 1000, 2000, products=["CDPS", "NRPS"], edge_status="Interior", source_gbk="ctg1.region001.gbk")
    cds = [
        CDSFeature("ctg1", 200, 500, 1, "cdsA", "cyclodipeptide synthase", "", "", {}),
        CDSFeature("ctg1", 600, 800, 1, "albA", "albonoursin biosynthesis nitroreductase", "", "", {}),
        CDSFeature("ctg1", 900, 950, 1, "reg", "LuxR transcriptional regulator", "", "", {}),
    ]
    out = scan_dkp_cdps("TEST", [bgc], cds)
    assert out["count"] == 1
    call = out["calls"][0]
    assert call["marker_family"] == "DKP_CDPS_cyclodipeptide"
    assert call["diagnostic_cdps_present"] == "yes"
    assert call["cdo_adjacent"] == "yes"
    assert call["dkp_grade"].startswith("DKP-A")
    assert "specific dipeptide/product requires isolation" in call["claim_ceiling"]


def test_gene_classification_excludes_self_and_housekeeping():
    assert classify_query_gene("AAN07911.1", "putative NADP-specific glutamate dehydrogenase", {}, 100.0, 100.0, "AAN07911.1", "AAN07911.1") == "self-hit"
    assert classify_query_gene("foo", "putative NADP-specific glutamate dehydrogenase", {}, 82.0, 90.0, "x", "y") == "housekeeping/conserved"
    assert classify_query_gene("albC", "cyclodipeptide synthase", {}, 48.0, 85.0, "x", "y") == "biosynthetic-diagnostic"
