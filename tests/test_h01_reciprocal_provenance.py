"""H01 additive provenance, with synthetic metadata and no tool/network execution."""
import ast
import copy
import importlib
import importlib.util
import os
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace, ModuleType

import pytest
from mamey import ref_completion as current

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'mamey/ref_completion.py'
FACADE_PACKAGE = '_h01_rggmci_standalone'


def load(path, name, monkeypatch):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


def standalone_owner(monkeypatch):
    package = ModuleType(FACADE_PACKAGE)
    package.__path__ = []
    monkeypatch.setitem(sys.modules, FACADE_PACKAGE, package)
    for dependency in ('_gbk_shim', 'csv_safety', 'residue_tiling', 'ziputil'):
        monkeypatch.setitem(sys.modules, FACADE_PACKAGE + '.' + dependency,
                            importlib.import_module('mamey.' + dependency))
    # Load capture readers in this package: relative imports and context state stay private.
    for dependency in ('archive_snapshot', 'source_context'):
        load(SOURCE.with_name(dependency + '.py'), FACADE_PACKAGE + '.' + dependency, monkeypatch)
    return load(SOURCE, FACADE_PACKAGE + '.ref_completion', monkeypatch)


@pytest.fixture(autouse=True)
def no_external_tools(monkeypatch):
    def refused(*args, **kwargs):
        pytest.fail('H01 must not launch an external tool')
    monkeypatch.setattr(subprocess, 'run', refused)


@pytest.fixture(params=['bundle', 'standalone'], ids=['bundle_owner', 'standalone_owner'])
def owner(request, monkeypatch):
    assert Path(current.__file__).resolve() == SOURCE.resolve()
    return current if request.param == 'bundle' else standalone_owner(monkeypatch)


@pytest.fixture
def package_owner(monkeypatch):
    return standalone_owner(monkeypatch)


@pytest.fixture
def preimage_owner(monkeypatch):
    # This optional comparison oracle is never needed for positive behavior tests.
    selected = os.environ.get('RGGMCI_H01_PREIMAGE')
    if not selected or not Path(selected).is_file() or not os.access(selected, os.R_OK):
        pytest.skip('optional preimage comparison: set RGGMCI_H01_PREIMAGE to a readable source file')
    return load(Path(selected), 'mamey._h01_optional_preimage', monkeypatch)


def fixture():
    protein = {'tag': 'p1', 'contig': 'partner', 'shown': 'SYN / partner', 'start': 100, 'end': 280,
               'strand': 1, 'contig_len': 1000, 'aa': 'X' * 60, 'kind': '', 'modular': False}
    core = {'contig': 'core', 'start': 0, 'end': 5000, 'edge': 'True'}
    ref = [{'i': 1, 'id': 'BGC9999001|1', 'name': 'dummy', 'product': '',
            'kind': 'biosynthetic', 'ks': 0, 'modular': False, 'aa': 'X' * 60}]
    hit = {'qseqid': ref[0]['id'], 'sseqid': 'p1', 'pident': 80.0, 'qcovhsp': 100.0,
           'bitscore': 100.0, 'sstart': 1, 'send': 60, 'qstart': 1, 'qend': 60, 'evalue': 1e-20}
    return {'p1': protein}, core, ref, [hit]


def rows_for(owner):
    prots, core, ref, hits = fixture()
    rows, _ = owner.search(ref, prots, [], hits, core)
    return rows, prots, hits, core, ref


def strip_additive(value):
    if isinstance(value, dict):
        return {k: strip_additive(v) for k, v in value.items()
                if k not in {'reciprocal_provenance', 'execution_state', 'execution_source'}}
    if isinstance(value, list):
        return [strip_additive(v) for v in value]
    return value


@pytest.mark.parametrize('scenario,expected', [
    ('no_finds', 'NOT_NEEDED'), ('no_database', 'NOT_RUN'), ('failed', 'FAILED'),
    ('success', 'RUN'), ('no_hits', 'RUN'), ('unjudged', 'UNJUDGED'), ('preflight', 'NOT_RUN')])
