"""v9.7.244 — tab-reconcile returned the wrong region on any multi-region contig.

`_choose_record` computed `wanted_region` and never read it; `_gene_overview_summary` hardcoded
`areas[0]`. Asking for a lanthipeptide BGC on region003 of a multi-region contig reported
region001 (233558-275304, NRPS-like) and the whole contig's CDS count (535 instead of 22).

Invisible to the single-region reference fixture, whose contig carries exactly one region.

Shapes below are copied from the real AS-421 antiSMASH JSON (areas carry no region number; index order
IS the region number, and CDS locations look like `[635:3869](+)`).
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mamey.tab_reconcile import _region_index, _gene_overview_summary, _feature_in_span

REC = {
    "id": "NODE_2_length_553361_cov_80.858698",
    "areas": [
        {"start": 233558, "end": 275304, "products": ["NRPS-like"]},
        {"start": 332841, "end": 394488, "products": ["NRPS"]},
        {"start": 438609, "end": 463791, "products": ["lanthipeptide-class-i"]},
    ],
    "features": [
        {"type": "CDS", "location": "[233600:234500](+)", "qualifiers": {"locus_tag": "ctg2_249"}},
        {"type": "CDS", "location": "[333000:334000](-)", "qualifiers": {"locus_tag": "ctg2_330"}},
        {"type": "CDS", "location": "[438700:439900](+)", "qualifiers": {"locus_tag": "ctg2_435"}},
        {"type": "CDS", "location": "[448610:450643](+)", "qualifiers": {"locus_tag": "ctg2_439"}},
    ],
}


def test_region_label_maps_to_area_index():
    assert _region_index(REC, "region003") == 2
    assert _region_index(REC, "3") == 2
    assert _region_index(REC, "region001") == 0
    assert _region_index(REC, None) == 0            # unrequested -> first, as before
    assert _region_index(REC, "region099") == 0     # out of range -> clamp, never IndexError


def test_requested_region_reports_its_own_span_and_products():
    for idx, (span, prod) in enumerate([("233558-275304", "NRPS-like"),
                                        ("332841-394488", "NRPS"),
                                        ("438609-463791", "lanthipeptide-class-i")]):
        _, summary = _gene_overview_summary(REC, idx)
        assert f"span={span}" in summary, summary
        assert f"products={prod}" in summary, summary


def test_the_old_bug_would_have_reported_region001_for_bgc018():
    """Regression pin: areas[0] for a region003 request is the defect, not a fallback."""
    _, wrong = _gene_overview_summary(REC, 0)
    _, right = _gene_overview_summary(REC, 2)
    assert "233558-275304" in wrong and "438609-463791" in right
    assert "lanthipeptide-class-i" not in wrong


def test_cds_count_is_scoped_to_the_region_not_the_contig():
    n0, _ = _gene_overview_summary(REC, 0)
    n2, _ = _gene_overview_summary(REC, 2)
    assert n0 == 1, "region001 holds one CDS in this fixture"
    assert n2 == 2, "region003 holds two; the old code returned all 4 (the contig)"


def test_feature_in_span_handles_join_locations():
    assert _feature_in_span({"location": "[438700:439900](+)"}, 438609, 463791)
    assert not _feature_in_span({"location": "[10:20](+)"}, 438609, 463791)
    assert _feature_in_span({"location": "join{[438700:439000](+),[439500:439900](+)}"}, 438609, 463791)
    assert not _feature_in_span({"location": "malformed"}, 0, 100)
