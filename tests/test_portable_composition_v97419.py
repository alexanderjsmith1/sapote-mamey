"""Portable negative controls for the reviewed .419 composition."""
from pathlib import Path
import importlib.util
import json
import sqlite3
import subprocess
import sys
import types
import pytest

ROOT = Path(__file__).resolve().parents[1]

def tool(name):
    spec = importlib.util.spec_from_file_location('_fixture_' + name, ROOT / 'tools' / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

@pytest.mark.parametrize('label', ['NR_123456.1 MW444715.1', 'MW444715.1 NR_123456.1', 'NR_123456.1 NR_234567.1', 'NR_123456.1 strain_NR_234567.1'])
def test_namespace_does_not_erase_another_accession(label):
    with pytest.raises(ValueError, match='REFERENCE_ACCESSION_CONFLICT'):
        tool('build_placement_ggtree_inputs')._ref_accession(label)

@pytest.mark.parametrize('strain', ['strain_PH21725', 'strain_YIM_PH21725', 'strain_CCTCC_AA97020_1'])
def test_declared_strain_field_is_preserved(strain):
    m = tool('build_placement_ggtree_inputs')
    name = 'NR_123456_1_Example_species_' + strain
    assert m._ref_accession(name) == 'NR_123456.1'
    label = m._ref_label(name, 'Example')
    assert 'PH21725' in label or 'AA97020' in label

def store(path, key):
    with sqlite3.connect(path) as con:
        con.execute('CREATE TABLE record(acc_base TEXT, isolation_source TEXT, country TEXT)')
        con.executemany('INSERT INTO record VALUES(?,?,?)', [('NR_123456', 'soil', 'country'), (key, '', '')])

def test_explicit_local_key_does_not_abort_reference_join(tmp_path, capsys):
    db = tmp_path / 'source.sqlite';store(db, 'AS_LOCAL_SID-100')
    assert tool('build_placement_ggtree_inputs')._load_ref_sources(db) == {'NR123456': 'soil · country'}
    assert 'skipped 1 non-reference row' in capsys.readouterr().err

@pytest.mark.parametrize('key', ['NR_broken', 'garbage', '', 'prefix_NR_123456_suffix', None])
def test_unknown_or_malformed_store_keys_still_refuse(tmp_path, key):
    db = tmp_path / 'source.sqlite';store(db, key)
    with pytest.raises(ValueError, match='REFERENCE_SOURCE_ACCESSION_INVALID'):
        tool('build_placement_ggtree_inputs')._load_ref_sources(db)

@pytest.mark.parametrize('text', [
    'SID-100 / NODE_1_length_100_cov_2 / region001 / BGC001 + BGC002',
    'SID-100 BGC001 and SID-101 / NODE_2_length_100_cov_2 / region002 / BGC002',
])
def test_citation_locators_cannot_be_borrowed_from_neighbours(text):
    from mamey.bgc_citation_gate import find_nodeless_bgc_citations
    assert find_nodeless_bgc_citations(text)

def test_complete_ordered_citations_pass_supplemental_gate():
    from mamey.bgc_citation_gate import find_nodeless_bgc_citations
    assert not find_nodeless_bgc_citations('SID-100 / NODE_1_length_100_cov_2 / region001 / BGC001 and SID-101 / NODE_2_length_100_cov_2 / region002 / BGC002')

def test_nested_inventory_does_not_depend_on_shared_discovery_bug(tmp_path, monkeypatch):
    m = tool('gen_tools_inventory')
    for rel in ['nested/probe.py', '.hidden/ignored.py', 'nested/__pycache__/ignored.py', 'nested/.ignored.py']:
        p = tmp_path / rel;p.parent.mkdir(parents=True, exist_ok=True);p.write_text('"""fixture"""\n')
    monkeypatch.setattr(m, 'TOOLS', tmp_path)
    assert [p.relative_to(tmp_path).as_posix() for p in m.tool_files()] == ['nested/probe.py']
    assert 'nested/probe.py' in dict(m.collect())
    assert '`tools/nested/probe.py`' in m.render_md(m.collect())
    assert '`tools/nested/probe.py`' in m.render_manifest_block(m.collect())

def test_release_runner_honours_configured_scope():
    script = (ROOT / 'tools/release_cut.sh').read_text()
    assert 'python3 -m pytest -q' in script
    assert 'python3 -m pytest tests/' not in script

def test_anti_emptying_guard_sees_adjacent_tools():
    spec = importlib.util.spec_from_file_location('_scope_guard', ROOT / 'tests/test_no_test_file_defines_zero_tests_v97416.py')
    m = importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    found = {p.relative_to(ROOT).as_posix() for p in m._collected_modules()}
    assert {'tools/test_reaction_gap_board.py', 'deliverable_tools/test_related.py'} <= found

def test_authority_refusal_is_preserved_without_traceback(tmp_path):
    env = __import__('os').environ.copy()
    env['OUTGROUP_REGISTRY'] = str(ROOT / 'data/OUTGROUP_REGISTRY.tsv')
    # Locate the actual bundled snapshot; explicit selection still cannot make it authoritative.
    from mamey.outgroup_registry_path import shipped_registry_path
    env['OUTGROUP_REGISTRY'] = str(shipped_registry_path())
    q = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/outgroup_registry.py'), 'lookup', 'Streptomyces'], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert q.returncode != 0
    assert 'OUTGROUP_AUTHORITY_UNBOUND' in q.stderr
    assert 'Traceback' not in q.stderr

@pytest.mark.parametrize('consumer', ['phylo_refset', 'phylo_place'])
def test_authority_consumers_handle_typed_refusal(consumer, tmp_path, monkeypatch):
    from mamey.outgroup_registry_path import RegistryAuthorityError
    def refuse(*args, **kw):raise RegistryAuthorityError('OUTGROUP_AUTHORITY_UNBOUND: fixture')
    stub = types.ModuleType('outgroup_registry');stub.RegistryAuthorityError = RegistryAuthorityError;stub.get_16s = refuse
    monkeypatch.setitem(sys.modules, 'outgroup_registry', stub)
    m = tool(consumer)
    if consumer == 'phylo_refset':
        with pytest.raises(SystemExit, match='OUTGROUP_AUTHORITY_UNBOUND'):
            m.add_outgroup([], 'Example', scope='genus')
    else:
        monkeypatch.setattr(m, '_is_protein', lambda path: False)
        monkeypatch.setattr(m, '_which', lambda *args: 'fixture-only-no-execution')
        args = types.SimpleNamespace(group='Actinomadura', add_outgroup='Actinomadura', approved_by='fixture', ref_fasta='fixture.fasta', refpkg=str(tmp_path / 'refpkg'))
        with pytest.raises(SystemExit, match='OUTGROUP_AUTHORITY_UNBOUND'):
            m.cmd_build_ref(args)

def test_refpkg_headers_survive_actual_genus_filter(tmp_path, monkeypatch):
    m = tool('phylo_place')
    ref = tmp_path / 'reference.fasta';og = tmp_path / 'outgroup.fasta'
    ingroup = 'NR_123456_1_Actinomadura_example_strain_100_16S'
    foreign = 'NR_234567_1_Othergenus_example_16S'
    ref.write_text(f'>{ingroup}\nACGT\n>{foreign}\nACGT\n')
    og.write_text('>Outgroup_example\nACGT\n')
    stub = types.ModuleType('outgroup_registry');stub.get_16s = lambda *a, **k: str(og)
    from mamey.outgroup_registry_path import RegistryAuthorityError
    stub.RegistryAuthorityError = RegistryAuthorityError
    monkeypatch.setitem(sys.modules, 'outgroup_registry', stub)
    monkeypatch.setattr(m, '_is_protein', lambda path: False)
    monkeypatch.setattr(m, '_which', lambda *args: 'fixture-only-no-execution')
    class FilterObserved(Exception):pass
    def capture(path, *args, **kwargs):
        text = Path(path).read_text()
        assert ingroup in text and '>Outgroup_example' in text
        assert foreign not in text
        raise FilterObserved()
    monkeypatch.setattr(m, '_dedup_reference', capture)
    args = types.SimpleNamespace(group='Actinomadura', add_outgroup='Actinomadura', approved_by='fixture', ref_fasta=str(ref), refpkg=str(tmp_path / 'refpkg'))
    with pytest.raises(FilterObserved):m.cmd_build_ref(args)

def test_census_catches_equal_count_outcome_churn(tmp_path, monkeypatch, capsys):
    m = tool('suite_count_census')
    snapshot = dict(schema='suite-count-census-v2', scopes='configured_testpaths', collected=2, selected=2, selected_nodeids=['a','b'], execution=None)
    monkeypatch.setattr(m, 'census', lambda scopes: dict(snapshot))
    old = tmp_path / 'old.xml';new = tmp_path / 'new.xml'
    old.write_text('<testsuite><testcase name="a"/><testcase name="b"><skipped/></testcase></testsuite>')
    new.write_text('<testsuite><testcase name="a"><skipped/></testcase><testcase name="b"/></testsuite>')
    baseline = tmp_path / 'baseline.json';baseline.write_text(json.dumps(dict(snapshot, execution=m.read_junit(old))))
    assert m.main(['--junit', str(new), '--against', str(baseline)]) == 1
    result = json.loads(capsys.readouterr().out)
    assert any('PREVIOUSLY_PASSING_CASES_NOT_PASSING' in c for c in result['concerns'])
    assert result['execution']['execution_environment'] == 'UNBOUND_IMPORTED_JUNIT'

@pytest.mark.parametrize('count', [-1, True, '2', None])
def test_invalid_counts_baseline_cannot_pass(tmp_path, monkeypatch, count):
    m = tool('suite_count_census')
    now = dict(schema='suite-count-census-v2', scopes='configured_testpaths', collected=2, selected=2, selected_nodeids=['a','b'], execution=None)
    monkeypatch.setattr(m, 'census', lambda scopes: dict(now))
    baseline = tmp_path / 'baseline.json';baseline.write_text(json.dumps(dict(now, collected=count)))
    assert m.main(['--against', str(baseline)]) == 2
