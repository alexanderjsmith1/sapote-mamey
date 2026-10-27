"""Report cards attach to each BGC only its own modules, even when one node holds two regions.

Before: modules were matched by the locus-tag prefix ctgN_, which names the contig, so both regions on
NODE_5 listed both regions' modules.
"""
import csv

from mamey.report_card import render_report_cards

S = "AS-9001"
CONTIG = "NODE_5_length_90000_cov_20.0"


def _csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def _package(tmp_path, with_gene_table=True):
    pkg = tmp_path / "package"; pkg.mkdir()
    _csv(pkg / f"{S}_4_triage_board.csv", [
        {"BGC_ID": "BGC001", "Contig": CONTIG, "antiSMASH_Region": "region001", "Rank": "1", "Products": "NRPS"},
        {"BGC_ID": "BGC002", "Contig": CONTIG, "antiSMASH_Region": "region002", "Rank": "2", "Products": "NRPS"}])
    _csv(pkg / f"{S}_nrps_prediction.csv", [
        {"record_id": CONTIG, "locus_tag": "ctg5_10", "domain_class": "NRPS_A", "substrate": "ser", "confidence": "high"},
        {"record_id": CONTIG, "locus_tag": "ctg5_80", "domain_class": "NRPS_A", "substrate": "orn", "confidence": "high"}])
    if with_gene_table:
        _csv(pkg / f"{S}_gene_by_gene_all_bgcs.csv", [
            {"bgc_id": "BGC001", "locus_tag": "ctg5_10"}, {"bgc_id": "BGC002", "locus_tag": "ctg5_80"}])
    return pkg


def _card_text(md, bgc):
    return md.split(bgc, 1)[1].split("BGC00", 1)[0]


def test_each_region_lists_only_its_own_modules(tmp_path):
    md = render_report_cards(str(_package(tmp_path)))["markdown"]
    one, two = _card_text(md, "BGC001"), _card_text(md, "BGC002")
    assert "ser" in one and "orn" not in one
    assert "orn" in two and "ser" not in two


def test_without_a_gene_table_two_regions_on_one_node_share_nothing(tmp_path):
    md = render_report_cards(str(_package(tmp_path, with_gene_table=False)))["markdown"]
    assert "ser(" not in md and "orn(" not in md
