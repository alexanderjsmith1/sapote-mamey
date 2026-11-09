"""The literature dataset says how pubmed_ingest.py really builds the corpus: offline, from saved PDFs."""
from pathlib import Path

from mamey import external_data

ROOT = Path(__file__).resolve().parents[1]


def test_literature_dataset_names_pdf_source_not_eutilities():
    ds = external_data.DATASETS["literature"]
    assert "PDF" in ds.upstream
    assert "(NCBI E-utilities)" not in ds.upstream
    assert "Build the corpus locally from E-utilities" not in ds.licence


def test_ingest_helper_reads_pdfs_offline():
    helper = (ROOT / "mamey" / "data" / "literature" / "_corpus" / "pubmed_ingest.py").read_text()
    assert "PdfReader" in helper
    for token in ("eutils", "efetch", "esearch", "urllib.request", "requests"):
        assert token not in helper
