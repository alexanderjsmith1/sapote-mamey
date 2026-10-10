"""Public browser entry-point and Sapote skill handoff contracts."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_has_browser_assistant_entrypoint():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    required = [
        "## Start in ChatGPT or Claude.ai",
        "https://github.com/alexanderjsmith1/sapote-mamey",
        "antiSMASH result ZIPs",
        "strain / full node-or-contig / region / BGC alias",
        "chat response alone is not a validated or sealed Mamey package",
    ]
    for phrase in required:
        assert phrase in text


def test_skill_uses_plain_workflow_heading_and_contextual_handoff_scope():
    text = (ROOT / "skills" / "sapote-mamey" / "SKILL.md").read_text(encoding="utf-8")
    assert "## The workflow — CDSW" not in text
    assert "## The workflow" in text
    assert "## Handoff scope" in text
    flat = " ".join(text.split())
    for phrase in (
        "eight concrete numbered next paths only for a major final delivery or explicit planning request",
        "when eight distinct useful options exist",
        "Routine statuses and small fixes stay concise with at most one useful next action",
        "Do not create extra work to fill a menu",
    ):
        assert phrase in flat
    assert "## Next paths at every substantive handoff" not in text


def test_skill_current_navigation_does_not_brand_features_as_v97338():
    text = (ROOT / "skills" / "sapote-mamey" / "SKILL.md").read_text(encoding="utf-8")
    assert "## Post-seal deliverables (v9.7.338)" not in text
    assert "compatibility utility, not a universal reply requirement" not in text
