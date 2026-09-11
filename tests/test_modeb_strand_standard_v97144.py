import pytest
pd = pytest.importorskip('pandas')
from mamey.mode_b.schema import normalize_modeb_gene_table, validate_modeb_gene_table

def _row(strand):
    return {"node":"NODE_1","locus":"ctg1_1","strand":strand,"query_length":100,"top_hit_accession":"x","top_hit_title":"x","top_hit_species":"x","percent_identity":90,"percent_similarity":95,"query_coverage_pct":100,"gene_function_call":"core","modeb_role":"core"}

def test_strand_normalizes_numeric_to_plus_minus():
    df = normalize_modeb_gene_table(pd.DataFrame([_row(1), _row(-1)]))
    assert list(df['strand']) == ['+', '-']
    validate_modeb_gene_table(df)

def test_missing_strand_becomes_explicit_unknown():
    r=_row('+'); r.pop('strand')
    df=normalize_modeb_gene_table(pd.DataFrame([r]))
    assert df['strand'].iloc[0] == 'UNKNOWN_EXPLICIT'
    validate_modeb_gene_table(df)

def test_arrow_strand_fails_validation():
    df = pd.DataFrame([_row('→')])
    df['protein_length_aa'] = 100
    with pytest.raises(AssertionError):
        validate_modeb_gene_table(df)
