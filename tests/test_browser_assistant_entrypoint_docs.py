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


def test_skill_uses_plain_workflow_heading_and_eight_distinct_paths():
    text = (ROOT / "skills" / "sapote-mamey" / "SKILL.md").read_text(encoding="utf-8")
    assert "## The workflow — CDSW" not in text
    assert "## The workflow" in text
    assert "## Next paths at every substantive handoff" in text
    assert "exactly\neight numbered paths, 1 through 8" in text
    for item in (
        "continue the next batch",
        "deepen a named BGC",
        "compare or merge",
        "figure or visual",
        "wet-lab, metabolomics, or",
        "checksum-bound handoff",
        "patch, debug, or improve validation",
        "documentation, release material",
    ):
        assert item in text


def test_skill_current_navigation_does_not_brand_features_as_v97338():
    text = (ROOT / "skills" / "sapote-mamey" / "SKILL.md").read_text(encoding="utf-8")
    assert "## Post-seal deliverables (v9.7.338)" not in text
    assert "compatibility utility, not a universal reply requirement" not in text
