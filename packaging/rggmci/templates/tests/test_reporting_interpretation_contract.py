"""T172 standalone counts and code-bound interpretation; synthetic fixtures only."""
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest
from rggmci import cli, core
from rggmci._functional_profiles import _core_fraction, rescue_functional_complementarity

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('scored,retained,omitted,state', [
    (1360, 1000, 360, 'truncated'),
    (1360, 1001, 359, 'truncated'),  # a later HIGH retained beyond the rank cap
    (1, 1, 0, 'not truncated'),
    (0, 0, 0, 'not truncated'),
])
def test_count_sentence_explicit(scored, retained, omitted, state):
    s = {'scored_pairs': scored, 'pairs_exported': retained}
    noun = 'pair' if scored == 1 else 'pairs'
    assert cli.pair_count_sentence(s) == f'{scored} scored {noun}, {retained} retained, {omitted} not exported ({state})'


def test_actual_cli_prints_explicit_counts(monkeypatch, capsys, tmp_path):
    z = tmp_path / 'synthetic.zip'
    z.write_bytes(b'not read: writer/scorer are stubbed for console contract')
    monkeypatch.setattr(cli, 'run', lambda *args, **kw: {'pairs_total': 1360, 'ranked_pairs': [{}] * 1000, 'moderate_pairs': 560})
    monkeypatch.setattr(cli, '_write_result', lambda *args, **kw: None)
    assert cli.main([str(z), '--reference-completion', 'off']) == 0
    assert '1360 scored pairs, 1000 retained, 360 not exported (truncated)' in capsys.readouterr().out


def test_summary_uses_full_counts_not_retained_counts():
    # The sealed .464 scorer already owns this fix. Retain it without a fork.
    result = {'pairs_total': 1360, 'ranked_pairs': [{'rggmci_confidence': 'MODERATE_RG_GMCI_CANDIDATE'}] * 1000,
              'high_pairs': 75, 'moderate_pairs': 560}
    s = cli._summary('SYNTHETIC', result)
    assert (s['scored_pairs'], s['pairs_exported'], s['high'], s['moderate']) == (1360, 1000, 75, 560)


@pytest.mark.parametrize('flag,status,selected', [
    ('True', 'Interior', True), ('False', 'Edge', False),
    (None, 'Edge', True), (None, 'Full-contig', True), (None, 'Interior', False),
    ('conflicting', 'Edge', True), ('conflicting', 'Interior', False),
    ('protocluster_only', 'Interior', False),
])
def test_region_flags_and_fallback_match_docs(tmp_path, flag, status, selected):
    z = tmp_path / 'synthetic.zip'
    text = 'FEATURES             Location/Qualifiers\n     region          1..100\n'
    if flag == 'conflicting':
        text += '                     /contig_edge="True"\n                     /contig_edge="False"\n'
    elif flag == 'protocluster_only':
        text += '     protocluster    1..100\n                     /contig_edge="True"\n'
    elif flag:
        text += f'                     /contig_edge="{flag}"\n'
    with zipfile.ZipFile(z, 'w') as archive:
        archive.writestr('SYNTHETIC.region001.gbk', text)
    record = SimpleNamespace(bgc_id='BGC001', source_gbk='SYNTHETIC.region001.gbk', edge_status=status)
    assert core._contig_edge_bgcs(z, [record]) == ({'BGC001'} if selected else set())


@pytest.mark.parametrize('mode', ['missing_member', 'unreadable_zip'])
def test_missing_source_uses_fallback(tmp_path, mode):
    z = tmp_path / 'source.zip'
    if mode == 'unreadable_zip':
        z.write_bytes(b'not a zip')
    else:
        with zipfile.ZipFile(z, 'w'):
            pass
    b = SimpleNamespace(bgc_id='BGC001', source_gbk='absent.region001.gbk', edge_status='Edge')
    assert core._contig_edge_bgcs(z, [b]) == {'BGC001'}


def test_core_fraction_denominator_and_zero_are_descriptors():
    assert _core_fraction({'core': 2, 'tailoring': 1, 'transport': 1, 'regulatory': 1, 'other': 95}) == 2 / 5
    other_only = {'other': 8, 'roles_present': []}
    assert _core_fraction(other_only) == 0
    assert rescue_functional_complementarity(other_only, other_only)['functional_rescue_class'] == 'ACCESSORY_ONLY'
    assert rescue_functional_complementarity(None, other_only)['a_core_fraction'] is None


