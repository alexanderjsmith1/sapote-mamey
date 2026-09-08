from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def text(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def test_execution_slice_is_default_controller():
    for rel in ["SESSION_START_MANIFEST.md", "CHATGPT_START_HERE.md", "README.md"]:
        doc = text(rel)
        assert "CHATGPT_EXECUTION_SLICE_v97147.md" in doc
    session = text("SESSION_START_MANIFEST.md")
    assert "docs/SAPOTE_SLIM_JUDGMENT_KERNEL.md` (legacy only)" in session


def test_trigger_routing_names_handback_and_edge_constants():
    routing = text("docs/TRIGGER_ROUTING.md")
    required = [
        "CHATGPT_EXECUTION_SLICE_LOADED",
        "MAMEY_COMPLETE_HANDOFF_REQUIRED",
        "ANALYSIS_COMPLETE_DELIVERABLE_OFFER",
        "LOCUS_MAP_PRESENTATION_REQUIRED",
        "POOR_TIER_EDGE_EQUALITY",
        "INTERPRETIVE_FLOOR_CHECK",
        "OFFLINE_EVIDENCE_ALLOWED",
        "WISE_PKS_QUEUE_DETECTED",
    ]
    for token in required:
        assert token in routing
    assert "OFFLINE_EVIDENCE_ALLOWED` suppresses `WISE_PKS_QUEUE_DETECTED`" in routing


def test_post_mamey_complete_handback_surface_contract():
    required_outputs = [
        "OPEN_ME_FIRST.html",
        "manifest.json",
        "_8_strain_brief.pdf",
        "_8a…_8m_fig_*.png",
        "locus_maps/",
        "_5_workbook.xlsx",
        "checksums_sha256.txt",
        "issue_log.md",
    ]
    docs = [
        text("docs/CHATGPT_EXECUTION_SLICE_v97147.md"),
        text("SESSION_START_MANIFEST.md"),
        text("docs/TRIGGER_ROUTING.md"),
    ]
    for output in required_outputs:
        assert any(output in doc for doc in docs), output


def test_prompt_backed_deliverables_are_offered_after_complete():
    execution = text("docs/CHATGPT_EXECUTION_SLICE_v97147.md")
    contract = text("docs/DELIVERABLE_CONTRACT.md")
    for name in [
        "Layperson-Ranked BGC Guide",
        "Technical Full-Analysis Report",
        "Compound Detection and Isolation Bench Guide",
        "Fermentation Card",
        "Wet-Lab Decision Matrix",
        "Metabolomics Readiness",
        "Ecological Synthesis",
        "Reviewer Attack Simulation",
    ]:
        assert name in execution or name in contract


def test_modeb_extensions_require_evidence_ledger_and_decision_tree():
    execution = text("docs/CHATGPT_EXECUTION_SLICE_v97147.md")
    assert "§28 — Evidence provenance ledger" in execution
    assert "§30 — Experimental decision tree" in execution
    assert "§28 and §30 are required for every completed Mode B card" in execution
