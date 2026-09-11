from __future__ import annotations

from pathlib import Path


CURRENT_USER_DOCS = [
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    "docs/CITATION_COMPACT_MODE.md",
    "docs/HOW_TO_USE.md",
    "docs/GUIDE/01_User_Manual.md",
    "docs/GUIDE/02_Quick_Guide.md",
    "docs/GUIDE/03_Technical_Manual_Encyclopedia.html",
    "docs/DELIVERABLE_CONTRACT.md",
]


def _read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8", errors="ignore")


def test_current_user_docs_have_citation_compact_provenance_block():
    root = Path(__file__).resolve().parents[1]
    for rel in CURRENT_USER_DOCS:
        text = _read(root, rel)
        assert "Citation-Compact Provenance and Citation Status" in text, rel
        assert "10.1093/nar/gkaf334" in text, rel
        assert "10.1093/nar/gkae1115" in text, rel
        assert "PASS_STRUCTURE" in text, rel
        assert "operator_supplied" in text, rel
        assert "citation_needed" in text, rel
        assert "Literature_Search_WorkOrder.md/json" in text, rel
        assert "interpretation_scope" in text, rel


def test_current_user_docs_do_not_reintroduce_legacy_scope_field_name():
    root = Path(__file__).resolve().parents[1]
    for rel in CURRENT_USER_DOCS:
        assert "claim_scope" not in _read(root, rel), rel
