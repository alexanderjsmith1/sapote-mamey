"""The package's DIAMOND guidance must state the import limit the program actually has.

The main CLI has no `--diamond-tsv` option and no workbook importer for DIAMOND output.
`docs/troubleshooting/DIAMOND_DATA_WORKFLOW.md` says so. The package copy written by
`mamey/cell_provenance.py`, the provenance rows and the shipped template used to tell the
reader to "import TSV", which no command does. The HMMER rows were already corrected the
same way; these checks hold DIAMOND to the same rule.
"""
import csv
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "Cell_Provenance_Template.csv"


def test_generated_diamond_guide_states_the_actual_integration_limit(tmp_path):
    from mamey.cell_provenance import _write_troubleshooting_folder

    _write_troubleshooting_folder(tmp_path)
    guide = (tmp_path / "Troubleshooting" / "DIAMOND_Data_Workflow.md").read_text()
    assert "no general `--diamond-tsv` option or automatic workbook importer" in guide
    assert "Keep `NEEDS_DIAMOND_TSV`" in guide
    assert "Import the tabular TSV output" not in guide


def test_diamond_glossary_entry_does_not_promise_an_import():
    from mamey.cell_provenance import STATUS_GLOSSARY

    assert "no general workbook importer" in STATUS_GLOSSARY["NEEDS_DIAMOND_TSV"]


def test_raw_diamond_tsv_does_not_clear_pending_rows(tmp_path):
    from mamey.cell_provenance import write_cell_provenance

    # Synthetic complete locus: AS-900 / NODE_1_length_2000_cov_10.0 / region001 / BGC001.
    run = SimpleNamespace(context=SimpleNamespace(strain_id="AS-900"), bgcs=[
        SimpleNamespace(bgc_id="BGC001", contig="NODE_1_length_2000_cov_10.0",
                        region="region001", products=[], edge_status="Interior")])
    (tmp_path / "STRAIN_diamond_hits.tsv").write_text("q1\ts1\t99.0\n")
    provenance, _, _ = write_cell_provenance(run, tmp_path)
    with provenance.open() as handle:
        rows = [r for r in csv.DictReader(handle) if r["status_code"] == "NEEDS_DIAMOND_TSV"]
    assert len(rows) == 2
    assert all(r["current_value"] == "" for r in rows)
    assert all("no general workbook importer" in r["source_parser"] for r in rows)
    assert all("pending until source-bound integration has a receipt" in r["how_to_fill"] for r in rows)
    assert not any("import TSV" in r["how_to_fill"] for r in rows)


def test_template_diamond_row_keeps_the_import_limit_explicit():
    with TEMPLATE.open(encoding="utf-8", newline="") as handle:
        rows = [r for r in csv.DictReader(handle) if r["status_code"] == "NEEDS_DIAMOND_TSV"]
    assert rows
    assert all("no general workbook importer" in r["source_parser"] for r in rows)
    assert all("pending until source-bound integration has a receipt" in r["how_to_fill"] for r in rows)
