import json
import pytest
from mamey.blastp_ingest import _manual_binding_guard


@pytest.mark.parametrize("query_len,defline_aa,rejected", [
    ("200", "", True), ("", "200", True), ("100", "200", True),
    ("200", "100", True), ("100", "100", False), ("", "", False),
])
def test_each_available_length_is_a_rejection_constraint(tmp_path, query_len, defline_aa, rejected):
    (tmp_path/"manifest.json").write_text(json.dumps({"strain_id":"fixture"}))
    (tmp_path/"fixture_gene_context.jsonl").write_text(json.dumps({
        "bgc_id":"fixture-region", "cds":[{"locus_tag":"gene1","aa_length":100}]})+"\n")
    source=tmp_path/"input.csv"; source.write_text("")
    row={"BGC_ID":"fixture-region", "query_locus":"gene=gene1|"+("aa="+defline_aa if defline_aa else ""),
         "query_len":query_len, "pct_identity":"90", "align_len":"90"}
    admitted,summary=_manual_binding_guard(tmp_path,"fixture",[row],source)
    assert len(admitted)==(0 if rejected else 1)
    assert summary["quarantined"]==int(rejected)
    if rejected:
        receipt=json.loads(__import__("pathlib").Path(summary["receipt"]).read_text())
        assert receipt["quarantined_by_reason"]["QUERY_CURRENT_AA_LENGTH_MISMATCH"]==1
