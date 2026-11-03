"""Blank query identifiers must be held and recorded before downstream work."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


shared = load('missing_id_phylo16s', ROOT / 'tools' / '_phylo16s.py')


@pytest.mark.parametrize('header', ['', '   ', '\t\n', None])
def test_blank_id_produces_hold(header):
    result = shared.screen_query_records([(header, 'A' * 250)])[0]
    assert result['query_id'] == ''
    assert result['admission_state'] == 'HOLD'
    assert result['hold_reasons'] == ['QUERY_ID_MISSING']
    assert result['length'] == 250


def test_valid_and_duplicate_ids_keep_existing_qc_behavior():
    rows = shared.screen_query_records([('example label', 'A' * 250), ('example other', 'A' * 250)])
    assert [r['query_id'] for r in rows] == ['example', 'example']
    assert rows[0]['admission_state'] == 'ADMITTED'
    assert rows[1]['hold_reasons'] == ['QUERY_ID_DUPLICATE']
    with pytest.raises(ValueError, match='QUERY_FASTA_EMPTY'):
        shared.screen_query_records([])


def test_autopilot_records_hold_before_downstream_work(tmp_path, monkeypatch):
    autopilot = load('missing_id_autopilot', ROOT / 'tools' / 'phylo_autopilot.py')
    monkeypatch.setattr(autopilot, '_p16', shared)
    monkeypatch.setattr(shared, 'refseq_16s_blastdb', lambda path: path)
    def forbidden(*args, **kwargs):
        pytest.fail('downstream work must not run for a held query')
    monkeypatch.setattr(autopilot, 'assign_genus', forbidden)
    query = tmp_path / 'query.fasta'
    query.write_text('>   \n' + 'A' * 250 + '\n')
    outdir = tmp_path / 'result'
    result = autopilot.main(['run-16s', '--query', str(query), '--db', 'unused', '--group', 'rare_genera', '--outdir', str(outdir), '--dry-run'])
    assert result == 2
    receipt = (outdir / 'query_qc.tsv').read_text()
    assert '\tHOLD\tQUERY_ID_MISSING\t' in receipt
    assert not (outdir / 'routing_table.tsv').exists()
