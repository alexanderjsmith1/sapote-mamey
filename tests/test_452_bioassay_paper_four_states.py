# All constructed fixture subjects, match/assay values and biological scenarios in this module are fabricated regression inputs, not experimental evidence.
"""mamey/bioassay_paper.py: a cell with no numeric reading shows its recorded state(s), and collection rules live in config.

House rule: an assay cell has exactly four non-numeric states, +, −, n.t. and blank, and none is coerced into another.
Codex's A01 card labelled every qualitative-only cell 'qual.' (a fifth state), and its test expected a tested '−'
to read 'n.t.'. Collection names ('Bryophytes', moss/bee/attine) were also branches in the code; they now live in
mamey/data/bioassay_layouts.json or a file passed with --layout-config. Synthetic strains only.
"""
import json
import re
from pathlib import Path

import pytest

from mamey.bioassay_paper import prepare, write, empty_cell_label, layout_profile, LAYOUTS

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = {'+', '−', '+/−', 'n.t.', ''}


def _fixture(tmp_path, rows, roster=None):
    r = tmp_path / 'roster.tsv'; a = tmp_path / 'aliases.json'; t = tmp_path / 'assay.tsv'
    write(r, roster or [dict(strain='AS-1', genus='Unassigned', group='G1'), dict(strain='SYNTHETIC-CASE-002', genus='Unassigned', group='G1'),
                        dict(strain='AS-3', genus='Unassigned', group='G1')])
    a.write_text('{}')
    write(t, [dict(zip(('strain', 'organism', 'material', 'best_pct'), x)) for x in rows])
    return t, r, a


def _profiles(tmp_path, **over):
    p = json.loads(LAYOUTS.read_text()); prof = dict(p['moss']); prof.update(focal_group='G1', a06_subset_group='G1'); prof.update(over)
    f = tmp_path / 'layouts.json'; f.write_text(json.dumps({'test': prof})); return f


@pytest.mark.parametrize('states,label', [
    (['−'], '−'), (['-'], '−'), (['+'], '+'), (['+', '−'], '+/−'), (['n.t.'], 'n.t.'), ([''], ''), (['', 'n.t.'], ''),
])
def test_empty_cell_shows_recorded_states(tmp_path, states, label):
    rows = [(('AS-1', 'SYNTHETIC-CASE-002', 'AS-3')[i], 'MRSA', 'Crude extract', s) for i, s in enumerate(states)]
    t, r, a = _fixture(tmp_path, rows)
    p = prepare(t, r, a, 'A06', 'test', layouts=_profiles(tmp_path))
    cell = {(x['group'], x['target']): x for x in p['plot']}['No 16S sequence', 'MRSA']
    assert cell['n_tested'] == 0 and cell['label'] == label
    assert cell['n_qual_positive'] == states.count('+')
    assert cell['n_qual_negative'] == sum(s in ('-', '−') for s in states)


def test_no_label_outside_the_four_states(tmp_path):
    rows = [('AS-1', 'MRSA', 'Crude extract', '+'), ('SYNTHETIC-CASE-002', 'MRSA', 'Crude extract', '−'), ('AS-3', 'MRSA', 'Crude extract', 'n.t.'),
            ('AS-1', 'E. coli', 'Crude extract', ''), ('SYNTHETIC-CASE-002', 'Candida albicans', 'Crude extract', '−'),
            ('SYNTHETIC-CASE-002', 'Candida auris', 'Crude extract', '+'), ('AS-3', 'Foulbrood 818', 'Fraction', '-')]
    t, r, a = _fixture(tmp_path, rows)
    prof = _profiles(tmp_path)
    for kind in ('A02', 'A06'):
        for x in prepare(t, r, a, kind, 'test', layouts=prof)['plot']:
            assert x['label'] in ALLOWED or re.fullmatch(r'\d+/\d+', x['label']), x
            assert x['label'] != 'qual.'


