import json
import pytest
from mamey.blastp_ingest import _manual_binding_guard


@pytest.mark.parametrize("kind", ["malformed", "ambiguous", "multiple"])
def test_present_invalid_context_never_uses_legacy_fallback(tmp_path, kind):
    (tmp_path / "manifest.json").write_text(json.dumps({"strain_id": "fixture"}))
    source = tmp_path / "input.csv"
    source.write_text("")
    context = tmp_path / "fixture_gene_context.jsonl"
    if kind == "malformed":
        context.write_text("{invalid")
    else:
        record = {"bgc_id": "fixture-region", "cds": [
            {"locus_tag": "gene1", "aa_length": 100},
            {"locus_tag": "gene1", "aa_length": 200}]}
        context.write_text(json.dumps(record) + "\n")
        if kind == "multiple":
            (tmp_path / "second_gene_context.jsonl").write_text("")
    with pytest.raises(ValueError):
        _manual_binding_guard(tmp_path, "fixture", [{"BGC_ID": "fixture-region"}], source)
    assert not (tmp_path / "blastp_quarantine").exists()


def test_absent_legacy_context_remains_explicitly_unvalidated(tmp_path):
    source = tmp_path / "input.csv"
    source.write_text("")
    rows = [{"BGC_ID": "fixture-region"}]
    admitted, summary = _manual_binding_guard(tmp_path, "fixture", rows, source)
    assert admitted == rows
    assert summary["binding_validated"] is False


def test_strain_contradicting_the_manifest_is_refused_before_any_write(tmp_path):
    """The guard's own docstring promises this refusal; nothing pinned it.

    Every other test in this file passes ``strain="fixture"`` against a manifest whose
    ``strain_id`` is also ``"fixture"``, so ``man_strain != strain`` is never reached and the
    ValueError they assert on comes from the gene-context branch instead. Measured with the
    mutation-probe: replacing the mismatch condition with ``if False:`` left this whole file
    green while a ``--strain`` contradicting the sealed manifest was admitted.

    That matters because the rows this function admits are written into
    ``<package>/blastp_online/``, which ``authored_verify`` and ``genome_explore`` trust for
    conservation_median_id and NOVELTY_CONTRADICTION. A wrong-strain ingest is a provenance
    error in a sealed package, not a cosmetic one.
    """
    (tmp_path / "manifest.json").write_text(json.dumps({"strain_id": "AS-001"}))
    source = tmp_path / "input.csv"
    source.write_text("")

    with pytest.raises(ValueError) as excinfo:
        _manual_binding_guard(tmp_path, "AS-999", [{"BGC_ID": "fixture-region"}], source)

    msg = str(excinfo.value)
    assert "AS-999" in msg and "AS-001" in msg, (
        f"the refusal must name both the supplied strain and the manifest's: {msg}")
    # nothing may be written on the refusal path
    assert not (tmp_path / "blastp_online").exists()
    assert not (tmp_path / "blastp_quarantine").exists()


def test_strain_matching_the_manifest_is_not_refused(tmp_path):
    """Guard against an over-eager refusal: an agreeing strain must still proceed."""
    (tmp_path / "manifest.json").write_text(json.dumps({"strain_id": "AS-001"}))
    source = tmp_path / "input.csv"
    source.write_text("")
    admitted, summary = _manual_binding_guard(
        tmp_path, "AS-001", [{"BGC_ID": "fixture-region"}], source)
    assert isinstance(admitted, list)
