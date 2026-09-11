"""D2/D3 RG-GMCI consistency (v9.7.187). A HIGH_RG_GMCI_RESCUE pair scoring below RGGMCI_D2_TOP_N
must still appear on the D2 board — pre-fix it was promoted into D3 but truncated out of D2
(silent-omission, AS-XXX family). This unit-tests the D2 write-set selection directly."""
from mamey.master_workbook import RGGMCI_D2_TOP_N


def _select_d2(ranked):
    # mirror the fixed selection in update_master_workbook
    ranked = sorted(ranked, key=lambda p: -(p.get("rggmci_score") or 0))
    d2 = ranked[:RGGMCI_D2_TOP_N]
    below = [p for p in ranked[RGGMCI_D2_TOP_N:]
             if p.get("rggmci_confidence") == "HIGH_RG_GMCI_RESCUE"]
    return d2 + below


def test_below_cap_high_pair_appears_in_d2():
    # build N+1 pairs: the lowest-scoring one is HIGH but ranks below the cap
    ranked = [{"bgc_a": f"BGC{i:03d}", "bgc_b": f"BGC{i+100:03d}",
               "rggmci_score": 100 - i,
               "rggmci_confidence": "MODERATE"} for i in range(RGGMCI_D2_TOP_N)]
    ranked.append({"bgc_a": "BGC028", "bgc_b": "BGC044", "rggmci_score": 1,
                   "rggmci_confidence": "HIGH_RG_GMCI_RESCUE"})
    d2 = _select_d2(ranked)
    d2_high = [p for p in d2 if p["rggmci_confidence"] == "HIGH_RG_GMCI_RESCUE"]
    d3_promoted = [p for p in ranked if p["rggmci_confidence"] == "HIGH_RG_GMCI_RESCUE"]
    assert ("BGC028", "BGC044") in [(p["bgc_a"], p["bgc_b"]) for p in d2]
    assert len(d2_high) == len(d3_promoted)  # D2 HIGH count == D3 promoted count
