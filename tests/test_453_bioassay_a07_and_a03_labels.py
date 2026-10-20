"""A07 (every fraction, Candida against MRSA) and the A03 --point-labels option."""
import csv, json
from pathlib import Path
from mamey import bioassay_paper as bp


def _write(p, rows):
    with open(p, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]), delimiter='\t'); w.writeheader(); w.writerows(rows)


def test_prepare_fractions_one_point_per_fraction(tmp_path):
    table = tmp_path / 't.tsv'; roster = tmp_path / 'r.tsv'; aliases = tmp_path / 'a.json'
    _write(table, [
        dict(strain='AS-1', fraction='F1', organism='Candida albicans', material='Fraction', best_pct='90'),
        dict(strain='AS-1', fraction='F1', organism='Candida auris', material='Fraction', best_pct='95'),
        dict(strain='AS-1', fraction='F1', organism='MRSA', material='Fraction', best_pct='85'),
        dict(strain='AS-1', fraction='F2', organism='MRSA', material='Fraction', best_pct='10'),          # no Candida: not drawn
        dict(strain='AS-2', fraction='F1', organism='Candida (species not named)', material='Fraction', best_pct='5'),
        dict(strain='AS-2', fraction='F1', organism='MRSA', material='Fraction', best_pct='n.t.'),        # non-numeric: not drawn
        dict(strain='AS-9', fraction='F1', organism='Candida albicans', material='Fraction', best_pct='50'),  # alias of AS-1
        dict(strain='AS-9', fraction='F1', organism='MRSA', material='Fraction', best_pct='60'),
        dict(strain='AS-1', fraction='F3', organism='MRSA', material='HPLC fraction', best_pct='99'),       # other material
    ])
    _write(roster, [dict(strain='AS-1', genus='Streptomyces', group='Bumblebees'), dict(strain='AS-2', genus='Unassigned', group='Wasps')])
    aliases.write_text(json.dumps({'AS-9': 'AS-1'}))
    out = bp.prepare_fractions(table, roster, aliases, 'bee', 'Fraction')
    pts = {(r['strain'], r['fraction']): (r['x'], r['y']) for r in out['plot']}
    assert pts == {('AS-1', 'F1'): (95.0, 85.0)}            # the alias's F1 is the same fraction; best values kept


def test_point_labels_option_reaches_the_render_config(tmp_path):
    import inspect
    assert "'--point-labels'" in inspect.getsource(bp.cli)
    assert 'point_labels=a.point_labels' in inspect.getsource(bp.cli)
