"""Keep the operator literature-corpus guide aligned to the shipped helper's CLI."""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "EXTERNAL_DATA.md"
HELPER = ROOT / "mamey" / "data" / "literature" / "_corpus" / "pubmed_ingest.py"


def test_literature_guide_uses_the_helper_positional_contract() -> None:
    doc = DOC.read_text(encoding="utf-8")
    helper = HELPER.read_text(encoding="utf-8")
    assert "Usage: python pubmed_ingest.py <pdf_dir> <out_dir>" in helper
    assert "pubmed_ingest.py --out" not in doc
    assert "/path/to/pubmed-search-result-pdfs" in doc
    assert '"$MAMEY_DATA_ROOT/literature"' in doc


def test_literature_guide_discloses_local_pdf_and_optional_reader_contract() -> None:
    doc = DOC.read_text(encoding="utf-8")
    helper = HELPER.read_text(encoding="utf-8")
    assert "local `*.pdf` files" in doc
    assert "python -m pip install pypdf" in doc
    assert "from pypdf import PdfReader" in helper
    assert "not a\n  network client" in doc
