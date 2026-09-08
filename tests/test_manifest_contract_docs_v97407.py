from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def test_execution_prompt_names_emitted_manifest_fields():
    text = (ROOT / "prompts" / "MAMEY_CHATGPT_EXECUTION_PROMPT.md").read_text(encoding="utf-8")
    contract = text[text.index("## 6. Scan-states"):text.index("## 7. Checkpoint")]
    assert '"analysis_date": "ISO-8601"' in contract
    assert '"run_date": "ISO-8601"' not in contract
    assert "`assembly.quality` is an object" in contract


def test_module_docs_name_bgc_counts_as_assembly_tier_owner():
    for relative in (
        "docs/modules/DELIVERABLE_ReviewerAttack.md",
        "docs/modules/DELIVERABLE_WetLabMatrix.md",
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "manifest.json → bgc_counts.assembly_tier" in text
        assert "manifest.json → assembly.assembly_tier" not in text
