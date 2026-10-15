"""Failing-first sibling admission tests; source claims never selected by precedence."""
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest

SRC = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SRC))


@pytest.fixture
def module():
    import mamey.blastp_ingest as baseline
    path = os.environ.get('TROVE_STRAIN_TOOL')
    if not path:
        return baseline
    spec = importlib.util.spec_from_file_location('mamey.trove_strain_candidate', path)
    instance = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = instance
    spec.loader.exec_module(instance)
    return instance


def package(tmp_path):
    # Synthetic full identity: SYN-A / NODE_1_length_90_cov_1 / region001 / BGC001.
    pkg = tmp_path / 'package'
    pkg.mkdir()
    (pkg / 'manifest.json').write_text(json.dumps({'strain_id': 'SYN-A'}))
    (pkg / 'SYN-A_gene_context.jsonl').write_text(json.dumps(
        {'bgc_id': 'BGC001', 'cds': [{'locus_tag': 'ctg1_1', 'aa_length': 30}]}) + '\n')
    (pkg / 'SYN-A_cds_table.csv').write_text('bgc_id,locus_tag,length_aa\nBGC001,ctg1_1,30\n')
    return pkg


def source(tmp_path, mode, changes):
    bgc = 'BGC099' if mode == 'rekey' else 'BGC001'
    folder = tmp_path / 'trove' / bgc
    folder.mkdir(parents=True)
    row = dict(query_strain='SYN-A', bgc_id=bgc, gene='ctg1_1', aa_length='30',
               subject_acc='SYN_HIT.1', subject_def='synthetic protein',
               subject_organism='Synthetic species', pct_identity='82',
               query_coverage='100', evalue='1e-9', bitscore='100', hit_rank='1')
    row.update(changes)
    suffix = '_blastp_top10.csv' if mode == 'top10' else '_top_hit_per_gene.csv'
    path = folder / (bgc + suffix)
    with path.open('w', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=list(row))
        writer.writeheader()
        writer.writerow(row)
    return folder.parent, path


def run(module, mode, pkg, trove):
    if mode == 'top10':
        return module.install_channel_top10(pkg, trove, 'nr')
    return module.ingest_blastp_trove(pkg, trove, 'nr', rekey_by_locus=mode == 'rekey')


CONFLICTS = [
    {'strain': 'SYN-B'},
    {'strain_id': 'SYN-B'},
    {'query_strain': '', 'strain': 'SYN-A', 'strain_id': 'SYN-B'},
    *[{alias: 'SYN-B|BGC001|gene=ctg1_1|aa=30'}
      for alias in ['query_locus', 'query_id', 'query_gene', 'gene', 'locus_tag']],
    {'query_locus': 'ctg1_1', 'query_id': 'SYN-B|BGC001|ctg1_1|30'},
    {'query_id': 'SYN-A|BGC001|ctg1_1|30', 'query_gene': 'SYN-B|BGC001|ctg1_1|30'},
    {'query_id': 'SYN-B BGC001 ctg1_1 30'},
]


@pytest.mark.parametrize('mode', ['strict', 'rekey', 'top10'])
@pytest.mark.parametrize('claims', CONFLICTS)
def test_conflicts_typed_quarantine_before_overlay_or_store(module, tmp_path, mode, claims):
    pkg = package(tmp_path)
    trove, path = source(tmp_path, mode, claims)
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest()
              for p in [path, *pkg.iterdir()]}
    result = run(module, mode, pkg, trove)
    assert result.get('genes', result.get('hits')) == 0
    assert result['quarantined'] == 1
    rows = list(csv.DictReader(Path(result['quarantine']).open()))
    assert rows[0]['reason'] == 'QUERY_STRAIN_CONFLICT'
    assert json.loads(rows[0]['source_row_json'])
    receipt = json.loads(Path(result['receipt']).read_text())
    assert receipt['admitted_total'] == 0
    assert receipt['quarantined_by_reason']['QUERY_STRAIN_CONFLICT'] == 1
    assert all(hashlib.sha256(p.read_bytes()).hexdigest() == sha for p, sha in before.items())
    assert not list((pkg / 'blastp_online').glob('*_online_blastp.csv'))
    assert not list((pkg / 'blastp_nr').glob('*_top10.csv'))


