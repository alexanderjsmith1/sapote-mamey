"""The tab-reconcile ledger counts module evidence for the requested region only.

The TFBS, Pfam, TIGRFAM, NRPS/PKS, active-site, tailoring and TTA summaries used to walk the
whole antiSMASH record. On a 42-region chromosome every region showed 609 TFBS hits; region001
has 13. The record below copies the antiSMASH 8.0.4 JSON shapes: `hits_by_region` keyed by the
1-based region number, Pfam/TIGRFAM hits with `locus_tag`, nrps_pks keys
`nrpspksdomains_<locus_tag>_<domain>.<n>`, TTA codons as `{start, strand}` with `gc_content`
and `threshold`.
"""
from mamey import tab_reconcile as tr


def _cds(tag, a, b):
    return {"type": "CDS", "location": f"[{a}:{b}](+)", "qualifiers": {"locus_tag": [tag]}}


def _record(gc=0.70):
    return {
        "id": "CTG1",
        "areas": [{"start": 0, "end": 1000, "products": ["NRPS"]},
                  {"start": 5000, "end": 6000, "products": ["T1PKS"]}],
        "features": [_cds("A_1", 100, 400), _cds("B_1", 5100, 5600)],
        "modules": {
            "antismash.modules.tfbs_finder": {"hits_by_region": {
                "1": [{"name": "AbrC3", "confidence": "strong"}],
                "2": [{"name": "DasR", "confidence": "weak"}, {"name": "ZuR", "confidence": "medium"}]}},
            "antismash.detection.cluster_hmmer": {"hits": [
                {"locus_tag": "A_1", "domain": "Condensation", "location": "[100:400](+)"},
                {"locus_tag": "B_1", "domain": "PKS_KS", "location": "[5100:5600](+)"},
                {"locus_tag": "B_1", "domain": "PKS_AT", "location": "[5100:5600](+)"}]},
            "antismash.detection.tigrfam": {"hits": [{"locus_tag": "B_1", "domain": "TIGR01720"}]},
            "antismash.modules.nrps_pks": {
                "domain_predictions": {"nrpspksdomains_A_1_AMP-binding.1": {},
                                       "nrpspksdomains_B_1_PKS_KS.1": {}, "nrpspksdomains_B_1_PKS_AT.1": {}},
                "consensus": {"nrpspksdomains_B_1_PKS_AT.1": "mal"}},
            "antismash.modules.active_site_finder": {"pairings": [["nrpspksdomains_B_1_PKS_KS.1", ["ok"]]]},
            "antismash.modules.tta": {"TTA codons": [{"start": 150, "strand": 1}, {"start": 5200, "strand": 1},
                                                     {"start": 5300, "strand": -1}],
                                      "gc_content": gc, "threshold": 0.65},
        },
    }


def test_each_summary_counts_only_the_requested_region():
    rec = _record()
    one, two = tr._region_scope(rec, 0), tr._region_scope(rec, 1)
    assert one["tags"] == {"A_1"} and two["tags"] == {"B_1"}
    assert tr._tfbs_summary(rec, one)[0] == 1 and tr._tfbs_summary(rec, two)[0] == 2
    assert tr._pfam_summary(rec, one)[0] == 1 and tr._pfam_summary(rec, two)[0] == 2
    assert tr._tigrfam_summary(rec, one)[0] == 0 and tr._tigrfam_summary(rec, two)[0] == 1
    assert tr._nrps_pks_summary(rec, one)[0] == 1 and tr._nrps_pks_summary(rec, two)[0] == 2
    assert tr._active_site_summary(rec, one)[0] == 0 and tr._active_site_summary(rec, two)[0] == 1
    assert tr._tta_summary(rec, one)[0] == 1 and tr._tta_summary(rec, two)[0] == 2


def test_record_without_areas_keeps_record_totals():
    rec = _record()
    rec["areas"] = []
    assert tr._region_scope(rec, 0) is None
    assert tr._tfbs_summary(rec, None)[0] == 3
    assert tr._pfam_summary(rec, None)[0] == 3


def test_skipped_or_absent_scan_is_not_no_hits():
    low = _record(gc=0.60)
    n, raw = tr._tta_summary(low, tr._region_scope(low, 0))
    assert n == 0 and raw.startswith("NOT_RUN_LOW_GC")
    bare = _record()
    del bare["modules"]["antismash.modules.tfbs_finder"]
    del bare["modules"]["antismash.detection.tigrfam"]
    assert tr._tfbs_summary(bare, tr._region_scope(bare, 0)) == (0, "MODULE_ABSENT")
    assert tr._tigrfam_summary(bare, tr._region_scope(bare, 0)) == (0, "MODULE_ABSENT")