def test_reciprocal_states_without_preimage(owner, scenario, expected):
    rows, prots, hits, core, ref = rows_for(owner)
    assert rows[0]['reciprocal_best'] is True
    if scenario == 'no_finds':
        rows[0]['status'] = 'PRESENT_IN_CORE'
    calls = []
    def search(query, database, **kwargs):
        calls.append(kwargs)
        if scenario == 'failed':
            return {'ok': False, 'hits': [], 'reason': 'synthetic callback failure'}
        if scenario == 'preflight':
            return {'ok': False, 'hits': [], 'reason': 'no aligner',
                    'execution_state': 'NOT_RUN', 'execution_source': 'native_preflight'}
        return {'ok': True, 'hits': [] if scenario == 'no_hits' else [
            {'qseqid': 'p1', 'sseqid': 'BGC9999001|1', 'pident': 80, 'bitscore': 100}],
                'reason': 'synthetic result'}
    kwargs = {'mibig_db': None if scenario == 'no_database' else 'metadata_db', 'search': search, 'ref': ref}
    accession = 'not_a_mibig_accession' if scenario == 'unjudged' else 'BGC9999001'
    new_rows = copy.deepcopy(rows)
    new = owner.partner_checks(new_rows, prots, hits, core, accession, **kwargs)
    assert new_rows[0]['status'] == rows[0]['status']
    assert new_rows[0]['reciprocal_best'] is True
    provenance = new['reciprocal_provenance']
    assert provenance['forward_winner']['separate_search'] is False
    reverse = provenance['reverse_search']
    assert reverse['state'] == expected
    assert reverse['provider'] == 'supplied_callback'
    assert reverse['callback_invoked'] == bool(calls)
    assert reverse['query_count'] == (0 if scenario == 'no_finds' else 1)
    assert reverse['queries_with_mibig_accession_hits'] == (1 if scenario in {'success', 'unjudged'} else 0)
    if scenario in {'success', 'no_hits', 'unjudged'}:
        assert reverse['execution_source'] == 'supplied_search_callback'
        assert reverse['execution_state'] == 'REPORTED_SUCCESS'
    if calls:
        assert calls[0]['max_target_seqs'] == 0


def test_forward_winner_does_not_certify_reverse_execution(owner):
    rows, prots, hits, core, ref = rows_for(owner)
    def forbidden(*args, **kwargs):
        pytest.fail('no database must not call reverse search')
    checks = owner.partner_checks(rows, prots, hits, core, 'BGC9999001', search=forbidden, ref=ref)
    assert rows[0]['reciprocal_best'] is True
    assert checks['reciprocal_provenance']['reverse_search']['state'] == 'NOT_RUN'
    assert checks['reciprocal_provenance']['reverse_search']['execution_state'] == 'NOT_RUN'


@pytest.mark.parametrize('scenario,state', [('unavailable', 'NOT_RUN'), ('failure', 'FAILED'), ('success', 'RUN')])
def test_native_owner_execution_reporting_without_a_process(owner, monkeypatch, tmp_path, scenario, state):
    monkeypatch.setattr(owner, 'find_aligner', lambda *a: ('', '') if scenario == 'unavailable' else ('diamond', 'synthetic'))
    db = tmp_path / 'db.dmnd'; db.write_bytes(b'metadata-only')
    def align(*args, **kwargs):
        if scenario == 'failure': raise OSError('synthetic align failure')
        return []
    monkeypatch.setattr(owner, 'align', align)
    result = owner.search_mibig('unread_queries', db)
    assert result['execution_state'] == state
    assert result['ok'] == (scenario == 'success')


