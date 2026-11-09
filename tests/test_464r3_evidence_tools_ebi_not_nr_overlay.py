"""EBI, UniProt and other non-nr sources never land in the package's nr overlay."""
import pytest
from mamey.blastp_ingest import BlastpHitTableError, _is_ncbi_nr_source, ingest_blastp


def test_source_classifier():
    assert _is_ncbi_nr_source("NCBI web-BLASTp")
    for source in ("EBI (uniprotkb_bacteria)", "NCBI ClusteredNR", "NCBI Swiss-Prot", "local", ""):
        assert not _is_ncbi_nr_source(source)


def test_ebi_source_with_package_is_refused_before_any_write(tmp_path):
    master = tmp_path / "master.xlsx"; master.write_bytes(b"not read")
    table = tmp_path / "hits.csv"; table.write_text("synthetic\n")
    pkg = tmp_path / "pkg"; pkg.mkdir()
    with pytest.raises(BlastpHitTableError, match="BLASTP_CHANNEL_UNSUPPORTED_FOR_PACKAGE_OVERLAY"):
        ingest_blastp(master, "EXAMPLE", table, package=pkg, source="EBI (uniprotkb_bacteria)")
    assert master.read_bytes() == b"not read"
    assert not (pkg / "blastp_online").exists()
