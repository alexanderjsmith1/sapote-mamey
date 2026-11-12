"""TFBS and bldA scan states must not read as a completed scan when no sequence was available.

scan_tfbs skips every CDS whose contig sequence is missing; scan_blda_tta gives NOT_COMPUTED when no
CDS sequence was read. The scan pack used to report TFBS NULL "no hits" and bldA PASS for those cases.
"""
from mamey.external_adapters import run_external_scan_pack
from mamey.models import CDSFeature, SourceScanBundle
from mamey.source_scans import scan_tfbs

_EMPTY = {"status": "NULL", "counts": {}, "bgc_coupling": {}}


def _bundle(tfbs=None, blda=None):
    return SourceScanBundle(
        chitinase=dict(_EMPTY), tfbs=tfbs or dict(_EMPTY), blda_tta=blda or dict(_EMPTY),
        regulators=dict(_EMPTY), transporters=dict(_EMPTY), resistance=dict(_EMPTY),
        cctt=dict(_EMPTY), flbr=dict(_EMPTY), cassettes=dict(_EMPTY), umed={"per_bgc": {}},
        efls=dict(_EMPTY), domain_architecture=dict(_EMPTY), resistance_tiers={"per_bgc": {}},
        wetlab_rows={}, qs_signals=dict(_EMPTY), glycosylation_arms=dict(_EMPTY),
        per_bgc_dss={}, rggmci={},
    )


def _scan(name, bundle, taxonomy="Streptomyces sp."):
    out = run_external_scan_pack(bundle, antismash_evidence={}, taxonomy=taxonomy)
    return next(r for r in out["scans"] if r[0] == name)


def _cds(tag, contig="C1"):
    return CDSFeature(contig, 400, 700, 1, tag, "synthetic")


def test_scan_tfbs_reports_how_many_cds_it_had():
    res = scan_tfbs({}, [_cds("a"), _cds("b")])
    assert (res["cds_total"], res["missing_contig_count"], res["total_hits"]) == (2, 2, 0)


def test_tfbs_with_no_contig_sequence_is_failed():
    _, state, detail = _scan("TFBS", _bundle(tfbs=scan_tfbs({}, [_cds("a"), _cds("b")])))
    assert state == "FAILED"
    assert "not a negative" in detail and "no hits" not in detail


def test_tfbs_partial_gap_stays_null_and_names_it():
    res = scan_tfbs({"C1": "A" * 1000}, [_cds("a"), _cds("b", contig="C2")])
    _, state, detail = _scan("TFBS", _bundle(tfbs=res))
    assert state == "NULL"
    assert "1 CDS skipped (no contig sequence)" in detail


def test_tfbs_older_scan_dict_keeps_its_reading():
    _, state, detail = _scan("TFBS", _bundle())
    assert (state, detail) == ("NULL", "no hits")


def test_blda_all_not_computed_is_failed():
    blda = {"per_bgc": {"BGC001": {"bldA_tier": "NOT_COMPUTED"}, "BGC002": {"bldA_tier": "NOT_COMPUTED"}}}
    _, state, detail = _scan("bldA_TTA", _bundle(blda=blda))
    assert state == "FAILED" and "not a negative" in detail


def test_blda_partly_not_computed_counts_only_the_read_bgcs():
    blda = {"per_bgc": {"BGC001": {"bldA_tier": "T4"}, "BGC002": {"bldA_tier": "NOT_COMPUTED"}}}
    _, state, detail = _scan("bldA_TTA", _bundle(blda=blda))
    assert state == "PASS"
    assert detail == "1 BGCs assessed; 1 T4; 1 BGCs not computed (no CDS sequence)"


def test_blda_non_actino_gate_unchanged():
    blda = {"per_bgc": {"BGC001": {"bldA_tier": "NOT_APPLICABLE"}}}
    assert _scan("bldA_TTA", _bundle(blda=blda), taxonomy="Fungi sp.")[1] == "NOT_APPLICABLE"