def test_mixed_states_in_one_pooled_row_are_both_shown(tmp_path):
    rows = [('AS-1', 'Candida albicans', 'Crude extract', '+'), ('AS-1', 'Candida auris', 'Crude extract', '−')]
    t, r, a = _fixture(tmp_path, rows)
    cell = {(x['group'], x['target']): x for x in prepare(t, r, a, 'A06', 'test', layouts=_profiles(tmp_path))['plot']}
    assert cell['No 16S sequence', 'Candida sp.']['label'] == '+/−'


def test_collection_names_are_not_in_code():
    code = [ROOT / 'mamey/bioassay_paper.py'] + sorted((ROOT / 'tools').glob('bioassay_a0*.py')) + \
           sorted((ROOT / 'tools').glob('bioassay_a0*.R')) + [ROOT / 'tools/bioassay_paper_theme.R']
    for f in code:
        text = f.read_text()
        for word in ('Bryophytes', 'Lichens', 'Mushrooms', 'moss', 'attine'):
            assert not re.search(rf"""['"]{word}['"]""", text), (f.name, word)
        assert not re.search(r"""layout\s*[!=]=\s*['"]""", text), f.name


def test_profiles_reproduce_the_previous_per_collection_rules():
    moss, bee, attine = (layout_profile(x) for x in ('moss', 'bee', 'attine'))
    assert (moss['focal_group'], bee['focal_group'], attine['focal_group']) == ('Bryophytes', None, None)
    assert (moss['split_larvae'], bee['split_larvae'], attine['split_larvae']) == (False, True, False)
    assert attine['unassigned_label'] == '16S not determined' and moss['unassigned_label'] == 'No 16S genus on record'
    assert (moss['a04_source_shape'], bee['a04_source_shape'], attine['a04_source_shape']) == (True, True, False)
    assert (moss['a03_source_shape'], bee['a03_source_shape'], attine['a03_source_shape']) == (True, True, True)
    # Bee draws host-group shapes with a legend and labels only isolates strong against both targets (owner ruling, 19 Oct).
    assert bee['a04_point_labels'] == 'strong'
    with pytest.raises(ValueError, match='Unknown layout'):
        layout_profile('nonexistent')


def test_a_user_layout_file_sets_the_focal_group(tmp_path):
    roster = [dict(strain='AS-1', genus='Streptomyces', group='Focal'), dict(strain='SYNTHETIC-CASE-002', genus='Nocardia', group='Other')]
    t, r, a = _fixture(tmp_path, [('AS-1', 'MRSA', 'Crude extract', '90'), ('SYNTHETIC-CASE-002', 'MRSA', 'Crude extract', '10')], roster)
    p = prepare(t, r, a, 'A01', 'test', layouts=_profiles(tmp_path, focal_group='Focal'))
    assert {x['strain']: x['row'] for x in p['plot']} == {'AS-1': 'Streptomyces', 'SYNTHETIC-CASE-002': 'Other'}


def test_hplc_fractions_are_their_own_material(tmp_path):
    """HPLC fractions are kept apart from flash fractions (owner ruling, 19 Oct): A02 asked for HPLC draws only HPLC rows."""
    roster = [dict(strain='AS-1', genus='Streptomyces', group='G'), dict(strain='SYNTHETIC-CASE-002', genus='Nocardia', group='Untested')]
    t, r, a = _fixture(tmp_path, [('AS-1', 'MRSA', 'Crude extract', '10'), ('AS-1', 'MRSA', 'Fraction', '50'),
                                  ('AS-1', 'MRSA', 'HPLC fraction', '90')], roster)
    p = prepare(t, r, a, 'A02', 'test', material='HPLC fraction', layouts=_profiles(tmp_path))
    assert {x['material'] for x in p['plot']} == {'HPLC fraction'}
    assert {x['group'] for x in p['plot']} == {'G'}          # a group with no HPLC fraction tested is not drawn
    assert [x['label'] for x in p['plot'] if x['target'] == 'MRSA'] == ['1/1']
    d = prepare(t, r, a, 'A02', 'test', layouts=_profiles(tmp_path))
    assert {x['material'] for x in d['plot']} == {'Crude extract', 'Fraction'}
