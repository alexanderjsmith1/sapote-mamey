"""SEXTANT_422o — the shipped Cell_Provenance template must satisfy the schema
the engine enforces on real runs.

In v9.7.421 the HMM-marker row carried an unquoted comma inside notes_for_llm
("This is domain/marker evidence, not BLASTP homolog evidence."), so csv parsed
it as 15 fields under a 14-column header: a surplus None-keyed field and a
truncated notes_for_llm.  mamey/cell_provenance.py defines HEADERS (14) and
validates status_code against STATUS_CODES on every real run — so the shipped
example of the schema violated the schema.

It survived because the only test touching this file asserted that it exists.
A test that cannot fail on a corrupt file is not a guard.
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "templates" / "Cell_Provenance_Template.csv"


def _rows():
    with TEMPLATE.open(encoding="utf-8", newline="") as fh:
        return list(csv.reader(fh))


def test_template_present():
    assert TEMPLATE.is_file(), TEMPLATE


def test_every_row_has_exactly_the_header_width():
    rows = _rows()
    width = len(rows[0])
    bad = [(i, len(r)) for i, r in enumerate(rows[1:], start=2) if len(r) != width]
    assert not bad, f"header is {width} fields; offending rows (1-indexed, width): {bad}"


def test_header_matches_the_engine_contract():
    sys.path.insert(0, str(ROOT))
    from mamey.cell_provenance import HEADERS
    assert _rows()[0] == list(HEADERS)


def test_no_dictreader_surplus_field():
    with TEMPLATE.open(encoding="utf-8", newline="") as fh:
        for i, row in enumerate(csv.DictReader(fh), start=2):
            assert None not in row, f"row {i} produced a surplus unnamed field: {row.get(None)!r}"


def test_notes_column_survives_intact():
    """The row that motivated this patch keeps its full sentence."""
    with TEMPLATE.open(encoding="utf-8", newline="") as fh:
        rows = [r for r in csv.DictReader(fh) if r["status_code"] == "NEEDS_HMMER_DOMTBLOUT"]
    assert rows, "expected the HMMER marker row in the template"
    assert rows[0]["notes_for_llm"].endswith("not BLASTP homolog evidence.")


def test_generated_hmmer_guide_states_the_actual_integration_limit(tmp_path):
    from mamey.cell_provenance import _write_troubleshooting_folder

    _write_troubleshooting_folder(tmp_path)
    guide = (tmp_path / 'Troubleshooting' / 'HMMER_Data_Workflow.md').read_text()
    assert 'no general `--hmmer-domtblout` option or automatic workbook importer' in guide
    assert 'Keep `NEEDS_HMMER_DOMTBLOUT`' in guide
    assert 'amino-acid SHA-256' in guide and 'match coordinates' in guide
    assert 'separate evidence channels' in guide
    assert 'when filling workbook evidence cells' not in guide
    assert 'Run `hmmscan --domtblout STRAIN_hmmscan.domtblout mamey_markers.hmm' not in guide


def test_raw_hmmer_file_does_not_clear_pending_package_worklist(tmp_path):
    from types import SimpleNamespace
    from mamey.cell_provenance import STATUS_CODES, write_cell_provenance

    # Synthetic complete locus: AS-900 / NODE_1_length_2000_cov_10.0 / region001 / BGC001.
    run = SimpleNamespace(context=SimpleNamespace(strain_id='AS-900'), bgcs=[
        SimpleNamespace(bgc_id='BGC001', contig='NODE_1_length_2000_cov_10.0',
                        region='region001', products=[], edge_status='Interior')])
    (tmp_path / 'STRAIN_hmmscan.domtblout').write_text('# independent output, not an integration receipt\n')
    provenance, worklist, _ = write_cell_provenance(run, tmp_path)
    with provenance.open() as handle:
        rows = list(csv.DictReader(handle))
    hmm = [row for row in rows if row['status_code'] == 'NEEDS_HMMER_DOMTBLOUT']
    assert len(hmm) == 2
    assert all(row['status_code'] in STATUS_CODES for row in rows)
    assert all(row['current_value'] == '' for row in hmm)
    assert all('no general workbook importer' in row['source_parser'] for row in hmm)
    assert all('pending until source-bound integration has a receipt' in row['how_to_fill'] for row in hmm)
    with worklist.open() as handle:
        pending = [row for row in csv.DictReader(handle) if row['status_code'] == 'NEEDS_HMMER_DOMTBLOUT']
    assert len(pending) == 2 and all(row['blocking_for_claims'] == 'yes' for row in pending)


def test_template_hmmer_row_keeps_the_import_limit_explicit():
    with TEMPLATE.open(encoding='utf-8', newline='') as handle:
        rows = [row for row in csv.DictReader(handle) if row['status_code'] == 'NEEDS_HMMER_DOMTBLOUT']
    assert rows
    assert all('no general workbook importer' in row['source_parser'] for row in rows)
    assert all('pending until source-bound integration has a receipt' in row['how_to_fill'] for row in rows)
