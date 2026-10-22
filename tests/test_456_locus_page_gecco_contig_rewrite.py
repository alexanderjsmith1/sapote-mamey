"""tools/locus_reading_pages.py: a GECCO cluster is matched to the page's contigs by the same rule as the gene table.

GECCO rewrites the coverage part of a SPAdes contig name (cov_9.012345 becomes cov_9.12345). An exact-name join drops
those clusters, and the page then says "no cluster for these contigs is recorded" although the table holds one.
Exact names still win; the NODE_n_length_L fallback is used only when it names one ledger contig. An alias that names
two ledger contigs is an identity hold only when the cluster overlaps the page's own region; any other such cluster is
skipped with a logged warning. GECCO rows are resolved while the strain's pages are planned, before any of its pages is
written. Synthetic data only (the AS-900 fixture of test_449_locus_reading_pages).
"""
import csv

import pytest

from tests.test_449_locus_reading_pages import (C1, C2, C5, C5_REWRITTEN, C9, S, STEM1, STEM2, _argv, _gene,  # noqa: F401
                                                _write_tsv, fx, lrp)

REGION1 = (C1, 5000, 8900)   # BGC001: g5-g8 on NODE_1


def _gecco(d, rows):
    _write_tsv(d / "gecco.tsv", [dict(strain=S, average_p="0.91", relation="OUTSIDE_REGION", **r) for r in rows])


def test_gecco_cluster_on_a_rewritten_contig_name_is_on_the_page(fx, tmp_path):
    _gecco(fx, [{"contig_full": C5_REWRITTEN, "type": "NRP", "start": "100", "end": "2900"}])
    lrp.main(_argv(fx, tmp_path / "out"))
    page = (tmp_path / "out" / S / f"{STEM1}.md").read_text()
    assert "- **GECCO:** NRP cluster on NODE_5 (8,000 bp, 9×), 100–2900" in page
    assert "no cluster for these contigs is recorded" not in page


def test_exact_names_still_match_and_contigs_off_the_page_stay_off(fx, tmp_path):
    _gecco(fx, [{"contig_full": C1, "type": "Polyketide", "start": "4000", "end": "9000"},
                {"contig_full": C9, "type": "Terpene", "start": "10", "end": "900"}])
    lrp.main(_argv(fx, tmp_path / "out"))
    page = (tmp_path / "out" / S / f"{STEM1}.md").read_text()
    assert "- **GECCO:** Polyketide cluster on NODE_1 (60,000 bp, 10×), 4000–9000" in page
    assert "Terpene" not in page   # NODE_9's gene is MISSING_NOT_FOUND, so NODE_9 is not on the page


def test_page_gecco_rows_carry_the_ledger_contig_name():
    rows = [{"strain": S, "contig_full": C5_REWRITTEN}, {"strain": S, "contig_full": C9},
            {"strain": "AS-9001", "contig_full": C5}]
    got = lrp.page_gecco(rows, S, [C1, C5], [C1, C5, C9], REGION1)
    assert [r["contig_full"] for r in got] == [C5]
    assert rows[0]["contig_full"] == C5_REWRITTEN   # the input table is not changed


def test_an_ambiguous_alias_overlapping_the_region_is_an_identity_hold():
    twins = ["NODE_3_length_100_cov_1.05", "NODE_3_length_100_cov_2.0"]
    row = {"strain": S, "contig_full": "NODE_3_length_100_cov_1.5", "start": "10", "end": "50"}
    with pytest.raises(ValueError, match="LOCUS_PAGE_CONTIG_IDENTITY_HOLD"):
        lrp.page_gecco([row], S, twins[:1], twins, (twins[0], 1, 90))


@pytest.mark.parametrize("order,region", [
    ([C1], REGION1),                                                     # neither twin is on the page
    (["NODE_3_length_100_cov_1.05"], ("NODE_3_length_100_cov_1.05", 60, 90)),   # on the core contig, outside the region
])
def test_an_ambiguous_alias_off_the_region_is_skipped_and_logged(monkeypatch, order, region):
    twins = ["NODE_3_length_100_cov_1.05", "NODE_3_length_100_cov_2.0"]
    logged = []
    monkeypatch.setattr(lrp._OUT, "warning", lambda msg, *a: logged.append(msg % a if a else msg))
    row = {"strain": S, "contig_full": "NODE_3_length_100_cov_1.5", "start": "10", "end": "50"}
    assert lrp.page_gecco([row], S, order, [C1] + twins, region) == []
    assert len(logged) == 1 and "NODE_3_length_100_cov_1.5" in logged[0] and "skipped" in logged[0]


def _add_ledger_contig(d, contig, n=1):
    path = d / "ledger" / f"{S}.tsv"
    with open(path, "a", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=lrp.LEDGER_COLUMNS, delimiter="\t", lineterminator="\n")   # test fixture input
        w.writerows(_gene(f"x{contig[5]}_{i}", contig, i) for i in range(1, n + 1))


def test_an_off_page_ambiguous_cluster_does_not_stop_the_build(fx, tmp_path):
    for twin in ("NODE_3_length_100_cov_1.05", "NODE_3_length_100_cov_2.0"):
        _add_ledger_contig(fx, twin)
    _gecco(fx, [{"contig_full": "NODE_3_length_100_cov_1.5", "type": "NRP", "start": "10", "end": "50"}])
    lrp.main(_argv(fx, tmp_path / "out"))
    assert (tmp_path / "out" / S / f"{STEM1}.md").exists() and (tmp_path / "out" / S / f"{STEM2}.md").exists()


def test_a_region_hold_fires_before_any_page_of_the_strain_is_written(fx, tmp_path):
    _add_ledger_contig(fx, "NODE_2_length_40000_cov_7.5")   # shares C2's NODE_2_length_40000 alias
    _gecco(fx, [{"contig_full": "NODE_2_length_40000_cov_9.9", "type": "Terpene", "start": "2100", "end": "3000"}])
    with pytest.raises(ValueError, match="LOCUS_PAGE_CONTIG_IDENTITY_HOLD"):
        lrp.main(_argv(fx, tmp_path / "out"))
    assert not list((tmp_path / "out").glob(f"{S}/*.md"))   # BGC001's page is not written before BGC002's hold
