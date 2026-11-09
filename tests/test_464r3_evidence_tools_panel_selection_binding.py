"""The panel's contig-and-coordinate join reports ambiguous and unmatched selections, and the guide
does not call XML2 proof-grade."""
import csv
import json
from mamey.bgc_blastp_panel import panel_rows, write_panel
from mamey.models import BGCRecord, CDSFeature


def _bgc(bid, start, end):
    return BGCRecord(bgc_id=bid, contig="ctg1", region_number=int(bid[-3:]), start=start, end=end,
                     contig_length=20000, products=["NRPS"], node_id="ctg1", antismash_region="region001")


def _cds(start, end, locus, contig="ctg1"):
    return CDSFeature(contig, start, end, 1, locus, "PKS ketosynthase", "M" * 250, "",
                      {"sec_met_domain": ["PKS ketosynthase"]})


def test_repeated_locus_tag_is_held():
    rows = panel_rows([_bgc("BGC001", 1, 3000)], [_cds(100, 900, "dup"), _cds(5000, 5800, "dup", contig="ctg9")],
                      "EXAMPLE", genes_per_bgc=1)
    assert rows[0]["selection_binding_state"] == "HOLD_AMBIGUOUS_LOCUS_TAG"


def test_unique_join_is_labelled_unverified_not_proven():
    rows = panel_rows([_bgc("BGC001", 1, 3000)], [_cds(100, 900, "g1")], "EXAMPLE", genes_per_bgc=1)
    assert rows[0]["selection_binding_state"] == "UNIQUE_IN_PARSED_RECORDS_NOT_SEQUENCE_VERIFIED"


def test_summary_lists_unselected_bgcs_and_guide_is_not_proof_grade(tmp_path):
    write_panel(tmp_path, "EXAMPLE", [_bgc("BGC001", 1, 3000), _bgc("BGC002", 10000, 12000)],
                [_cds(100, 900, "g1")])
    summary = json.loads((tmp_path / "EXAMPLE_BGC_BLASTP_PANEL_summary.json").read_text())
    assert summary["bgcs_without_selection"] == ["BGC002"]
    assert summary["selection_binding_holds"] == 0
    manifest = list(csv.DictReader(open(tmp_path / "EXAMPLE_BGC_BLASTP_PANEL_selection_manifest.csv")))
    assert "selection_binding_state" in manifest[0]
    assert "proof-grade" not in (tmp_path / "EXAMPLE_BGC_BLASTP_PANEL_USER_GUIDE.md").read_text()
