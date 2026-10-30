import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent

def test_glossary_declares_canonical():
    g = (ROOT / "docs" / "GLOSSARY.md").read_text(encoding="utf-8")
    assert g.startswith("<!-- CANONICAL GLOSSARY -->")
    assert "This is the canonical glossary." in g
    assert "[cell-status glossary](troubleshooting/CELL_STATUS_CODE_GLOSSARY.md)" in g

def test_cell_status_reference_declares_scope_and_links_to_canonical_glossary():
    p = ROOT / "docs" / "troubleshooting" / "CELL_STATUS_CODE_GLOSSARY.md"
    assert p.is_file()
    text = p.read_text(encoding="utf-8")
    assert "mamey/cell_provenance.py" in text
    assert "[canonical glossary](../GLOSSARY.md)" in text
    assert (p.parent / "../GLOSSARY.md").resolve() == ROOT / "docs" / "GLOSSARY.md"