@pytest.mark.parametrize('mode', ['strict', 'rekey', 'top10'])
@pytest.mark.parametrize('claims', [
    {},
    {'strain': 'SYN-A', 'strain_id': ' SYN-A ', 'query_id': 'SYN-A|BGC001|gene=ctg1_1|aa=30'},
    {'query_strain': '', 'query_id': 'SYN-A|BGC001|ctg1_1|30'},
])
def test_consistent_normal_rows_and_old_bgc_rekey_still_admitted(module, tmp_path, mode, claims):
    pkg = package(tmp_path)
    trove, path = source(tmp_path, mode, claims)
    before = path.read_bytes()
    result = run(module, mode, pkg, trove)
    assert result.get('genes', result.get('hits')) == 1
    assert result['quarantined'] == 0
    assert path.read_bytes() == before
    if mode == 'rekey':
        assert result['bgcs_written'] == {'BGC001': 1}


@pytest.mark.parametrize('mode', ['strict', 'rekey', 'top10'])
def test_consistent_foreign_only_claims_remain_foreign_not_conflict(module, tmp_path, mode):
    pkg = package(tmp_path)
    trove, _ = source(tmp_path, mode, {'query_strain': 'SYN-B', 'strain': 'SYN-B',
                                     'query_id': 'SYN-B|BGC001|gene=ctg1_1|aa=30'})
    result = run(module, mode, pkg, trove)
    assert result.get('genes', result.get('hits')) == 0
    row = next(csv.DictReader(Path(result['quarantine']).open()))
    assert row['reason'] == 'FOREIGN_STRAIN'


def test_hidden_encoded_claim_does_not_widen_previously_legacy_held_row(module, tmp_path):
    pkg = package(tmp_path)
    trove, _ = source(tmp_path, 'strict', {'query_strain': '', 'query_locus': 'ctg1_1',
                                         'query_id': 'SYN-A|BGC001|ctg1_1|30'})
    result = run(module, 'strict', pkg, trove)
    assert result['genes'] == 0
    assert next(csv.DictReader(Path(result['quarantine']).open()))['reason'] == 'LEGACY_PROVENANCE_HOLD'


@pytest.mark.parametrize('mode', ['strict', 'rekey', 'top10'])
@pytest.mark.parametrize('prefix', ['ctg1_1', 'ctg1', 'BGC001_ctg1_1', 'NODE_1'])
def test_legacy_space_prefix_is_not_invented_strain_claim(module, tmp_path, mode, prefix):
    pkg = package(tmp_path)
    trove, _ = source(tmp_path, mode, {'query_id': f'{prefix} BGC001 gene=ctg1_1 aa=30'})
    result = run(module, mode, pkg, trove)
    assert result.get('genes', result.get('hits')) == 1
    assert result['quarantined'] == 0


def historical_package(case, pkg, raw):
    import base64
    bound = json.loads((SRC / "tests/fixtures/audit451_historical_blastp_packages.json").read_text())
    fixture = bound["cases"][case]
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == fixture["source_sha256"]
    for relative, encoded in fixture["package_files"].items():
        target = pkg / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(encoded))
    return pkg / fixture["receipt_relative_path"]

@pytest.mark.parametrize('mode', ['strict', 'top10'])
def test_upgrade_of_consistent_source_preserves_immutable_receipt(module, tmp_path, mode):
    pkg = package(tmp_path)
    trove, raw = source(tmp_path, mode, {})
    receipt = historical_package('valid_' + mode, pkg, raw)
    before = receipt.read_bytes()
    result = run(module, mode, pkg, trove)
    assert result.get('genes', result.get('hits')) == 1
    assert receipt.read_bytes() == before


def test_historical_conflicting_top10_collision_holds_before_changing_old_evidence(module, tmp_path):
    pkg = package(tmp_path)
    trove, raw = source(tmp_path, 'top10', {'query_id': 'SYN-B|BGC001|gene=ctg1_1|aa=30'})
    historical_package('conflicting_top10', pkg, raw)
    before = {p.relative_to(pkg): p.read_bytes() for p in pkg.rglob('*') if p.is_file()}
    raw_before = raw.read_bytes()
    with pytest.raises(ValueError, match='immutable BLASTP quarantine collision'):
        run(module, 'top10', pkg, trove)
    assert {p.relative_to(pkg): p.read_bytes() for p in pkg.rglob('*') if p.is_file()} == before
    assert raw.read_bytes() == raw_before
