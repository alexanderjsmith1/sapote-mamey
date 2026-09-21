from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
GUIDE=ROOT/"docs/guides/DEEP_BGC_TO_THESIS_QUICKSTART.md"

def test_quickstart_links_and_contract_sections_exist():
    text=GUIDE.read_text(encoding="utf-8")
    for heading in ("Quick start","Exact identity","Evidence channels","Overmerge and gene-slice examples","Reading the deep report","Using the metabolomics and activity decision tree","Building the thesis handoff","Browser assistant workflow","Troubleshooting","Glossary"):
        assert f"## {heading}" in text
    for target in re.findall(r"\]\((\.\./[^)]+\.md)\)",text):
        assert (GUIDE.parent/target).resolve().is_file()

def test_quickstart_is_neutral_and_product_boundary_is_explicit():
    text=GUIDE.read_text(encoding="utf-8")
    assert not re.search(r"/(?:Users|home)/[^/\s]+", text)
    assert not re.search(r"\b(?:AS|AJS)-\d+\b", text)
    assert "user-supplied locus evidence" in text
    assert "not a Sapote-Mamey release" in text
    assert "SYNTHETIC-001 / contig_demo_0001_complete / region001 / BGC007" in text
