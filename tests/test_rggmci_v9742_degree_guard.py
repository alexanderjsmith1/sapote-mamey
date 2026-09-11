"""v9.7.42 — component-degree guard (hub promiscuity).

From the recalibration: with MIBiG references counting toward geometry, a promiscuous hub on a fragmented
assembly becomes pairwise-HIGH with many partners (one strain showed 183 HIGH across 33 BGCs at degree 8-19). A genuine
cross-contig split rarely exceeds RGGMCI_MAX_HUB_DEGREE confidently-linked fragments, so a BGC over the cap is
a hub and its HIGH pairs demote to MODERATE. A clean low-degree co-cluster (degree-1 indolocarbazole) survives.
"""
import mamey.rggmci as rg


def _pair(a, b, conf="HIGH_RG_GMCI_RESCUE", gate="OK"):
    return {"bgc_a": a, "bgc_b": b, "rggmci_confidence": conf, "acceptance_gate": gate}


def test_low_degree_pair_survives():
    ranked = [_pair("BGC001", "BGC013")]  # degree 1 each
    rg._apply_hub_degree_guard(ranked)
    assert ranked[0]["rggmci_confidence"] == "HIGH_RG_GMCI_RESCUE"
    assert ranked[0]["max_endpoint_hub_degree"] == 1


def test_hub_web_collapses():
    # one hub BGCH linked to 6 partners -> degree 6 > cap(4) -> all its HIGH pairs demote.
    ranked = [_pair("BGCH", f"BGC{i:03d}") for i in range(6)]
    rg._apply_hub_degree_guard(ranked)
    assert all(r["rggmci_confidence"] == "MODERATE_RG_GMCI_CANDIDATE" for r in ranked)
    assert all("HUB_PROMISCUITY" in r["acceptance_gate"] for r in ranked)


def test_degree_exactly_at_cap_survives():
    # hub linked to exactly RGGMCI_MAX_HUB_DEGREE partners -> degree == cap -> NOT demoted (strictly >).
    n = rg.RGGMCI_MAX_HUB_DEGREE
    ranked = [_pair("BGCH", f"BGC{i:03d}") for i in range(n)]
    rg._apply_hub_degree_guard(ranked)
    assert all(r["rggmci_confidence"] == "HIGH_RG_GMCI_RESCUE" for r in ranked)
    assert ranked[0]["max_endpoint_hub_degree"] == n


def test_guard_only_demotes_high_pairs():
    # a MODERATE pair sharing the hub endpoint is not touched by the guard (only HIGH pairs demote).
    ranked = [_pair("BGCH", f"BGC{i:03d}") for i in range(6)]
    ranked.append(_pair("BGCH", "BGCX", conf="MODERATE_RG_GMCI_CANDIDATE"))
    rg._apply_hub_degree_guard(ranked)
    mod = [r for r in ranked if r["bgc_b"] == "BGCX"][0]
    assert mod["rggmci_confidence"] == "MODERATE_RG_GMCI_CANDIDATE"
    assert mod["acceptance_gate"] == "OK"  # untouched


def test_clean_co_cluster_survives_amid_web():
    # a degree-1 pair coexists with a hub web; only the web collapses.
    ranked = [_pair("BGCH", f"BGC{i:03d}") for i in range(6)]   # hub web
    ranked.append(_pair("BGCcore", "BGCtail"))                   # clean degree-1 co-cluster
    rg._apply_hub_degree_guard(ranked)
    clean = [r for r in ranked if r["bgc_a"] == "BGCcore"][0]
    assert clean["rggmci_confidence"] == "HIGH_RG_GMCI_RESCUE"
    assert all("HUB" in r["acceptance_gate"] for r in ranked if r["bgc_a"] == "BGCH")


def test_cap_constant_value():
    assert rg.RGGMCI_MAX_HUB_DEGREE == 4
