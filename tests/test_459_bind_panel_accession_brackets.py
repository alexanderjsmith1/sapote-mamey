"""bind_panel_metadata puts the reference accession in brackets (house rules 6 and 11).

It wrote "(GCF_...)". The owner ruled that the tool follows rule 6. This test runs the tool on a
one-reference panel and reads the label from the written figure_metadata.tsv.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import bind_panel_metadata as bpm  # noqa: E402


def test_written_reference_label_has_bracketed_accession(tmp_path):
    panel = tmp_path / "PANEL_A"
    panel.mkdir()
    (panel / "figure_metadata.tsv").write_text(
        "tip\tidentifier\trole\tlabel_concise\tlabel_experiment\treference_class\n"
        "GCF_000000001.1\tGCF_000000001.1\tREFERENCE\told\told\tReference\n"
        "OUT_1\tGCF_000000009.1\tOUTGROUP\told\told\tReference\n", encoding="utf-8")
    records = tmp_path / "assembly_records.tsv"
    records.write_text(
        "accession\torganism\tstrain\tfromtype\n"
        "GCF_000000001.1\tGenus alpha\tDSM 1\tassembly from type material\n"
        "GCF_000000009.1\tOuter beta\tK9\t\n", encoding="utf-8")
    out = tmp_path / "bound"
    assert bpm.main(["--panel-dir", str(panel), "--out-dir", str(out), "--assembly-records", str(records)]) == 0
    with open(out / "figure_metadata.tsv", encoding="utf-8", newline="") as fh:
        rows = {r["identifier"]: r for r in csv.DictReader(fh, delimiter="\t")}
    assert rows["GCF_000000001.1"]["label_concise"] == "Genus alpha DSM 1 [Type] [GCF_000000001.1]"
    assert rows["GCF_000000009.1"]["label_concise"] == "Outer beta K9 [outgroup] [GCF_000000009.1]"
    for r in rows.values():
        assert "(GCF_" not in r["label_concise"] and "(GCF_" not in r["label_experiment"]
