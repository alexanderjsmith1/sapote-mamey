"""N-01: the ANALYSIS_FORWARD priority worklist must rank by Lead_tier_auto, not the raw triage Rank.

The triage Rank is a score-based routing prior for the judgment layer; a standing-rule/fragment downgrade
caps the lead TIER without zeroing the raw score, so ranking the worklist by Rank re-floats demoted Inventory
fragments above real High/Medium leads (worse on fragmented strains). This pins the tier-first ordering.
"""
from mamey.package_addons import _lead_tier_rank, _LEAD_TIER_ORDER


def test_tier_dominates_raw_rank():
    # an Inventory fragment with the BEST raw rank (1) must still sort AFTER a Medium lead with a worse rank
    inv = {"Lead_tier_auto": "Inventory", "Rank": "1"}
    med = {"Lead_tier_auto": "Medium", "Rank": "40"}
    assert _lead_tier_rank(med) < _lead_tier_rank(inv)


def test_full_tier_order():
    rows = [
        {"BGC_ID": "B_inv", "Lead_tier_auto": "Inventory", "Rank": "1"},
        {"BGC_ID": "B_high", "Lead_tier_auto": "High", "Rank": "9"},
        {"BGC_ID": "B_med", "Lead_tier_auto": "Medium", "Rank": "5"},
        {"BGC_ID": "B_exc", "Lead_tier_auto": "Exceptional", "Rank": "12"},
    ]
    order = [r["BGC_ID"] for r in sorted(rows, key=_lead_tier_rank)]
    assert order == ["B_exc", "B_high", "B_med", "B_inv"], order


def test_tie_break_within_tier_by_rank():
    rows = [
        {"BGC_ID": "A", "Lead_tier_auto": "High", "Rank": "7"},
        {"BGC_ID": "B", "Lead_tier_auto": "High", "Rank": "2"},
    ]
    assert [r["BGC_ID"] for r in sorted(rows, key=_lead_tier_rank)] == ["B", "A"]


def test_inventory_never_tops_a_real_lead_in_topN():
    # the audit's spec: no Inventory fragment may appear above a Medium/High lead in the top-N
    rows = ([{"BGC_ID": f"inv{i}", "Lead_tier_auto": "Inventory", "Rank": str(i)} for i in range(1, 6)]
            + [{"BGC_ID": "real", "Lead_tier_auto": "Medium", "Rank": "99"}])
    top = sorted(rows, key=_lead_tier_rank)[:3]
    ids = [r["BGC_ID"] for r in top]
    assert ids[0] == "real", ids   # the Medium lead leads the worklist despite its worse raw rank


def test_unknown_tier_sorts_last():
    rows = [{"BGC_ID": "x", "Lead_tier_auto": "", "Rank": "1"},
            {"BGC_ID": "y", "Lead_tier_auto": "Inventory", "Rank": "9"}]
    assert [r["BGC_ID"] for r in sorted(rows, key=_lead_tier_rank)] == ["y", "x"]
