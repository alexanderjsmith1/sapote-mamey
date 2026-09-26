"""Invalid ClusterBlast percent identities must not become numeric evidence."""

from mamey.modeb_template_emitter import _body_25_neighbourhood, _pct_or_none


def test_percent_identity_accepts_only_finite_range():
    assert _pct_or_none("0") == 0
    assert _pct_or_none("87.5") == 87.5
    assert _pct_or_none("100") == 100
    for value in (None, "", "n/a", "nan", "NaN", "inf", "-inf", "-1", "101", []):
        assert _pct_or_none(value) is None


def test_invalid_csv_percent_identity_does_not_render_as_median(tmp_path):
    # Generic complete fixture identity: S1 / NODE_1_length_10000_cov_30 /
    # region001 / S1_BGC001.
    (tmp_path / "S1_4A2_ClusterBlast_per_gene.csv").write_text(
        "bgc_id,reference,reference_source,query_gene,pct_identity\n"
        "S1_BGC001,ref1,generic,g1,nan\n"
        "S1_BGC001,ref1,generic,g2,inf\n"
        "S1_BGC001,ref1,generic,g3,101\n"
        "S1_BGC001,ref1,generic,g4,87\n"
        "S1_BGC001,ref2,generic,g5,nan\n",
        encoding="utf-8",
    )
    facts = {
        "_pkg": str(tmp_path),
        "strain_id": "S1",
        "contig": "NODE_1_length_10000_cov_30",
        "region": "region001",
        "bgc_id": "S1_BGC001",
        "_triage_rows": [],
        "gene_rows": [{"id": f"g{i}"} for i in range(1, 6)],
    }
    text = _body_25_neighbourhood(facts)
    assert "| ref1 | generic | 4 of 5 | 87 |" in text
    assert "| ref2 | generic | 1 of 5 | — |" in text
    assert "| nan |" not in text
    assert "| inf |" not in text
