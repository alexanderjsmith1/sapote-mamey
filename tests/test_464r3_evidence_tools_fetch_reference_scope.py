"""fetch_reference_cluster records which CDS subset it retained, and never calls it a characterized cluster."""
import io
from tests.test_fetch_reference_cluster import _load, _make_db


def test_db_receipt_names_retained_subset(tmp_path):
    m = _load()
    db = tmp_path / "syn.db"; _make_db(db)
    prov = {}
    m.ref_from_db(str(db), "BGC0000877", "ref", provenance=prov)
    assert prov["retained_cds_scope"] == "CDS_ROWS_PRESENT_IN_SELECTED_DATABASE_RECORD"
    assert prov["cluster_completeness_state"] == "NOT_ASSESSED"
    assert prov["characterization_state"] == "NOT_ASSESSED"


def test_ncbi_receipt_counts_untranslated_cds(monkeypatch):
    m = _load()
    from Bio import SeqIO
    from Bio.Seq import Seq
    from Bio.SeqFeature import FeatureLocation, SeqFeature
    from Bio.SeqRecord import SeqRecord
    rec = SeqRecord(Seq("N" * 200), id="AA123456.1"); rec.annotations["molecule_type"] = "DNA"
    rec.features = [SeqFeature(FeatureLocation(0, 60, strand=1), type="CDS",
                               qualifiers={"translation": ["M" * 20]}),
                    SeqFeature(FeatureLocation(90, 150, strand=1), type="CDS", qualifiers={})]
    buf = io.StringIO(); SeqIO.write(rec, buf, "genbank")
    monkeypatch.setattr(m.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(buf.getvalue().encode()))
    prov = {}
    genes = m.ref_from_ncbi("AA123456.1", "ref", provenance=prov)
    assert len(genes) == 1
    assert prov["source_cds_feature_count"] == 2 and prov["untranslated_cds_dropped"] == 1
    assert prov["retained_cds_scope"] == "TRANSLATED_CDS_FEATURES_OF_FETCHED_RECORD"


def test_docstring_does_not_claim_characterized_genes():
    m = _load()
    assert "is the characterised cluster's genes" not in m.__doc__
