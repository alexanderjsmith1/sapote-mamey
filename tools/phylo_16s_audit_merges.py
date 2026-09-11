
"""phylo 16s audit merges. External inputs remain outside the software bundle."""
import argparse
from contextlib import closing
import os
import sqlite3
import sys
import tempfile

import os as _os, sys as _sys
_sys.path.insert(0, _os.path.dirname(_os.path.abspath(__file__)))
import logging
_LOG = logging.getLogger(__name__)
import _phylo16s as _p16

DB = _p16.rrna16s_db(os.environ.get("SAPOTE_16S_SQLITE"), must_exist=False)
MIN_COLS = 500
CONFLICT_PCT = 97.0


def ident(x, y):
    if not x or not y or len(x) != len(y):
        raise ValueError('missing or unequal aligned sequences')
    n = m = 0
    for a, b in zip(x, y):
        if a.upper() not in 'ACGT' or b.upper() not in 'ACGT':
            continue
        n += 1
        m += (a.upper() == b.upper())
    return (100.0 * m / n if n else None), n


def align(sa, sb):
    sa, sb = _p16.sequence(sa), _p16.sequence(sb)
    with tempfile.NamedTemporaryFile("w", suffix=".fa", delete=False) as fh:
        fh.write(f">a\n{sa}\n>b\n{sb}\n")
        p = fh.name
    try:


        out = _p16.run_checked([_p16.mafft_bin(), "--auto", "--thread", "1", p],
                               "mafft (merge-audit pairwise alignment)",
                               allow_empty_stdout=False).stdout
    finally:
        os.unlink(p)
    seqs, k = {}, None
    for line in out.splitlines():
        if line.startswith(">"):
            k = line[1:].strip()
            if k not in {'a','b'} or k in seqs:
                raise ValueError('MAFFT returned unexpected or duplicate sequence IDs')
            seqs[k] = []
        elif k:
            seqs[k].append(line.strip())
    if set(seqs) != {'a','b'}:
        raise ValueError('MAFFT output is missing a sequence')
    a, b = ''.join(seqs['a']), ''.join(seqs['b'])
    if len(a) != len(b) or a.replace('-','').upper() != sa or b.replace('-','').upper() != sb:
        raise ValueError('MAFFT alignment does not bind to input sequences')
    return a, b


def main(argv=()):
    ap = argparse.ArgumentParser(allow_abbrev=False)
    ap.add_argument('--db',default='')
    ap.add_argument('--out-db')
    ap.add_argument('--dry-run',action='store_true')
    a = ap.parse_args(argv)
    db = _p16.rrna16s_db(a.db or None)
    if not a.dry_run and not a.out_db:
        ap.error('--out-db is required for an additive result')
    if a.out_db:
        _p16.require_new_output(a.out_db)
    db = _p16.rrna16s_db(a.db or None)
    digest = _p16.sha256_file(db)
    events = []
    with closing(_p16.database_copy(db)) as con:
        pairs = con.execute('SELECT rowid,strain_uid,acc_a,acc_b FROM merge_audit').fetchall()
        if a.dry_run:
            _LOG.info(f'DRY_RUN: {len(pairs)} pairs; no alignment or output writes')
            return 0
        for rid, uid, aa, bb in pairs:
            values = [con.execute('SELECT seq FROM record WHERE acc_base=?',(acc,)).fetchone() for acc in (aa,bb)]
            if any(row is None or not row[0] for row in values):
                raise ValueError('merge-audit pair has missing input sequence')
            sa, sb = [row[0] for row in values]
            x, y = align(sa,sb)
            pct, cols = ident(x,y)
            status = ('INSUFFICIENT_COMPARABLE_COLUMNS' if cols < MIN_COLS else
                      'SIMILARITY_SCREEN_PASS' if pct >= CONFLICT_PCT else 'SIMILARITY_SCREEN_FLAG')
            event = dict(strain_uid=uid,acc_a=aa,acc_b=bb,pct_identity=pct,comparable_columns=cols,
                         status=status,authority='alignment screen only; strain merge unvalidated')
            events.append(event)
            # Retain the original k-mer note; alignment results live in an additive receipt table.
        con.execute('CREATE TABLE IF NOT EXISTS merge_alignment_screen '
                    '(strain_uid TEXT,acc_a TEXT,acc_b TEXT,pct_identity REAL,comparable_columns INTEGER,status TEXT)')
        con.executemany('INSERT INTO merge_alignment_screen VALUES (?,?,?,?,?,?)',
            [(e['strain_uid'],e['acc_a'],e['acc_b'],e['pct_identity'],e['comparable_columns'],e['status']) for e in events])
        if _p16.sha256_file(db) != digest:
            raise ValueError('input database changed during audit')
        _p16.save_database(con,a.out_db,'merge_alignment_screen',dict(input_sha256=digest,pairs=events,
            min_columns=MIN_COLS,threshold_pct=CONFLICT_PCT,status='MERGE_ACCEPTANCE_HELD'))
    _LOG.info(f'{len(events)} pairs screened; no strain merges accepted; additive database: {a.out_db}')
    return 0


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    sys.exit(main(sys.argv[1:]))
