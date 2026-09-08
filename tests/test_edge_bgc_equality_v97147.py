from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_edge_equality_replaces_partial_modeb_stub():
    monolith = text("docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md")
    assert "### 15.4 Edge/FC BGC presentation (v9.7.147)" in monolith
    assert "Assembly boundary status is a metadata flag, not a depth limiter" in monolith
    assert "The boundary caveat belongs in §3 and §19" in monolith
    assert "### 15.4 Partial Mode B for Edge/FC/poor-assembly BGCs\nSame §1–§8" not in monolith


def test_triage_sort_is_not_interior_first():
    slim = text("docs/SAPOTE_SLIM_JUDGMENT_KERNEL.md")
    execution = text("docs/CHATGPT_EXECUTION_SLICE_v97147.md")
    assert "Sort all BGCs by `Corrected_rank`" in slim
    assert "Sort all BGCs by `Corrected_rank`" in execution
    assert "List Interior BGCs first (sorted by AB_auto desc), then Edge, then FC" not in slim


def test_poor_tier_edge_penalty_removed():
    full_run = text("prompts/FULL_RUN_PROFILE.md")
    monolith = text("docs/SAPOTE_MAMEY_BUNDLE_MONOLITH.md")
    execution = text("docs/CHATGPT_EXECUTION_SLICE_v97147.md")
    for doc in (full_run, monolith, execution):
        assert "POOR/VERY_POOR" in doc
    assert "Edge or Full-contig BGC in POOR/VERY_POOR assembly | 0" in full_run
    assert "In POOR/VERY_POOR assemblies the Edge/FC score effect is 0" in monolith
    assert "POOR/VERY_POOR | 0" in execution


def test_deliverable_contract_all_bgc_visibility():
    contract = text("docs/DELIVERABLE_CONTRACT.md")
    assert "POOR/VERY_POOR equal-visibility rule" in contract
    assert "all detected BGCs must remain visible" in contract
    assert "minimum candidate card" in contract
