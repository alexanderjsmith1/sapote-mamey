from pathlib import Path

from mamey.cohort_figures import CAPTIONS


def test_known_figure_producers_use_publication_raster_constant() -> None:
    root = Path(__file__).resolve().parents[1]
    paths = [
        root / "mamey" / "cohort_figures.py",
        root / "mamey" / "cohort_figures_extended.py",
        root / "mamey" / "bgc_figures.py",
        root / "tools" / "build_figures.py",
    ]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        assert "PUBLICATION_RASTER_DPI = 300" in text
        assert not any(token in text for token in (
            "dpi=110", "dpi=115", "dpi=140", "dpi=150", "dpi=160",
            '"savefig.dpi":150',
        ))


def test_f10_caption_discloses_raw_annotation_unit_and_claim_ceiling() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "mamey" / "cohort_figures.py").read_text(encoding="utf-8")
    caption = CAPTIONS["regulator_TF_heatmap"]
    required = (
        "upstream antiSMASH GBK aSDomain/PFAM_domain annotations",
        "deep_data.domain_hits occurrence assigned to a BGC overlap",
        "deduplicates identical feature keys",
        "overlaps multiple BGC intervals",
        "does not independently call or validate regulator identity",
        "LysR_substrate denotes a substrate-binding-domain token",
        "does not establish a complete LysR regulator",
    )
    for phrase in required:
        assert phrase in caption
    assert "Transcription-factor / regulator family domain counts per strain" not in text


def test_f11_mixed_token_clustermap_fails_closed_pending_source_class_filter() -> None:
    root = Path(__file__).resolve().parents[1]
    text = (root / "mamey" / "cohort_figures.py").read_text(encoding="utf-8")
    assert "F11_MIXED_TOKEN_SOURCE_CLASS_UNBOUND" in text
    assert "REDESIGN_NOT_PUBLICATION_READY" in text
    assert '"feature_type", "accession", "annotation_source"' in text
    assert '"Top-40 Pfam domains' not in text
    assert '"The 40 most abundant Pfam domains' not in text
