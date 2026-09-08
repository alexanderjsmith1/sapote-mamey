import pathlib
ROOT = pathlib.Path(__file__).resolve().parent.parent

def test_glossary_declares_canonical():
    g = (ROOT / "docs" / "GLOSSARY.md").read_text(encoding="utf-8")
    assert "CANONICAL" in g and "addenda" in g.lower()

def test_addenda_declare_scope():
    for p in (ROOT / "docs" / "troubleshooting" / "CELL_STATUS_CODE_GLOSSARY.md",):
        if p.exists():
            assert "ADDENDUM (scoped)" in p.read_text(encoding="utf-8")
