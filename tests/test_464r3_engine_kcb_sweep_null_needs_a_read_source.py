"""The KCB sweep is NULL only when a KCB source was read; with none it is FAILED, not a negative.

The scan adapter set `KCB_sweep` to NULL whenever parsed-region and loose-hit counts were zero,
so an archive with no KCB source looked the same as one searched with no hits.
"""
from mamey.external_adapters import run_external_scan_pack
from mamey.models import SourceScanBundle

_EMPTY = {"status": "NULL", "counts": {}, "bgc_coupling": {}}


def _bundle():
    return SourceScanBundle(
        chitinase=dict(_EMPTY), tfbs=dict(_EMPTY), blda_tta=dict(_EMPTY),
        regulators=dict(_EMPTY), transporters=dict(_EMPTY), resistance=dict(_EMPTY),
        cctt=dict(_EMPTY), flbr=dict(_EMPTY), cassettes=dict(_EMPTY), umed={"per_bgc": {}},
        efls=dict(_EMPTY), domain_architecture=dict(_EMPTY), resistance_tiers={"per_bgc": {}},
        wetlab_rows={}, qs_signals=dict(_EMPTY), glycosylation_arms=dict(_EMPTY),
        per_bgc_dss={}, rggmci={},
    )


def _kcb(evidence):
    out = run_external_scan_pack(_bundle(), antismash_evidence=evidence)
    return next(r for r in out["scans"] if r[0] == "KCB_sweep")


def test_no_source_is_failed_not_null():
    name, state, detail = _kcb({"status": "NO_KCB_SOURCE_FOUND", "by_region": {}, "loose_hits": [],
                                "txt_files": [], "json_files": []})
    assert state == "FAILED" and "not a negative" in detail


def test_all_txt_unreadable_is_failed():
    name, state, detail = _kcb({"by_region": {}, "loose_hits": [], "txt_files": ["a.txt"], "json_files": [],
                                "txt_parse_receipt": [{"source": "a.txt", "state": "READ_FAILED"}]})
    assert state == "FAILED"


def test_a_read_source_with_no_hits_is_null():
    name, state, detail = _kcb({"status": "NO_KCB_SOURCE_FOUND", "by_region": {}, "loose_hits": [],
                                "txt_files": ["knownclusterblast/r1.txt"], "json_files": [],
                                "txt_parse_receipt": [{"source": "knownclusterblast/r1.txt",
                                                       "state": "NO_HITS_TEXT_UNVALIDATED"}]})
    assert state == "NULL" and detail.startswith("source read")


def test_hits_are_still_pass():
    name, state, detail = _kcb({"by_region": {"r1": [{}]}, "loose_hits": [], "txt_files": ["x.txt"]})
    assert state == "PASS"