def setup_completion(owner, monkeypatch, root, reverse_failure=False):
    root.mkdir()
    (root / owner.DB_FAA).write_text('>metadata\nXXXX\n')
    prots, core, ref, forward_hits = fixture()
    regions = [{'bgc_id': 'BGC001', 'identity': 'SYN / core / region001 / BGC001', **core}]
    db = {'root': str(root), 'faa': str(root / owner.DB_FAA), 'dmnd': str(root / 'db.dmnd'),
          'genes': {'BGC9999001': ref}, 'compounds': {}, 'manifest': {}, 'lengths_kb': {}, 'protein_counts': {}}
    monkeypatch.setattr(owner, 'has_whole_genome_gbk', lambda path: True)
    monkeypatch.setattr(owner, 'find_aligner', lambda *args: ('diamond', 'synthetic'))
    monkeypatch.setattr(owner, 'load_mibig_db', lambda path: db)
    monkeypatch.setattr(owner, '_core_reference', lambda *args: {'BGC001': 'BGC9999001'})
    monkeypatch.setattr(owner, 'genome_from_zip', lambda *args: (prots, regions))
    calls = []
    def align(aligner, binary, query, subject, work, **kwargs):
        calls.append((query.name, kwargs))
        if query.name == 'references.faa': return copy.deepcopy(forward_hits)
        if reverse_failure: raise OSError('synthetic reverse failure')
        ids = [line[1:] for line in query.read_text().splitlines() if line.startswith('>')]
        return [{'qseqid': q, 'sseqid': 'BGC9999001|1', 'bitscore': 100, 'pident': 80} for q in ids]
    monkeypatch.setattr(owner, 'align', align)
    bgcs = [SimpleNamespace(bgc_id='BGC001', contig='core', start=0, end=5000)]
    return bgcs, calls


@pytest.mark.parametrize('failed', [False, True], ids=['cached_success', 'reverse_failure'])
def test_complete_provenance_and_legacy_fields_without_preimage(owner, monkeypatch, tmp_path, failed):
    bgcs, calls = setup_completion(owner, monkeypatch, tmp_path / 'db', failed)
    result = {'ranked_pairs': [{'bgc_a': 'BGC001', 'bgc_b': 'BGC002',
        'contig_a': 'core', 'contig_b': 'partner', 'rggmci_score': 17.25,
        'rggmci_confidence': 'HIGH_RG_GMCI_RESCUE'}]}
    owner.complete(result, 'unread.zip', bgcs, {}, {'BGC001'}, label='SYN',
                   mibig_db=tmp_path / 'db', work_dir=tmp_path / 'work')
    assert result['ranked_pairs'][0]['rggmci_score'] == 17.25
    assert result['ranked_pairs'][0]['rggmci_confidence'] == 'HIGH_RG_GMCI_RESCUE'
    assert result['ranked_pairs'][0]['completion_tier'] == 'FULL'
    block = result['reference_completion']
    reverse = block['cores'][0]['reciprocal_provenance']['reverse_search']
    assert reverse['state'] == ('FAILED' if failed else 'RUN')
    # complete selects a cached_search closure, not the search_mibig function.
    # Its callback metadata separately reports actual alignment/cache ownership.
    assert reverse['provider'] == 'supplied_callback'
    assert reverse['execution_source'] == ('alignment_workflow' if failed else 'sequence_cache')
    assert len(calls) == (3 if failed else 2)
    assert block['genes'][0]['reciprocal_best'] is True
    assert block['genes'][0]['status'] == 'MISSING_FOUND_CLEAR'
    assert block['cores'][0]['reciprocal_check'] == (
        'not run: diamond search failed: OSError' if failed else 'run')
    assert owner.table_payloads(block, 'synthetic_') == owner.table_payloads(strip_additive(block), 'synthetic_')


def test_native_default_provider_is_not_a_supplied_callback(owner, monkeypatch):
    rows, prots, hits, core, ref = rows_for(owner)
    monkeypatch.setattr(owner, 'find_aligner', lambda *args: ('', ''))
    result = owner.partner_checks(rows, prots, hits, core, 'BGC9999001', mibig_db='metadata_db', ref=ref)
    reverse = result['reciprocal_provenance']['reverse_search']
    assert reverse['provider'] == 'native_search_mibig'
    assert reverse['state'] == 'NOT_RUN'
    assert reverse['execution_source'] == 'native_preflight'


def test_shared_standalone_owner_is_verbatim_without_preimage(package_owner):
    tree = ast.parse((ROOT / 'packaging/rggmci/build_rggmci_package.py').read_text())
    verbatim = next(ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)
                    and any(isinstance(t, ast.Name) and t.id == 'VERBATIM' for t in n.targets))
    assert 'ref_completion.py' in verbatim
    assert Path(package_owner.__file__).read_bytes() == SOURCE.read_bytes()
    for dependency in ('archive_snapshot', 'source_context'):
        shared = sys.modules[FACADE_PACKAGE + '.' + dependency]
        assert shared.__package__ == FACADE_PACKAGE
        assert Path(shared.__file__).resolve() == SOURCE.with_name(dependency + '.py').resolve()
        assert shared is not importlib.import_module('mamey.' + dependency)


