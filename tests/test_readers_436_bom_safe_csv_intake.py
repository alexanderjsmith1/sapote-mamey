"""Operator-supplied CSV/TSV readers must tolerate a UTF-8 BOM.

Excel writes CSV as utf-8-sig, and so does the sealed Codex fraction-plate
package (`Codex_September_20_v1`): all four of its CSVs carry a BOM, checked
this pass. The bundle already knows this -- `mamey/phylo_evidence.py`,
`mamey/blastp_followup.py`, `mamey/activity_lead_report.py`,
`mamey/strain_modeb.py`, `mamey/literature_intake.py` and
`mamey/blastp_channel_triage.py` all read `encoding="utf-8-sig"`.

Six readers added or carried into `.435` do not, and the failure is silent
rather than loud: `DictReader` keys the first column `'\\ufeffname'`, so
`row.get("name")` returns None instead of raising. Two of the six also specify
no encoding at all, making them locale-dependent as well.

`utf-8-sig` is byte-identical to `utf-8` on input without a BOM, so this is
safe on every file that already works.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

BUNDLE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BUNDLE))
sys.path.insert(0, str(BUNDLE / "tools"))

BODY = "locus_tag,order,product\ngene_001,1,polyketide synthase\n"
TSV_BODY = "gene_id\tvalue\ngene_001\t7\n"


def _readers():
    from tools.clear_match_finder import read_csv as cmf
    from tools.definitive_bgc_ranker import read_csv as ranker
    return {"clear_match_finder": cmf, "definitive_bgc_ranker": ranker}


@pytest.mark.parametrize("name", sorted(_readers()))
def test_tool_read_csv_is_bom_safe(tmp_path, name):
    reader = _readers()[name]
    path = tmp_path / f"{name}.csv"
    path.write_text(BODY, encoding="utf-8-sig")
    rows = reader(path)
    assert rows, "reader returned no rows"
    assert list(rows[0])[0] == "locus_tag", (
        f"{name}: first column is {list(rows[0])[0]!r}; a BOM is being read as "
        "part of the header name"
    )
    assert rows[0].get("locus_tag") == "gene_001", (
        f"{name}: row.get('locus_tag') is {rows[0].get('locus_tag')!r} -- the "
        "BOM makes this silently None rather than raising"
    )


@pytest.mark.parametrize("name", sorted(_readers()))
def test_tool_read_csv_unchanged_without_bom(tmp_path, name):
    """utf-8-sig must not alter behaviour on files that already work."""
    reader = _readers()[name]
    path = tmp_path / f"{name}_plain.csv"
    path.write_text(BODY, encoding="utf-8")
    rows = reader(path)
    assert rows[0]["locus_tag"] == "gene_001"
    assert rows[0]["product"] == "polyketide synthase"


def test_deep_report_evidence_tsv_is_bom_safe(tmp_path):
    """The evidence reader keys on identity columns; a BOM breaks the first one."""
    import json
    from mamey.deep_bgc_report import build_deep_report

    ident = {"strain": "SYNTHETIC-001", "full_node_or_contig": "contig_demo_0001_complete",
             "region": "region001", "bgc_alias": "BGC007"}
    record = dict(ident, genes=[{"gene_id": "gene_001", "start": 1, "end": 900, "strand": "+"}],
                  canonical_gene_count=1, boundary={"status": "COMPLETE", "note": ""})
    locus = tmp_path / "locus.json"
    locus.write_text(json.dumps(record))
    evidence = tmp_path / "evidence.tsv"
    # written the way Excel and the Codex package write tables
    with evidence.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, delimiter="\t",
                                fieldnames=list(ident) + ["gene_id"])
        writer.writeheader()
        writer.writerow(dict(ident, gene_id="gene_001"))
    receipt = build_deep_report(locus, tmp_path / "out", evidence)
    assert receipt["evidence_row_count"] == 1


def test_activity_tree_leads_tsv_is_bom_safe(tmp_path):
    import json
    from mamey.activity_decision_tree import build_activity_decision_trees

    ident = {"strain": "SYNTHETIC-001", "full_node_or_contig": "contig_demo_0001_complete",
             "region": "region001", "bgc_alias": "BGC007"}
    root = tmp_path / "reports"
    (root / "one").mkdir(parents=True)
    (root / "one/REPORT_RECEIPT.json").write_text(json.dumps({"identity": ident}))
    leads = tmp_path / "leads.tsv"
    row = dict(ident, report_receipt="one/REPORT_RECEIPT.json",
               hypothesis="pigment-family chemistry",
               claim_ceiling="Class-level hypothesis only")
    with leads.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    receipt = build_activity_decision_trees(leads, root, tmp_path / "out")
    assert receipt["lead_count"] == 1
