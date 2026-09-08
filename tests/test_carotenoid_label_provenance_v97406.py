"""A13: raw and gene-backed carotenoid labels remain independently selectable."""
from types import SimpleNamespace

from mamey.cohort_class_heatmap import build_class_matrix
from mamey.master_workbook import _b2_product_class_rows
from mamey.models import BGCRecord


def _run(*, products, domains=(), pigment_hits=()):
    bgc = BGCRecord("BGC001", "NODE_1_length_50000_cov_20.0", 1, 100, 1000, 50000,
                    products=list(products), antismash_region="region001")
    scans = SimpleNamespace(
        domain_architecture={"per_bgc": {"BGC001": {"domains": [
            {"domain": d} for d in domains]}}},
        primary_metabolism={"hits": {"pigment": list(pigment_hits)}},
    )
    return SimpleNamespace(context=SimpleNamespace(strain_id="SYNTHETIC-STRAIN"),
                           bgcs=[bgc], source_scans=scans)


def test_raw_carotenoid_does_not_enter_gene_backed_view_without_core_marker():
    raw, gene = _b2_product_class_rows(_run(products=["carotenoid"]), "OK")
    assert raw["label_provenance"] == "RAW_ANTISMASH" and raw["carotenoid"] == 1
    assert gene["label_provenance"] == "GENE_BACKED" and gene["carotenoid"] == 0


def test_lycopene_cyclase_domain_backs_gene_view_without_rewriting_raw_label():
    raw, gene = _b2_product_class_rows(
        _run(products=["terpene"], domains=["Lycopene_cycl"]), "OK")
    assert raw["terpene"] == 1 and raw["carotenoid"] == 0
    assert gene["terpene"] == 1 and gene["carotenoid"] == 1


def test_phytoene_synthase_product_is_bound_by_contig_and_coordinates():
    hit = {"contig": "NODE_1_length_50000_cov_20.0", "start": 200, "end": 400,
           "product": "phytoene synthase"}
    _, gene = _b2_product_class_rows(_run(products=["terpene"], pigment_hits=[hit]), "OK")
    assert gene["carotenoid"] == 1


def test_heatmap_selects_one_provenance_view_without_duplicate_strains():
    rows = [
        {"strain": "SYNTHETIC-STRAIN", "label_provenance": "RAW_ANTISMASH",
         "terpene": 1, "carotenoid": 0},
        {"strain": "SYNTHETIC-STRAIN", "label_provenance": "GENE_BACKED",
         "terpene": 1, "carotenoid": 1},
    ]
    strains, classes, matrix = build_class_matrix(rows, label_provenance="GENE_BACKED")
    assert strains == ["SYNTHETIC-STRAIN"]
    assert matrix[0][classes.index("carotenoid")] == 1
