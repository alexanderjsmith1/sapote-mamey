"""Card 464_ingest_trove_summary: ingest-blastp-trove reports the BGCs that received rows, the quarantine
reasons, and the --rekey-by-locus hint when genes sat in other BGCs.

The old line counted zero-row BGCs: a fresh v9.7.463 package read "32 BGCs, 15 genes" when one BGC got rows and
600 were quarantined as NONCURRENT_LOCUS, with no hint. Synthetic result; the ingester itself is not run."""
import argparse
import csv

from mamey import blastp_ingest, cli


def _run(tmp_path, monkeypatch, capsys, rekey, reasons):
    q = tmp_path / 'q.csv'
    with q.open('w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['reason']); w.writeheader(); w.writerows({'reason': r} for r in reasons)
    res = dict(package=str(tmp_path), channel='nr', bgcs_written={'BGC001': 15, 'BGC002': 0, 'BGC003': 0}, genes=15,
               quarantined=len(reasons), quarantine=str(q), rekey_by_locus=rekey)
    monkeypatch.setattr(blastp_ingest, 'ingest_blastp_trove', lambda *a, **k: res)
    args = argparse.Namespace(package=str(tmp_path), trove=str(tmp_path), channel='nr', strain='SYN-971', rekey_by_locus=rekey)
    assert cli.ingest_blastp_trove_command(args) == 0
    return capsys.readouterr().out


def test_counts_filled_bgcs_and_hints_rekey(tmp_path, monkeypatch, capsys):
    out = _run(tmp_path, monkeypatch, capsys, False, ['NONCURRENT_LOCUS'] * 3 + ['ZERO_OR_BLANK_AA_LENGTH'])
    assert 'channel=nr 1 BGCs, 15 genes' in out
    assert 'quarantined 4 row(s): NONCURRENT_LOCUS 3, ZERO_OR_BLANK_AA_LENGTH 1' in out
    assert '--rekey-by-locus' in out


def test_no_hint_when_already_rekeyed(tmp_path, monkeypatch, capsys):
    out = _run(tmp_path, monkeypatch, capsys, True, ['ZERO_OR_BLANK_AA_LENGTH'])
    assert 'quarantined 1 row(s)' in out and 're-run with --rekey-by-locus' not in out
