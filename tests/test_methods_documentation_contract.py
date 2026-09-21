"""Regression gate for the admitted, portable Methods documentation set."""
import re
from pathlib import Path


ROOT = Path(__file__).parent.parent
DOCS = {
    "template": ROOT / "docs/templates/MANUSCRIPT_METHODS_IMPLEMENTATION_TEMPLATE.md",
    "appendix": ROOT / "docs/reference/METHODS_TECHNICAL_APPENDIX.md",
    "source_map": ROOT / "docs/development/METHODS_IMPLEMENTATION_SOURCE_MAP.md",
    "checklist": ROOT / "docs/METHODS_REPORTING_CHECKLIST.md",
}


def test_methods_documentation_set_is_present_and_portable():
    forbidden = (
        "/Users/", "Claude_Alex_2026", "Codex Alex 2026", "/private/tmp/",
        "SESSION_TRANSCRIPT", "METHODS_STATE.json", "README_DELIVERABLES",
    )
    for name, path in DOCS.items():
        assert path.is_file(), f"missing {name}: {path.relative_to(ROOT)}"
        text = path.read_text(encoding="utf-8")
        assert not any(token in text for token in forbidden), (
            f"non-portable/task-packet token in {path.relative_to(ROOT)}")


def test_template_is_prospective_not_an_execution_claim():
    text = DOCS["template"].read_text(encoding="utf-8")
    assert "does not assert that any study was run" in text
    assert "Required substitutions" in text
    assert "[archived release, DOI, or commit]" in text


def test_checklist_states_universal_items_once():
    text = DOCS["checklist"].read_text(encoding="utf-8")
    assert text.count("Report exact bundle, engine, build or commit") == 1
    assert text.count("Display every individual BGC") == 1
    assert "## Universal requirements" in text
    assert "## Module-specific requirements" in text
    for section in ("RG-GMCI, FLBR, and EFLS", "Mode B and LLM assistance",
                    "Phylogeny and ANI/AAI", "Sealing, privacy, and validation"):
        assert f"### {section}" in text


def test_source_map_paths_and_tests_resolve():
    """Prevent implementation/test renames from silently staling the source map."""
    text = DOCS["source_map"].read_text(encoding="utf-8")
    rows = [line for line in text.splitlines() if re.match(r"^\| \d+ \|", line)]
    assert len(rows) == 14
    missing = []
    for row in rows:
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        for item in cells[2].strip("`").split("; "):
            rel = item.split("::", 1)[0]
            if not (ROOT / rel).exists():
                missing.append(rel)
        for item in cells[3].strip("`").split("; "):
            if not (ROOT / "tests" / item).is_file():
                missing.append(f"tests/{item}")
    assert not missing, "stale Methods source-map paths:\n" + "\n".join(missing)


def test_current_docs_index_links_the_methods_set():
    index = (ROOT / "CURRENT_DOCS_INDEX.md").read_text(encoding="utf-8")
    for path in DOCS.values():
        assert str(path.relative_to(ROOT)) in index

