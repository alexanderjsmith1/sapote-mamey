import csv
import json
from pathlib import Path

from mamey.tab_reconcile import build_tab_reconciliation


def test_tab_reconcile_bgc028_as760_fixture(tmp_path):
    antismash = Path('/mnt/data/AS-760.zip')
    package = Path('/mnt/data/AS-760_PATCHED_SapoteMamey_v9.7.229_engine1.9.109_Complete_Package.zip')
    if not antismash.exists() or not package.exists():
        # Allows source tree tests to run outside the ChatGPT fixture environment.
        return
    summary = build_tab_reconciliation(
        antismash, tmp_path, bgc='BGC028', package=package
    )
    assert summary['record_id'].startswith('NODE_32_length_60747_cov_53')
    ledger = Path(summary['ledger_csv'])
    assert ledger.exists()
    rows = list(csv.DictReader(ledger.open()))
    by_tab = {r['tab']: r for r in rows}
    assert by_tab['SubClusterBlast']['raw_result'] == 'NO_HITS'
    assert by_tab['TIGRFAM domains']['raw_result'] == 'NO_HITS'
    assert 'mal' in by_tab['NRPS/PKS predictions']['raw_result']
    assert 'weak' in by_tab['TFBS Finder']['raw_result']
    assert by_tab['KnownClusterBlast']['direct_evidence'] == 'positive'
