"""Headerless NCBI Hit Table rows parse correctly whatever commas the query title holds.

A one-comma title gives 13 fields, the same count as a 12-field row with % positives, so the old
count-based split misread it. So did a comma title with % positives.
"""
from mamey.blastp_followup import parse_hit_table_csv

M10 = "45.2,310,160,4,1,300,12,318,1e-50,180"


def _parse(tmp_path, line):
    f = tmp_path / "hits.csv"
    f.write_text(line + "\n")
    return parse_hit_table_csv(f)[0]


def test_plain_row(tmp_path):
    r = _parse(tmp_path, f"ctg1_5 Type: T1PKS,WP_000001.1,{M10}")
    assert (r.query_id, r.subject_id, r.pct_identity, r.pct_positive) == ("ctg1_5 Type: T1PKS", "WP_000001.1", 45.2, None)


def test_plain_row_with_positives(tmp_path):
    r = _parse(tmp_path, f"ctg1_5,WP_000001.1,{M10},61.0")
    assert (r.query_id, r.subject_id, r.pct_positive) == ("ctg1_5", "WP_000001.1", 61.0)


def test_one_comma_title_without_positives(tmp_path):
    r = _parse(tmp_path, f"ctg1_5 Streptomyces sp., complete_genome | Type: T1PKS,WP_000001.1,{M10}")
    assert r.query_id == "ctg1_5 Streptomyces sp., complete_genome | Type: T1PKS"
    assert (r.subject_id, r.pct_identity, r.bitscore, r.pct_positive) == ("WP_000001.1", 45.2, 180.0, None)


def test_comma_title_with_positives(tmp_path):
    r = _parse(tmp_path, f"ctg1_5 a, b, c,WP_000001.1,{M10},61.0")
    assert (r.query_id, r.subject_id, r.pct_identity, r.pct_positive) == ("ctg1_5 a, b, c", "WP_000001.1", 45.2, 61.0)


def test_two_comma_title_without_positives(tmp_path):
    r = _parse(tmp_path, f"ctg1_5 a, b, c,WP_000001.1,{M10}")
    assert (r.query_id, r.subject_id, r.pct_identity, r.pct_positive) == ("ctg1_5 a, b, c", "WP_000001.1", 45.2, None)
