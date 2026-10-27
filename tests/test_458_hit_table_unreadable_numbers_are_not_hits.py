"""A Hit Table row whose identity or bit score cannot be read is not turned into a 0.0 weak hit."""
from mamey.blastp_followup import parse_hit_table_csv


def test_unreadable_identity_or_bitscore_is_skipped(tmp_path):
    f = tmp_path / "hits.csv"
    f.write_text("ctg1_5,WP_1.1,NA,310,160,4,1,300,12,318,1e-50,180\n"
                 "ctg1_6,WP_2.1,45.0,310,160,4,1,300,12,318,1e-50,n/a\n"
                 "ctg1_7,WP_3.1,52.5,310,160,4,1,300,12,318,1e-50,190\n")
    recs = parse_hit_table_csv(f)
    assert [r.query_id for r in recs] == ["ctg1_7"]
    assert recs[0].pct_identity == 52.5
