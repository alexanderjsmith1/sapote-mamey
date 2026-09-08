"""v9.7.245 — the nr overlay was invisible to the BGC guide.

`ingest-blastp --package` writes `blastp_online/<BGC>_online_blastp.csv` whose gene column is
`locus_tag`. `bgc_guide._load_blastp_store` skipped any row without a `query_gene` column, so the guide
could not see the nr evidence the pipeline had just spent `.239` creating and `.241` un-truncating.

Independently reproduced here after the AS-421 Mode B session reported it as P10.
"""
import csv, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from mamey.bgc_guide import _load_blastp_store

OVERLAY_COLS = ["locus_tag", "aa_length", "antismash_domains", "blastp_top_def", "blastp_accession",
                "blastp_organism", "pct_identity", "query_coverage", "evalue", "bitscore", "agreement"]


def _write(path, cols, row):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerow(row)


def test_nr_overlay_rows_are_visible_to_the_guide(tmp_path):
    _write(tmp_path / "BGC018_online_blastp.csv", OVERLAY_COLS,
           {"locus_tag": "ctg2_439", "pct_identity": "92.75", "bitscore": "900",
            "blastp_top_def": "lanthipeptide dehydratase", "blastp_organism": "S. saharense"})
    store = _load_blastp_store(tmp_path)
    assert "ctg2_439" in store, "the overlay's locus_tag column was being skipped entirely"


def test_legacy_query_gene_column_still_works_and_wins_a_tie(tmp_path):
    _write(tmp_path / "legacy.csv", ["query_gene", "locus_tag", "pct_identity", "bitscore"],
           {"query_gene": "ctg1_5", "locus_tag": "IGNORED", "pct_identity": "80", "bitscore": "500"})
    store = _load_blastp_store(tmp_path)
    assert "ctg1_5" in store and "ignored" not in store


def test_rows_with_neither_column_are_still_skipped(tmp_path):
    _write(tmp_path / "junk.csv", ["something_else"], {"something_else": "x"})
    assert _load_blastp_store(tmp_path) == {}


def test_missing_store_dir_is_graceful(tmp_path):
    assert _load_blastp_store(tmp_path / "nope") == {}
