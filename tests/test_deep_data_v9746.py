"""v9.7.46 (B-9/F-10) — gene-level deep_data emission + Mode B verdict scaffold.

The gene-by-gene deep dive degraded to verdict-less cards because the run never emitted deep_data.json or
modeb_verdicts.csv. These tests cover the deterministic verdict scaffold and the package emitter that
build the inputs the deep dive consumes.
"""
import json
import csv
from mamey.deep_data import (modeb_verdict_rows, build_deep_data_files, extract_profiles,
                             extract_finer, MODEB_VERDICT_HEADERS)


class _T:
    def __init__(self, bgc_id, standing="", pm=False, misanchor="", cap="NRPS"):
        self.bgc_id = bgc_id; self.standing_rule_flag = standing
        self.primary_metabolism_flag = pm; self.misanchor_flag = misanchor
        self.architecture_capacity = cap


def test_verdict_status_logic():
    triage = [
        _T("BGC001"),                                   # clean -> CONFIRM
        _T("BGC002", standing="saccharide-exclusion"),  # standing rule -> DOWNGRADE
        _T("BGC003", pm=True),                          # primary metab -> DROP
        _T("BGC004", misanchor="anchor_lacks_diag"),    # mis-anchor -> DOWNGRADE
    ]
    rows = {r["bgc"]: r for r in modeb_verdict_rows("ST-X", triage, {"BGC004"})}
    assert rows["BGC001"]["status"] == "CONFIRM"
    assert rows["BGC002"]["status"] == "DOWNGRADE" and "saccharide" in rows["BGC002"]["note"]
    assert rows["BGC003"]["status"] == "DROP"
    assert rows["BGC004"]["status"] == "DOWNGRADE" and "mis-anchor" in rows["BGC004"]["note"]


def test_verdict_headers_and_strain():
    rows = modeb_verdict_rows("ST-100", [_T("BGC001")])
    assert set(rows[0].keys()) == set(MODEB_VERDICT_HEADERS)
    assert rows[0]["strain"] == "ST-100"


def test_extract_finer_from_top_level_arrays():
    evidence = {
        "active_site_pairings": [{"record_id": "NODE_1", "locus_tag": "ctg1_5",
                                  "domain_id": "d1", "active_site_calls": ["malonyl-CoA specific"]}],
        "product_class_predictions": [{"record_id": "NODE_1", "module": "t2pks",
                                       "protocluster_id": "1", "product_classes": ["T2PKS"]}],
        "nrps_pks_consensus": [{"record_id": "NODE_1", "locus_tag": "ctg1_6",
                                "domain_id": "d2", "consensus_substrate": "mal"}],
        "ripp_cores": [{"record_id": "NODE_2", "ripp_family": "lanthipeptide", "core": "SCTTCV"}],
    }
    act, cls, subs, ripp = extract_finer("ST-100", {}, evidence)
    assert len(act) == 1 and act[0]["domain_id"] == "d1"
    assert len(cls) == 1 and "T2PKS" in cls[0]["predicted_products"]
    assert len(subs) == 1 and subs[0]["substrate"] == "mal"
    assert len(ripp) == 1 and ripp[0]["family"] == "lanthipeptide"


def test_extract_profiles_from_snapshot():
    snap = {"source_scans": {"domain_architecture": {"per_bgc": {
        "BGC001": {"domain_counts": {"PKS_KS": 2, "NRPS_A": 1}, "domains": []}}}}}
    profiles, archs, hits = extract_profiles("ST-100", snap)
    assert len(profiles) == 1
    p = profiles[0]
    assert p["PKS_KS"] == 2 and p["NRPS_A"] == 1 and p["total_domains"] == 3


def test_build_deep_data_files_writes_package(tmp_path):
    sid = "ST-100"
    (tmp_path / f"{sid}_Project_Memory_Snapshot.json").write_text(json.dumps(
        {"source_scans": {"domain_architecture": {"per_bgc": {
            "BGC001": {"domain_counts": {"PKS_KS": 1}, "domains": []}}}}}))
    (tmp_path / f"{sid}_AntiSMASH_Evidence_Parse.json").write_text(json.dumps(
        {"active_site_pairings": [{"record_id": "NODE_1", "active_site_calls": ["x"], "domain_id": "d"}]}))
    counts = build_deep_data_files(str(tmp_path), sid)
    assert (tmp_path / "deep_data.json").exists()
    assert (tmp_path / "gene_data.json").exists()
    deep = json.loads((tmp_path / "deep_data.json").read_text())
    assert counts["bgc_profile"] == 1 and len(deep["bgc_profile"]) == 1
    assert counts["active_sites"] == 1


def test_build_deep_data_degrades_gracefully_on_empty(tmp_path):
    # no snapshot / evidence present -> empty payloads, still writes valid files (does not raise).
    counts = build_deep_data_files(str(tmp_path), "ST-999")
    assert counts["bgc_profile"] == 0
    assert json.loads((tmp_path / "deep_data.json").read_text())["bgc_profile"] == []
