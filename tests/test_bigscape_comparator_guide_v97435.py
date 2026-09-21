from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs" / "BIGSCAPE_COHORT_NETWORK_GUIDE.md"


def test_comparator_guide_has_required_undergraduate_workflows_and_live_tool_links():
    text = GUIDE.read_text(encoding="utf-8")
    required = (
        "How to read comparator badges and citations",
        "Whole-region and coherent-component metrics",
        "Batch enrichment without changing source reports",
        "Static gene-order and GCF figure",
        "Using a browser assistant",
        "Common mistakes",
        "Glossary",
    )
    assert all(heading in text for heading in required)
    for tool in (
        "bigscape_network_widget.py", "batch_mibig_comparator_context.py",
        "mibig_component_context.py", "bigscape_gene_domain_context.py",
    ):
        assert (ROOT / "deliverable_tools" / tool).is_file(), tool
        assert tool in text
    assert (ROOT / "docs" / "BIGSCAPE_CLASS_GLOSSARY.md").is_file()
    assert "docs/BIGSCAPE_COHORT_NETWORK_GUIDE.md" in (ROOT / "CURRENT_DOCS_INDEX.md").read_text(encoding="utf-8")


def test_comparator_guide_is_portable_and_version_neutral():
    text = GUIDE.read_text(encoding="utf-8")
    assert not re.search(r"/Users/[^/\s]+/", text)
    assert not re.search(r"\bAS-\d+\b", text)
    assert not re.search(r"\bv\d+\.\d+\.\d+\b", text)
    assert "DEMO-A / NODE_7_length_47000_cov_20.0 / region001 / BGC004" in text
