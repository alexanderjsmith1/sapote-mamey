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
