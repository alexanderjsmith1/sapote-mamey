"""test_cohort_figures_cross_strain_import.py — H5 regression (v9.7.352).

`mamey/cohort_figures.py` calls `build_cross_strain_figures(...)` at its cohort-figure
entry, but the symbol lived in `cross_strain_figures.py` and was never imported. The call
sat inside a broad try/except that swallowed the resulting NameError and returned
{"status": "SKIPPED_ERROR"}, so auto cross-strain figures were silently never produced for
real >=2-strain batches. Existing tests only exercised the 0/1-strain early return, so the
bug escaped coverage. This pins the import binding.
"""
import mamey.cohort_figures as cohort_figures
from mamey.cross_strain_figures import build_cross_strain_figures as canonical


def test_cross_strain_builder_is_bound_in_cohort_module():
    # The exact symbol the cohort-figure entry calls must be importable in this namespace.
    assert hasattr(cohort_figures, "build_cross_strain_figures"), (
        "cohort_figures.build_cross_strain_figures is unbound — the missing import "
        "regressed (H5): >=2-strain cohort figures would silently SKIP with a NameError."
    )


def test_bound_symbol_is_the_canonical_one():
    assert cohort_figures.build_cross_strain_figures is canonical


def test_cohort_builder_labels_render_failure_as_error(tmp_path, monkeypatch):
    """An attempted cohort render that cannot write output is not an expected skip."""
    run_dir = tmp_path / "run"
    results = []
    for strain_id in ("AS-XXX", "AS-YYY"):
        package = run_dir / strain_id / "package"
        package.mkdir(parents=True)
        (package / "bgc_data.json").write_text('{"bgcs": []}', encoding="utf-8")
        results.append({"strain_id": strain_id, "package_zip": str(package.parent / "sealed.zip")})
    monkeypatch.setattr(
        cohort_figures, "build_cross_strain_figures",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("output unavailable")),
    )

    result = cohort_figures.build_cohort_figures(results, run_dir)

    assert result["status"] == "ERRORED"
    assert "output unavailable" in result["reason"]


def test_unreadable_boundary_evidence_is_marked_uncomputed(tmp_path):
    """Corrupt BGC boundary evidence must not become a three-zero cohort row."""
    package = tmp_path / "package"
    package.mkdir()
    (package / "bgc_data.json").write_text("not json", encoding="utf-8")

    row, _ranked = cohort_figures._strain_summary_row("AS-XXX", str(package), {})

    assert row["boundary_counts_status"].startswith("UNCOMPUTED:")
    assert row["interior_bgcs"] == ""
    assert row["edge_bgcs"] == ""
    assert row["full_contig_bgcs"] == ""


def test_valid_boundary_evidence_remains_computable(tmp_path):
    """Negative control: valid boundary records retain their measured counts."""
    package = tmp_path / "package"
    package.mkdir()
    (package / "bgc_data.json").write_text(
        '{"bgcs": [{"edge_status": "interior"}, {"edge_status": "edge"}, {"edge_status": "full"}]}',
        encoding="utf-8",
    )

    row, _ranked = cohort_figures._strain_summary_row("AS-XXX", str(package), {})

    assert row["boundary_counts_status"] == "COMPUTED"
    assert (row["interior_bgcs"], row["edge_bgcs"], row["full_contig_bgcs"]) == (1, 1, 1)


def test_cross_strain_boundary_plot_requires_computable_rows():
    """Consumer control: only fully computed boundary rows may reach the stacked plot."""
    from mamey.cross_strain_figures import _has_computable_boundary_counts

    valid = [{"interior_bgcs": 1, "edge_bgcs": 2, "full_contig_bgcs": 3,
              "boundary_counts_status": "COMPUTED"}]
    uncomputed = [{"interior_bgcs": "", "edge_bgcs": "", "full_contig_bgcs": "",
                   "boundary_counts_status": "UNCOMPUTED: JSONDecodeError"}]

    assert _has_computable_boundary_counts(valid) is True
    assert _has_computable_boundary_counts(uncomputed) is False


def test_corrupt_bridge_csv_does_not_become_empty_evidence(tmp_path):
    """A decoding failure is not equivalent to a valid header-only evidence table."""
    path = tmp_path / "ranked.csv"
    path.write_bytes(b"\xff\xfe\x00")

    import pytest
    with pytest.raises(UnicodeDecodeError):
        cohort_figures._read_csv(path)


def test_header_only_bridge_csv_remains_valid_empty_table(tmp_path):
    """Negative control: a readable header-only table remains an honest empty result."""
    path = tmp_path / "ranked.csv"
    path.write_text("rggmci_score,rggmci_confidence\n", encoding="utf-8")
    assert cohort_figures._read_csv(path) == []


def test_invalid_nonempty_numeric_cell_does_not_become_zero():
    """Malformed evidence must fail; declared missingness retains the supplied default."""
    import pytest
    from mamey import cross_strain_figures

    with pytest.raises(ValueError):
        cohort_figures._num("not-a-number")
    with pytest.raises(ValueError):
        cross_strain_figures._num("not-a-number")
    assert cohort_figures._num("", 7.0) == 7.0
    assert cross_strain_figures._num(None, 8.0) == 8.0
    assert cohort_figures._num("NA", 9.0) == 9.0


def test_missing_ripp_inventory_is_not_reported_as_zero(tmp_path):
    import pytest

    with pytest.raises(FileNotFoundError, match="RiPP product count requires"):
        cohort_figures._ripp_product_count(tmp_path)


def test_valid_ripp_inventory_preserves_zero_and_positive_counts(tmp_path):
    inventory = tmp_path / "AS-XXX_2_inventory.csv"
    inventory.write_text("Products\nNRPS\nterpene\n", encoding="utf-8")
    assert cohort_figures._ripp_product_count(tmp_path) == 0
    inventory.write_text("Products\nNRPS\nlanthipeptide\n", encoding="utf-8")
    assert cohort_figures._ripp_product_count(tmp_path) == 1


def test_domain_architecture_parser_rejects_malformed_evidence():
    import pytest

    with pytest.raises(ValueError, match="domain architecture"):
        cohort_figures._domain_counts_from_architecture({"architecture": "not a mapping"})


def test_domain_architecture_parser_preserves_valid_counts():
    record = {"architecture": "{'domain_counts': {'PKS_KR': 2, 'PKS_DH': 1}}"}
    assert cohort_figures._domain_counts_from_architecture(record) == {"PKS_KR": 2, "PKS_DH": 1}