def test_module_aliases_restore_at_owned_context_teardown(monkeypatch):
    before = {k: v for k, v in sys.modules.items() if k.startswith(FACADE_PACKAGE)}
    with monkeypatch.context() as scoped:
        module = standalone_owner(scoped)
        assert sys.modules[FACADE_PACKAGE + '.ref_completion'] is module
    assert {k: v for k, v in sys.modules.items() if k.startswith(FACADE_PACKAGE)} == before


def test_collection_does_not_install_rggmci_facades(monkeypatch):
    before = {k: v for k, v in sys.modules.items() if k.startswith(('rggmci', FACADE_PACKAGE))}
    with monkeypatch.context() as scoped:
        load(Path(__file__), '_h01_collection_probe', scoped)
        assert {k: v for k, v in sys.modules.items() if k.startswith(('rggmci', FACADE_PACKAGE))} == before


def test_bundle_and_standalone_source_owner_outputs_match(package_owner):
    rows, prots, hits, core, ref = rows_for(current)
    def search(*args, **kwargs): return {'ok': False, 'hits': [], 'reason': 'synthetic callback failure'}
    a = current.partner_checks(copy.deepcopy(rows), prots, hits, core, 'BGC9999001', mibig_db='db', search=search, ref=ref)
    b = package_owner.partner_checks(copy.deepcopy(rows), prots, hits, core, 'BGC9999001', mibig_db='db', search=search, ref=ref)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


@pytest.mark.parametrize('with_database', [False, True])
def test_optional_preimage_partner_results(owner, preimage_owner, with_database):
    rows, prots, hits, core, ref = rows_for(owner)
    def search(*args, **kwargs):
        return {'ok': False, 'hits': [], 'reason': 'synthetic callback failure'}
    kwargs = {'mibig_db': 'db' if with_database else None, 'search': search, 'ref': ref}
    old_rows, new_rows = copy.deepcopy(rows), copy.deepcopy(rows)
    old = preimage_owner.partner_checks(old_rows, prots, hits, core, 'BGC9999001', **kwargs)
    new = owner.partner_checks(new_rows, prots, hits, core, 'BGC9999001', **kwargs)
    assert new_rows == old_rows and strip_additive(new) == old


@pytest.mark.parametrize('failed', [False, True], ids=['cached_success', 'reverse_failure'])
def test_optional_preimage_complete_and_tables(owner, preimage_owner, monkeypatch, tmp_path, failed):
    old_bgcs, old_calls = setup_completion(preimage_owner, monkeypatch, tmp_path / 'old_db', failed)
    new_bgcs, new_calls = setup_completion(owner, monkeypatch, tmp_path / 'new_db', failed)
    old_result = {'ranked_pairs': [{'bgc_a': 'BGC001', 'bgc_b': 'BGC002',
        'contig_a': 'core', 'contig_b': 'partner', 'rggmci_score': 17.25,
        'rggmci_confidence': 'HIGH_RG_GMCI_RESCUE'}]}
    new_result = copy.deepcopy(old_result)
    preimage_owner.complete(old_result, 'unread.zip', old_bgcs, {}, {'BGC001'}, label='SYN',
                            mibig_db=tmp_path / 'old_db', work_dir=tmp_path / 'old_work')
    owner.complete(new_result, 'unread.zip', new_bgcs, {}, {'BGC001'}, label='SYN',
                   mibig_db=tmp_path / 'new_db', work_dir=tmp_path / 'new_work')
    assert strip_additive(new_result) == old_result
    assert owner.table_payloads(new_result['reference_completion'], 'synthetic_') == (
        preimage_owner.table_payloads(old_result['reference_completion'], 'synthetic_'))
    assert len(new_calls) == len(old_calls)


def test_optional_preimage_emission_sites(preimage_owner):
    def sites(path):
        tree = ast.parse(path.read_text())
        return [ast.dump(n, include_attributes=False) for n in ast.walk(tree)
                if isinstance(n, ast.Call) and (
                    isinstance(n.func, ast.Name) and n.func.id in {'print', 'emit'} or
                    ast.unparse(n.func) in {'sys.stdout.write', 'sys.stderr.write'})]
    assert sites(SOURCE) == sites(Path(preimage_owner.__file__))
