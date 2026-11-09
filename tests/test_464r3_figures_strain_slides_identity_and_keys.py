"""Strain slides: a blank BLASTp identity is not 0%, and repeated join keys are refused."""
import csv
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import strain_slides as ss  # noqa: E402


def _csv(path, rows):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def test_blank_identity_is_labeled_not_zero():
    hit = {"org": "Example bacterium", "pid": "", "acc": "WP_000001.1"}
    assert ss.blastp_cell(hit) == "Example bacterium identity not recorded"
    assert "0%" not in ss.blastp_cell(hit)
    assert ss.identity_text({"pid": "NA"}) == "identity not recorded"
    assert ss.identity_text({"pid": "87.4"}) == "87%"


def test_stored_hits_with_blank_identity_stay_unlabeled_zero(tmp_path):
    _csv(tmp_path / "hits.csv", [
        {"gene": "ctg1_1", "hit_rank": "1", "subject_acc": "WP_1", "subject_organism": "Org A", "pct_identity": ""},
    ])
    hits = ss.blastp_hits([str(tmp_path / "*.csv")])
    assert ss.blastp_cell(hits["ctg1_1"]) == "Org A identity not recorded"


def test_conflicting_rank_one_hits_for_one_locus_tag_are_held(tmp_path):
    _csv(tmp_path / "a.csv", [
        {"gene": "ctg1_1", "hit_rank": "1", "subject_acc": "WP_1", "subject_organism": "Org A", "pct_identity": "90"},
    ])
    _csv(tmp_path / "b.csv", [
        {"gene": "ctg1_1", "hit_rank": "1", "subject_acc": "WP_2", "subject_organism": "Org B", "pct_identity": "40"},
    ])
    hits = ss.blastp_hits([str(tmp_path / "*.csv")])
    assert hits["ctg1_1"].get("conflict") is True
    assert ss.blastp_cell(hits["ctg1_1"]) == "conflicting stored hits"


def test_same_hit_in_two_files_is_not_a_conflict(tmp_path):
    for name in ("a.csv", "b.csv"):
        _csv(tmp_path / name, [
            {"gene": "ctg1_1", "hit_rank": "1", "subject_acc": "WP_1", "subject_organism": "Org A", "pct_identity": "90"},
        ])
    hits = ss.blastp_hits([str(tmp_path / "*.csv")])
    assert not hits["ctg1_1"].get("conflict")
    assert ss.blastp_cell(hits["ctg1_1"]) == "Org A 90%"


def test_duplicate_inventory_alias_is_refused():
    rows = [{"BGC_ID": "BGC001", "Contig": "C1"}, {"BGC_ID": "BGC001", "Contig": "C2"}]
    with pytest.raises(ss.SourceIdentityError, match="BGC001"):
        ss.keyed(rows, "BGC_ID", "inventory")


def test_build_command_refuses_a_duplicate_inventory_alias(tmp_path):
    pytest.importorskip("pptx")
    pkg = tmp_path / "package"
    pkg.mkdir()
    inv = [
        {"BGC_ID": "BGC001", "Contig": "C1", "antiSMASH_Region": "region001", "Start": "1", "End": "900", "Products": "NRPS"},
        {"BGC_ID": "BGC001", "Contig": "C2", "antiSMASH_Region": "region002", "Start": "1", "End": "900", "Products": "PKS"},
    ]
    _csv(pkg / "EX_2_inventory.csv", inv)
    _csv(pkg / "EX_gene_by_gene_all_bgcs.csv", [{"bgc_id": "BGC001", "locus_tag": "g1"}])
    sources = tmp_path / "sources.json"
    sources.write_text('{"strain": "EX", "package": "package"}')
    out = tmp_path / "decks"
    assert ss.main(["build", "--sources", str(sources), "--out", str(out)]) == 2
    assert not out.exists() or not any(out.iterdir())