def test_docs_expose_truncation_and_uncertainty():
    readme = (ROOT / 'README.md').read_text()
    guide = (ROOT / 'docs/OUTPUT_GUIDE.md').read_text()
    worked = (ROOT / 'docs/WORKED_EXAMPLES.md').read_text()
    assert '1,360' in readme and '360 were not exported' in guide
    assert 'later HIGH pairs are always kept' in readme
    assert 'zero denominator returns 0.0' in guide
    assert 'does not require tailoring genes' in guide
    assert 'does not assign a compound family' in guide
    assert 'An explicit `False` excludes' in worked
    assert 'does not establish that the' in worked
    assert 'does\nnot establish two copies' in worked
    assert '## 2. Two copies rather than two halves' not in worked


def test_worked_profiles_are_explicit():
    worked = (ROOT / 'docs/WORKED_EXAMPLES.md').read_text()
    assert 'three Actinomadura archives recording `loose`' in worked
    assert 'one Saccharopolyspora archive recording `relaxed`' in worked
    assert 'Some records lack that field' in worked
    assert 'not a uniform-profile comparison' in worked
    assert 'Historical report on 40 genomes' in worked


@pytest.mark.parametrize('state', ['DIAMOND_NOT_FOUND', 'DIAMOND_DB_NOT_FOUND', 'NO_PAIRS_IN_SCOPE'])
def test_optional_residue_no_search_states_match_reader_contract(tmp_path, monkeypatch, state):
    from rggmci import residue_tiling as rt
    def forbidden(*args, **kwargs):
        pytest.fail('no-search regression attempted an alignment')
    monkeypatch.setattr(rt, '_run_diamond', forbidden)
    monkeypatch.setattr(rt, 'find_diamond', lambda *_: None if state == 'DIAMOND_NOT_FOUND' else 'synthetic-never-run')
    db = tmp_path / 'synthetic.dmnd'
    if state == 'NO_PAIRS_IN_SCOPE':
        db.write_bytes(b'not a real database; no pair qualifies for search')
    pair = {'rggmci_confidence': 'SYNTHETIC_UNCHANGED'}
    result = {'ranked_pairs': [pair]}
    rt.add_residue_tiling(result, tmp_path / 'not-read.zip', [], {}, db)
    assert result['residue_tiling_status']['state'] == state
    assert result['residue_tiling_status']['pairs_tested'] == 0
    assert pair['residue_tiling'] == 'NOT_TESTED'
    assert pair['rggmci_confidence'] == 'SYNTHETIC_UNCHANGED'
    guide = (ROOT / 'docs/OUTPUT_GUIDE.md').read_text()
    assert 'Present only when the DIAMOND search ran' not in guide
    assert 'initialized when the residue layer is invoked' in guide
    assert state in guide and 'without an alignment search' in guide


def test_completion_off_does_not_describe_explicit_residue_layer(tmp_path, monkeypatch):
    from rggmci import residue_tiling as rt
    def forbidden(*args, **kwargs):
        pytest.fail('OFF-layer regression attempted an alignment')
    monkeypatch.setattr(rt, '_run_diamond', forbidden)
    monkeypatch.setattr(rt, 'find_diamond', lambda *_: None)
    monkeypatch.setattr(core, 'parse_clusterblast_reference_map', lambda *_: {'status': 'SYNTHETIC'})
    monkeypatch.setattr(core, '_glycosyltransferase_bgcs', lambda *_: set())
    monkeypatch.setattr(core, '_contig_edge_bgcs', lambda *_: set())
    pair = {'rggmci_confidence': 'SYNTHETIC_UNCHANGED'}
    monkeypatch.setattr(core, 'compute_rggmci', lambda *args, **kwargs: {'ranked_pairs': [pair]})
    monkeypatch.setattr(core, 'related_locus_pairs', lambda *args, **kwargs: [])
    result = core.run_rggmci(tmp_path / 'not-read.zip', [], reference_completion='off',
                             diamond_db=tmp_path / 'not-read.dmnd')
    assert result['reference_completion']['completion_tier'] == 'OFF'
    assert result['residue_tiling_status']['state'] == 'DIAMOND_NOT_FOUND'
    assert pair['residue_tiling'] == 'NOT_TESTED'
    guide = (ROOT / 'docs/OUTPUT_GUIDE.md').read_text()
    assert 'off disables reference-guided completion only' in guide
    assert 'explicit `--diamond-db` can still invoke residue tiling' in guide
