"""Card 464_blastp_gate_guidance: the BLASTp gate finds the workspace's clustered-nr troves, says when
a trove predates the package's BGC numbering, and gives one fix command per trove root.

Seen on a fresh v9.7.463 package (5 Nov): the gate missed every '_NR_CLUSTER_RID*' root, suggested a plain
ingest that quarantined 600 of 615 nr rows as NONCURRENT_LOCUS, and named one root when the strain's clustered
results sat in two. Synthetic IDs only."""
import csv
from pathlib import Path

from mamey import blastp_gate


def _write(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)


def _package(tmp):
    pkg = tmp / 'ws' / 'runs' / 'SYN-971' / 'package'
    rows = [dict(strain='SYN-971', bgc_id='BGC001', locus_tag='ctg1_1', length_aa=100),
            dict(strain='SYN-971', bgc_id='BGC002', locus_tag='ctg2_1', length_aa=200),
            dict(strain='SYN-971', bgc_id='BGC002', locus_tag='ctg2_2', length_aa=210)]
    _write(pkg / 'SYN-971_cds_table.csv', ['strain', 'bgc_id', 'locus_tag', 'length_aa'], rows)
    return pkg


def _trove(root, bgc, genes):
    f = root / 'SYN-971' / bgc / f'{bgc}_blastp_top10_clustered.csv'
    _write(f, ['strain', 'bgc_id', 'gene', 'aa_length', 'hit_rank', 'subject_acc'],
           [dict(strain='SYN-971', bgc_id=bgc, gene=g, aa_length=a, hit_rank=1, subject_acc='WP_1') for g, a in genes])
    return f


def test_nr_cluster_and_clnr_roots_are_clustered_nr(tmp_path):
    base = tmp_path / 'ws'
    (base / 'Blastp RESULTS' / '_NR_CLUSTER_RID_WAVE1_B').mkdir(parents=True)
    (base / 'Blastp RESULTS' / '_NR_CLNR_GAP_A').mkdir(parents=True)
    (base / 'Blastp RESULTS' / '_NR_RID').mkdir(parents=True)
    found = blastp_gate.discover_trove_roots(base, roots_base=base)
    assert sorted(p.name for p in found['clustered_nr']) == ['_NR_CLNR_GAP_A', '_NR_CLUSTER_RID_WAVE1_B']
    assert [p.name for p in found['nr']] == ['_NR_RID']          # the nr names still do not claim either


def test_alias_drift_flags_older_numbering(tmp_path):
    pkg = _package(tmp_path)
    old = _trove(tmp_path / 'tr', 'BGC001', [('ctg2_1', 200), ('ctg2_2', 210)])   # genes now in BGC002
    same = _trove(tmp_path / 'tr', 'BGC002', [('ctg2_1', 200)])
    drift = blastp_gate.alias_drift(pkg, [('clustered_nr', 'BGC001', str(old)), ('clustered_nr', 'BGC002', str(same))])
    assert drift == {'clustered_nr': (1, 2)}
    assert blastp_gate.alias_drift(pkg, [('clustered_nr', 'BGC002', str(same))]) == {}


def test_block_message_gives_rekey_and_one_command_per_root(tmp_path):
    pkg = _package(tmp_path)
    a = _trove(tmp_path / 'A' / 'results', 'BGC001', [('ctg2_1', 200)])
    b = _trove(tmp_path / 'B' / 'results', 'BGC009', [('ctg2_2', 210)])
    missing = [('clustered_nr', 'BGC001', str(a)), ('clustered_nr', 'BGC009', str(b))]
    msg = blastp_gate.format_block_message('SYN-971', pkg, missing, set(), blastp_gate.alias_drift(pkg, missing))
    fixes = [l for l in msg.splitlines() if 'fix:' in l]
    assert len(fixes) == 2 and all('--rekey-by-locus' in l for l in fixes)
    assert str(tmp_path / 'A' / 'results') in fixes[0] and str(tmp_path / 'B' / 'results') in fixes[1]
    assert '2 of 2 saved BGC folders hold genes this package places in other BGCs' in msg


def test_single_root_message_unchanged_in_shape(tmp_path):
    pkg = _package(tmp_path)
    a = _trove(tmp_path / 'A' / 'results', 'BGC002', [('ctg2_1', 200)])
    msg = blastp_gate.format_block_message('SYN-971', pkg, [('clustered_nr', 'BGC002', str(a))], set(), {})
    fixes = [l for l in msg.splitlines() if 'fix:' in l]
    assert len(fixes) == 1 and '--rekey-by-locus' not in fixes[0] and '#' not in fixes[0]
