"""9.7.465: max4_tree_figure --fill-blank finds a row by the bracketed accession in its label.

Since 9.7.460 reference labels carry the accession in brackets ("Name [GCF_...]"). --fill-blank still looked
for "(GCF_...)" in the label, so a table row whose tip is not the accession was never filled, and the change log
did not say the fill row went unused. Pass-after: "[acc]" and the older "(acc)" both match, and an accession
that finds no row is logged as unmatched and listed in the receipt summary. Synthetic files only.
"""
import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("max4_tree_figure_465", ROOT / "tools" / "max4_tree_figure.py")
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def _run(tmp_path, table_rows, fill_rows):
    table = tmp_path / "table.tsv"
    table.write_text("tip\trole\tlabel_concise\tsource_display\tgeography_display\n"
                     + "".join("\t".join(r) + "\n" for r in table_rows))
    fill = tmp_path / "fill.tsv"
    fill.write_text("accession\tfield\tvalue\tevidence\n" + "".join("\t".join(r) + "\n" for r in fill_rows))
    out = tmp_path / "out.tsv"
    assert mod.main(["metadata", "--table", str(table), "--fill-blank", str(fill), "--out", str(out)]) == 0
    rows = list(mod.csv.DictReader(out.open(), delimiter="\t"))
    changes = list(mod.csv.DictReader((tmp_path / "out_changes.tsv").open(), delimiter="\t"))
    receipt = json.loads((tmp_path / "out_receipt.json").read_text())
    return rows, changes, receipt


def test_bracketed_and_older_parenthesised_accessions_are_both_filled(tmp_path):
    rows, changes, _ = _run(tmp_path,
                            [("Synthetica_alpha_ref", "REFERENCE", "Synthetica alpha [GCF_000000001.1]", "", "Panama"),
                             ("Synthetica_beta_ref", "REFERENCE", "Synthetica beta (GCF_000000002.1)", "", "Panama")],
                            [("GCF_000000001.1", "source_display", "soil", "BioSample attribute"),
                             ("GCF_000000002.1", "source_display", "soil", "BioSample attribute")])
    assert [r["source_display"] for r in rows] == ["soil", "soil"]
    assert sorted(c["tip"] for c in changes if c["kind"] == "filled") == ["Synthetica_alpha_ref", "Synthetica_beta_ref"]


def test_an_accession_that_finds_no_row_is_logged_and_listed(tmp_path):
    rows, changes, receipt = _run(tmp_path,
                                  [("Synthetica_alpha_ref", "REFERENCE", "Synthetica alpha [GCF_000000001.1]", "", "Panama")],
                                  [("GCF_000000009.1", "source_display", "soil", "BioSample attribute")])
    assert rows[0]["source_display"] == ""
    assert [(c["kind"], c["tip"]) for c in changes] == [("unmatched", "GCF_000000009.1")]
    assert receipt["summary"]["fill_blank_unmatched"] == ["GCF_000000009.1"]
