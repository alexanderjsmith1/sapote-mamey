"""An explicitly supplied but unusable Mode B source is missing evidence."""

from mamey.modeb_template_emitter import (
    _body_40_bigscape, _body_44_prevalence, _body_46_reference,
    _body_47_host_matched,
)


def _facts(**sources):
    supplied = {"cohort_dir": None, "reference_dir": None,
                "strain_metadata": None, "bigscape_regions_dir": None}
    supplied.update(sources)
    return {"_sources": supplied, "strain_id": "SID001", "taxonomy": "Fixtureus sp.",
            "contig": "NODE_1_length_5000_cov_1", "region": "region001",
            "bgc_id": "BGC001", "products": "NRPS"}


def test_missing_cohort_root_is_not_zero_denominator(tmp_path):
    text = _body_44_prevalence(_facts(cohort_dir=str(tmp_path / "missing")))
    assert "SOURCE HOLD" in text and "--cohort-dir" in text
    assert "**Denominator:** 0" not in text


def test_empty_cohort_root_is_not_zero_denominator(tmp_path):
    text = _body_44_prevalence(_facts(cohort_dir=str(tmp_path)))
    assert "SOURCE HOLD" in text and "--cohort-dir" in text
    assert "**Denominator:** 0" not in text


def test_missing_reference_root_is_not_zero_references(tmp_path):
    text = _body_46_reference(_facts(reference_dir=str(tmp_path / "missing")))
    assert "SOURCE HOLD" in text and "--reference-dir" in text
    assert "*None found.*" not in text


def test_missing_bigscape_root_is_not_empty_directory(tmp_path):
    text = _body_40_bigscape(_facts(bigscape_regions_dir=str(tmp_path / "missing")))
    assert "SOURCE HOLD" in text and "--bigscape-regions-dir" in text
    assert "No region GBKs found" not in text


def test_missing_metadata_file_is_not_host_absence(tmp_path):
    text = _body_47_host_matched(_facts(strain_metadata=str(tmp_path / "missing.tsv")))
    assert "SOURCE HOLD" in text and "--strain-metadata" in text
    assert "Host unresolved" not in text
