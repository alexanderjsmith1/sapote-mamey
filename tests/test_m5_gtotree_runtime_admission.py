"""Synthetic transport/admission controls; no installed imports or native science.

The test-only authority pins a fabricated software tree. Production authority is
independently checked against the shipped reviewed manifest. Fake watched child
outputs test policy/route joins; they do not certify a real native environment.
"""
from pathlib import Path
from types import SimpleNamespace
import hashlib
import importlib
import io
import json
import sys
import pytest

TOOLS = Path(__file__).resolve().parents[1] / 'tools'
sys.path.insert(0, str(TOOLS))
rt = importlib.import_module('_gtotree_runtime')
versions = importlib.import_module('_gtotree_versions')
runner = importlib.import_module('run_planned_tree')
planner = importlib.import_module('plan_gtotree_iqtree')
gate = importlib.import_module('gtotree_execution_gate')
watch_owner = importlib.import_module('_release_validation')


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(data, encoding='utf-8')
    return path


def json_put(path, data):
    return put(path, json.dumps(data))


@pytest.fixture
def synthetic(tmp_path, monkeypatch):
    e = tmp_path / 'environment'
    s = tmp_path / 'editable'
    for p in (e / 'lib/python3.12/site-packages', e / 'lib/python3.12/lib-dynload', s / 'gtotree'):
        p.mkdir(parents=True)
    files = [put(e / 'bin/python', 'SYNTHETIC_INTERPRETER'),
             put(e / 'bin/gtotree', 'SYNTHETIC_LAUNCHER'),
             put(e / 'bin/muscle', 'SYNTHETIC_HELPER'),
             put(e / 'lib/python3.12/site-packages/runtime.so', 'SYNTHETIC_EXTENSION'),
             put(e / 'lib/python3.12/site-packages/synthetic.pth', '# SYNTHETIC_STARTUP\n'),
             put(s / 'gtotree/source.py', '# SYNTHETIC_EDITABLE_SOURCE\n')]
    for p in files[:3]: p.chmod(0o755)
    rows = []
    for p in files:
        key, root = ('environment', e) if e in p.parents else ('editable_source', s)
        logical = {'root': key, 'path': p.relative_to(root).as_posix()}
        rows.append(dict(logical, resolved=logical, sha256=rt.sha256(p), bytes=p.stat().st_size))
    origin = {'root': 'editable_source', 'path': 'gtotree/source.py'}
    module = {'module': 'gtotree', 'origin': origin,
              'distribution_metadata': {'root': 'environment', 'path': 'lib/python3.12/site-packages'},
              'loaded_version': None, 'distribution_version': '2.0.0', 'version_comparison': 'NO_MODULE_VERSION'}
    command = {'exit_code': 0, 'stdout_sha256': hashlib.sha256(b'').hexdigest(),
               'stderr_sha256': hashlib.sha256(b'').hexdigest()}
    m = {'schema': 'GTOTREE_REVIEWED_RUNTIME_V1', 'profile_id': rt.PROFILE_ID,
         'version': '2.0.0', 'thread_environment_keys': list(rt.THREAD_ENV_KEYS),
         'files': rows, 'source_python_roster': ['gtotree/source.py'],
         'startup_pth_roster': ['synthetic.pth'], 'absent_paths': [],
         'startup_hook_rosters': [{'root': {'root': 'environment', 'path': 'lib/python3.12'}, 'names': []}],
         'probe_worker_module_aliases': [], 'observed_loaded_module_roster': [dict(origin, module='gtotree', sha256=rt.sha256(files[-1]), bytes=files[-1].stat().st_size)],
         'modules': [module], 'commands': [['gtotree', '-v']], 'probe_command_hashes': [command]}
    manifest = json_put(tmp_path / 'manifest.json', m)
    monkeypatch.setattr(rt, 'APPROVED_MANIFEST_SHA256', rt.sha256(manifest))
    calls = []
    def watched(command, *, cwd, log, env, **budgets):
        calls.append((command, env, budgets))
        put(Path(log), 'SYNTHETIC_SOFTWARE_DIAGNOSTIC\n')
        out = Path(command[-1])
        runtime = {'loaded_file_closure': [{'module': 'gtotree', 'origin': str(files[-1]),
                    'sha256': rt.sha256(files[-1]), 'bytes': files[-1].stat().st_size}],
                   'modules': [dict(module, origin=str(files[-1]), distribution_metadata_path=str(e / 'lib/python3.12/site-packages'))],
                   'observed_hmm_threads_per_genome': [2, 2],
                   'thread_environment': {k: env[k] for k in rt.THREAD_ENV_KEYS},
                   'no_user_site': True, 'safe_path': True, 'dont_write_bytecode': True,
                   'executable_resolved': str(e / 'bin/python'), 'executable_sha256': rt.sha256(e / 'bin/python'),
                   'available_cpu_count_observed': 8}
        json_put(out / 'IMPORT_ORIGINS.json', runtime)
        json_put(out / 'WORKER_RESULT.json', {'status': 'PASS_SOFTWARE_PROBE_ONLY', 'commands': [command_result.copy()]})
        return {'exit_code': 0, 'stop_reason': None, 'cleanup_error': None}
    command_result = command
    monkeypatch.setattr(watch_owner, 'run_watched', watched)
    def prove(name='probe'):
        return rt.probe_runtime(manifest, e, s, tmp_path / name, e / 'bin/gtotree')
    return SimpleNamespace(e=e, s=s, files=files, manifest=manifest, m=m, calls=calls,
                           prove=prove, watched=watched, root=tmp_path)


def test_production_authority_is_exact_data_digest():
    assert rt.APPROVED_MANIFEST_SHA256 == 'b408acaab01b44f770d9c8f327df39ed12945477119b6a3ee97decc121370edd'
    assert rt.sha256(TOOLS / 'gtotree_runtime_profile.json') == rt.APPROVED_MANIFEST_SHA256


def test_default_v2_hold_and_existing_v1_contract():
    assert versions.resource_contract('2.0.0', 1, 1)['status'] == 'HOLD_UNVERIFIED_V2_RESOURCE_PROFILE'
    assert versions.resource_contract('1.8.19', 3, 2)['maximum_parallel_search_threads'] == 6
    with pytest.raises(ValueError, match='TYPED_PROOF'):
        versions.resource_contract('2.0.0', 1, 1, verified_runtime={'hmm_threads': 2})


def test_fresh_watched_proof_and_actual_requested_worker_math(synthetic):
    proof = synthetic.prove()
    for jobs, expected in [(1, 2), (2, 4)]:
        c = versions.resource_contract('2.0.0', 1, jobs, verified_runtime=proof, cpu_budget=4)
        assert c['maximum_parallel_search_threads'] == expected
        assert c['muscle_threads'] == 1
        assert c['native_execution_validated'] is False
    with pytest.raises(ValueError, match='CPU_BUDGET'):
        proof.contract('2.0.0', 1, 2, 3)
    command, env, budgets = synthetic.calls[0]
    assert command[1:4] == ['-B', '-s', '-P']
    assert {k: env[k] for k in rt.THREAD_ENV_KEYS} == dict.fromkeys(rt.THREAD_ENV_KEYS, '1')
    assert 'PYTHONPATH' not in env and 'PYTHONHOME' not in env
    assert budgets == {'rss_limit': 3_800_000_000, 'min_disk': 2_147_483_648, 'timeout': 900}
    assert rt.verified_interface(proof, synthetic.e / 'bin/gtotree')['verified_interface'] == 'PASS'
    with pytest.raises(ValueError, match='BINARY_BINDING'):
        rt.require_verified(proof, synthetic.e / 'bin/different')
    receipt = json.loads((synthetic.root / 'probe/RECEIPT.json').read_text())
    with pytest.raises(ValueError, match='TYPED_PROOF'):
        rt.require_verified(receipt)


@pytest.mark.parametrize('index', range(6))
def test_selected_source_startup_interpreter_helper_extension_drift_refuses(synthetic, index):
    synthetic.files[index].write_text('CHANGED_SYNTHETIC_SOFTWARE')
    with pytest.raises(ValueError, match='FILE_DRIFT'):
        synthetic.prove()
    assert synthetic.calls == []
    assert not (synthetic.root / 'probe').exists()


@pytest.mark.parametrize('kind', ['source', 'pth', 'hook', 'manifest', 'escape', 'occupied'])
def test_roster_authority_and_freshness_refusals_preserve_occupied(synthetic, kind):
    if kind == 'source': put(synthetic.s / 'gtotree/extra.py', '# synthetic extra\n')
    elif kind == 'pth': put(synthetic.e / 'lib/python3.12/site-packages/extra.pth', '# synthetic extra\n')
    elif kind == 'hook': put(synthetic.e / 'lib/python3.12/sitecustomize.py', '# synthetic extra\n')
    elif kind in ('manifest', 'escape'):
        m = synthetic.m.copy()
        m['hmm_workers_per_genome'] = 1
        if kind == 'escape': m['files'][0]['path'] = '../outside'
        json_put(synthetic.manifest, m)
    else: put(synthetic.root / 'probe/sentinel', 'SYNTHETIC_OCCUPIED')
    with pytest.raises((OSError, ValueError)):
        synthetic.prove()
    assert synthetic.calls == []
    if kind == 'occupied': assert (synthetic.root / 'probe/sentinel').read_text() == 'SYNTHETIC_OCCUPIED'


@pytest.mark.parametrize('mutation', ['origin', 'version', 'env', 'cpu', 'missing_roster', 'nonzero', 'stop', 'cleanup'])
def test_probe_refusals_are_diagnostic_not_fallback(synthetic, monkeypatch, mutation):
    def bad(command, **kw):
        receipt = synthetic.watched(command, **kw)
        path = Path(command[-1]) / 'IMPORT_ORIGINS.json'
        data = json.loads(path.read_text())
        if mutation == 'origin': data['loaded_file_closure'][0]['origin'] = str(synthetic.root / 'unapproved.py')
        elif mutation == 'version': data['modules'][0]['loaded_version'] = 'FAKE_VERSION'
        elif mutation == 'env': data['thread_environment']['OMP_THREAD_LIMIT'] = '8'
        elif mutation == 'cpu': data['available_cpu_count_observed'] = 1
        elif mutation == 'missing_roster': data['loaded_file_closure'] = []
        elif mutation == 'nonzero': receipt['exit_code'] = 1
        elif mutation == 'stop': receipt['stop_reason'] = 'TIME_LIMIT'
        else: receipt['cleanup_error'] = 'SYNTHETIC_CLEANUP_ERROR'
        json_put(path, data)
        return receipt
    monkeypatch.setattr(watch_owner, 'run_watched', bad)
    with pytest.raises(ValueError): synthetic.prove()
    receipt = json.loads((synthetic.root / 'probe/RECEIPT.json').read_text())
    assert receipt['status'] == 'FAILED' and receipt['native_job'] is False
    assert len(synthetic.calls) == 1


def test_post_probe_source_and_receipt_drift_invalidate_capability(synthetic):
    proof = synthetic.prove()
    put(synthetic.root / 'probe/IMPORT_ORIGINS.json', '{}')
    with pytest.raises(ValueError, match='DIAGNOSTIC_DRIFT|RECEIPT_CHAIN'): proof.revalidate()
    proof = synthetic.prove('second')
    synthetic.files[-1].write_text('# CHANGED_SYNTHETIC_SOURCE\n')
    with pytest.raises(ValueError, match='FILE_DRIFT'): proof.revalidate()


def test_no_implicit_import_optin_and_isolated_probe_write_boundary(synthetic):
    assert rt.runtime_from_arguments(SimpleNamespace(), synthetic.e / 'bin/gtotree') is None
    with pytest.raises(ValueError, match='OPTIONS_INCOMPLETE'):
        rt.runtime_from_arguments(SimpleNamespace(gtotree_runtime_manifest=str(synthetic.manifest)), synthetic.e / 'bin/gtotree')
    with pytest.raises(ValueError, match='DIAGNOSTIC_ISOLATION'):
        rt.probe_runtime(synthetic.manifest, synthetic.e, synthetic.s, synthetic.e / 'probe', synthetic.e / 'bin/gtotree')
    assert not (synthetic.e / 'probe').exists()


def test_watch_launch_bindings_env_and_failed_stop(synthetic, monkeypatch):
    proof = synthetic.prove()
    work = synthetic.root / 'execution'; work.mkdir()
    tool = put(synthetic.root / 'tool', 'SYNTHETIC_TOOL')
    selected = put(synthetic.root / 'selected', 'SYNTHETIC_INPUT')
    launch = rt.WatchedLaunch(proof, work, [selected], [tool], rss_limit=100, min_disk=0, timeout=3)
    log = io.StringIO()
    env = proof.native_environment()
    env['OMP_THREAD_LIMIT'] = '2'
    assert launch([str(tool)], log, env) == 125
    assert len(synthetic.calls) == 1  # only software proof; native child was not started
    env = proof.native_environment()
    def stop(command, **kw):
        put(kw['log'], 'SYNTHETIC_STOP\n')
        return {'exit_code': 0, 'stop_reason': 'TIME_LIMIT', 'cleanup_error': None}
    monkeypatch.setattr(watch_owner, 'run_watched', stop)
    assert launch([str(tool)], log, env) == 125
    assert launch.resource_failed is True
    selected.write_text('CHANGED_SYNTHETIC_INPUT')
    with pytest.raises(ValueError, match='EXECUTION_BINDING_DRIFT'): launch.revalidate()


def test_mapping_exact_roster_and_order(tmp_path):
    entries = ['/synthetic/q.fna', '/synthetic/o.fna']
    mapping = put(tmp_path / 'labels.tsv', 'q.fna\tSYNTHETIC_QUERY\no.fna\tSYNTHETIC_OUTGROUP\n')
    assert runner.mapped_tips(entries, mapping) == ['SYNTHETIC_QUERY', 'SYNTHETIC_OUTGROUP']
    put(mapping, 'q.fna\tSYNTHETIC_QUERY\n')
    with pytest.raises(ValueError, match='MAPPING_ROSTER'): runner.mapped_tips(entries, mapping)
    put(mapping, 'q.fna\tSYNTHETIC_QUERY\no.fna\tSYNTHETIC_QUERY\n')
    with pytest.raises(ValueError, match='MAPPING_IDENTITY'): runner.mapped_tips(entries, mapping)


def packet_for(synthetic):
    genome = put(synthetic.root / 'genome.fna', '>SYNTHETIC_REFERENCE\nACGT\n')
    hmm = put(synthetic.root / 'model.hmm', 'NAME SYNTHETIC_MODEL\n')
    return {'run_id': 'SYNTHETIC_RUN', 'gtotree': {'path': str(synthetic.e / 'bin/gtotree'),
             'version': '2.0.0', 'sha256': rt.sha256(synthetic.e / 'bin/gtotree')},
            'hmm': {'path': str(hmm), 'sha256': rt.sha256(hmm)}, 'max_concurrent_jobs': 1,
            'working_directory': str(synthetic.root / 'work'), 'output_directory': str(synthetic.root / 'out'),
            'panel': [{'tip': 'SYNTHETIC_REFERENCE', 'genome_path': str(genome), 'sha256': rt.sha256(genome)}]}


def test_gate_default_v2_hold_and_typed_common_admission(synthetic):
    packet = packet_for(synthetic)
    with pytest.raises(ValueError, match='TYPED_PROOF'): gate.validate(packet, synthetic.root)
    proof = synthetic.prove()
    answer = gate.validate(packet, synthetic.root, verified_runtime=proof)
    assert answer['status'] == 'GTOTREE_EXECUTION_GATE_PASS'
    assert answer['resource_contract']['maximum_parallel_search_threads'] == 2
    packet['gtotree']['version'] = '1.8.19'
    assert gate.validate(packet, synthetic.root)['status'] == 'GTOTREE_EXECUTION_GATE_PASS'


def make_plan(synthetic, monkeypatch, *, threads=1, cpu_budget=4):
    proof = synthetic.prove()
    monkeypatch.setattr(rt, 'runtime_from_arguments', lambda a, binary: proof)
    iq = put(synthetic.root / 'iqtree', 'SYNTHETIC_IQTREE'); iq.chmod(0o755)
    monkeypatch.setattr(planner, 'probe_toolchain', lambda g, i, verified_runtime=None:
        {'gtotree': rt.verified_interface(proof, g),
         'iqtree': {'status': 'PRESENT', 'path': str(iq), 'help_contract': 'PASS'}, 'helpers': {}})
    rows = ['role\tquery_id\tstrain_id\tlabel\tassembly_path']
    for role, label, sequence in [('QUERY', 'SYNTHETIC_QUERY', 'ACGT'),
                                  ('REFERENCE', 'SYNTHETIC_REFERENCE', 'CCGT'),
                                  ('OUTGROUP', 'SYNTHETIC_OUTGROUP', 'GCGT')]:
        genome = put(synthetic.root / (label + '.fna'), '>' + label + '\n' + sequence + '\n')
        rows.append('\t'.join([role, 'SYNTHETIC_QUERY', label, label, str(genome)]))
    panel = put(synthetic.root / 'panel.tsv', '\n'.join(rows) + '\n')
    hmm = put(synthetic.root / 'model.hmm', 'NAME SYNTHETIC_MODEL\n')
    args = planner.build_parser().parse_args(['plan', '--panel-tsv', str(panel), '--workspace', str(synthetic.root),
        '--run-id', 'SYNTHETIC_PLAN', '--hmm', str(hmm), '--references-per-query', '1',
        '--threads-per-tree', str(threads), '--max-concurrent-cores', str(cpu_budget),
        '--gtotree-bin', str(synthetic.e / 'bin/gtotree'), '--iqtree-bin', str(iq),
        '--gtotree-runtime-manifest', str(synthetic.manifest), '--gtotree-runtime-environment', str(synthetic.e),
        '--gtotree-runtime-source', str(synthetic.s), '--gtotree-runtime-probe-dir', str(synthetic.root / 'unused')])
    assert planner.plan(args) == 0
    return synthetic.root / 'runs/SYNTHETIC_PLAN', proof, iq


def test_actual_planner_generates_governed_route_with_phase_budget_and_roles(synthetic, monkeypatch):
    root, proof, iq = make_plan(synthetic, monkeypatch)
    manifest = json.loads((root / 'RUN_MANIFEST.json').read_text())
    assert manifest['resource_policy']['max_concurrent_trees'] == 2
    assert manifest['resource_policy']['phase_requested_threads'] == 2
    command = (root / 'COMMAND.sh').read_text()
    assert 'run_planned_tree.py' in command and '--plan-dir' in command and '--mapping-file' in command
    assert '${GTOTREE_RUNTIME_PROBE_DIR:?' in command
    assert '--query-tips SYNTHETIC_QUERY' in command and '--outgroup SYNTHETIC_OUTGROUP' in command
    assert ' -f ' not in command  # no direct native GToTree bypass
    assert '"$@"' in command  # explicit execution approval remains required


def test_actual_runner_refuses_unapproved_plan_without_native_child(synthetic, monkeypatch):
    root, proof, iq = make_plan(synthetic, monkeypatch)
    args = ['--approved', '--genome-list', str(root / 'input_view/genomes_absolute.txt'),
        '--mapping-file', str(root / 'input_view/labels.tsv'), '--plan-dir', str(root),
        '--workdir', str(root / 'outputs/governed_run'), '--outgroup', 'SYNTHETIC_OUTGROUP',
        '--query-tips', 'SYNTHETIC_QUERY', '--hmm', str(root / json.loads((root / 'RUN_MANIFEST.json').read_text())['hmm']['object_relpath']),
        '--threads', '1', '--parallel', '1', '--gtotree-bin', str(synthetic.e / 'bin/gtotree'), '--iqtree-bin', str(iq),
        '--gtotree-runtime-manifest', str(synthetic.manifest), '--gtotree-runtime-environment', str(synthetic.e),
        '--gtotree-runtime-source', str(synthetic.s)]
    assert runner.main(args) == 3
    assert len(synthetic.calls) == 1
    assert not (root / 'outputs/governed_run').exists()


@pytest.mark.parametrize('drop_query', [False, True])
def test_governed_runner_actual_route_retains_mapping_completion_and_optional_ani(synthetic, monkeypatch, drop_query):
    root, proof, iq = make_plan(synthetic, monkeypatch)
    state = json.loads((root / 'RUN_STATE.json').read_text()); state['approved'] = True
    json_put(root / 'RUN_STATE.json', state)
    manifest = json.loads((root / 'RUN_MANIFEST.json').read_text())
    ani = put(synthetic.root / 'fastANI', 'SYNTHETIC_FASTANI')
    queries = put(synthetic.root / 'ani_queries.txt', str(synthetic.root / 'SYNTHETIC_QUERY.fna') + '\n')
    references = put(synthetic.root / 'ani_refs.txt', str(synthetic.root / 'SYNTHETIC_REFERENCE.fna') + '\n')
    original_resolve = runner._resolve
    monkeypatch.setattr(runner, '_resolve', lambda names: str(ani) if names == ['fastANI'] else original_resolve(names))
    native = []
    def native_watch(command, **kw):
        native.append(command)
        put(kw['log'], 'SYNTHETIC_NATIVE_DIAGNOSTIC\n')
        assert all(kw['env'][k] == '1' for k in rt.THREAD_ENV_KEYS)
        if command[0] == str(synthetic.e / 'bin/gtotree'):
            assert command[command.index('-j') + 1] == '1'
            assert command[command.index('-M') + 1] == '1'
            assert '-N' in command and '-n' not in command
            out = Path(command[command.index('-o') + 1])
            tips = ['SYNTHETIC_QUERY', 'SYNTHETIC_REFERENCE', 'SYNTHETIC_OUTGROUP']
            if drop_query: tips.remove('SYNTHETIC_QUERY')
            put(out / 'aligned-SCGs.faa', ''.join('>' + t + '\nACDE\n' for t in tips))
        elif command[0] == str(iq) and '-s' in command:
            prefix = Path(command[command.index('--prefix') + 1])
            tree = '((SYNTHETIC_QUERY:0.1,SYNTHETIC_REFERENCE:0.1)99/100:0.1,SYNTHETIC_OUTGROUP:0.2);\n'
            put(Path(str(prefix) + '.treefile'), tree)
            put(Path(str(prefix) + '.contree'), tree)
            put(Path(str(prefix) + '.log'), 'Total wall-clock time: 1 second\n')
        elif command[0] == str(ani) and '--ql' in command:
            put(Path(command[command.index('-o') + 1]), 'SYNTHETIC_QUERY\tSYNTHETIC_REFERENCE\t99\t1\t1\n')
        return {'exit_code': 0, 'stop_reason': None, 'cleanup_error': None}
    monkeypatch.setattr(watch_owner, 'run_watched', native_watch)
    qc_calls = []
    # Native science/QC algorithms are outside this transport test; existing QC tests stay intact.
    def unchanged_qc(treefile, outgroup, **kw):
        qc_calls.append((treefile, outgroup, kw))
        assert isinstance(kw['launch'], rt.WatchedLaunch)
        return True, ['SYNTHETIC_QC_TRANSPORT_CONTROL']
    monkeypatch.setattr(runner, 'hard_tree_qc', unchanged_qc)
    work = root / 'outputs/governed_run'
    args = ['--approved', '--genome-list', str(root / 'input_view/genomes_absolute.txt'),
        '--mapping-file', str(root / 'input_view/labels.tsv'), '--plan-dir', str(root),
        '--workdir', str(work), '--outgroup', 'SYNTHETIC_OUTGROUP', '--query-tips', 'SYNTHETIC_QUERY',
        '--hmm', str(root / manifest['hmm']['object_relpath']), '--threads', '1', '--parallel', '1',
        '--gtotree-bin', str(synthetic.e / 'bin/gtotree'), '--iqtree-bin', str(iq),
        '--gtotree-runtime-manifest', str(synthetic.manifest), '--gtotree-runtime-environment', str(synthetic.e),
        '--gtotree-runtime-source', str(synthetic.s), '--ani-refs', str(references), '--ani-queries', str(queries)]
    rc = runner.main(args)
    status = json.loads((work / 'run_status.json').read_text())
    if drop_query:
        assert rc == 7 and status['status'] == 'QUERY_TIP_DROPPED'
        assert not qc_calls
        assert not any('--ql' in c or '-s' in c for c in native)
    else:
        assert rc == 0 and status['status'] == 'DONE'
        assert status['tip_retention'] == 'TIPS_RETAINED'
        assert status['fastani_stage']['status'] == 'DONE'
        assert len(qc_calls) == 1
        assert any(c == [str(ani), '--version'] for c in native)
        bindings = json.loads((work / 'EXECUTION_BINDINGS.json').read_text())['files']
        assert str(ani) in bindings and str(queries) in bindings and str(references) in bindings
        assert status['gtotree_resource_contract']['maximum_parallel_search_threads'] == 2
        assert len(list(work.glob('watch_*.json'))) == len(native)


def test_runner_v2_default_hold_starts_no_analysis(synthetic, monkeypatch):
    genome = put(synthetic.root / 'input.fna', '>SYNTHETIC_REFERENCE\nACGT\n')
    genomes = put(synthetic.root / 'genomes.txt', str(genome) + '\n')
    monkeypatch.setattr(runner, '_resolve', lambda names: str(synthetic.e / 'bin/gtotree'))
    monkeypatch.setattr(runner, 'gtotree_probe', lambda binary: {'verified_interface': 'PASS',
                        'version': '2.0.0', 'major': 2})
    monkeypatch.setattr(runner, 'run', lambda *a, **kw: pytest.fail('native bypass'))
    work = synthetic.root / 'native'
    assert runner.main(['--approved', '--genome-list', str(genomes), '--workdir', str(work),
                        '--outgroup', 'input']) == 3
    assert not work.exists() and synthetic.calls == []


def test_gate_cli_explicit_optin_calls_shared_validator(synthetic, monkeypatch):
    packet = packet_for(synthetic)
    path = json_put(synthetic.root / 'packet.json', packet)
    proof = synthetic.prove()
    seen = []
    def selected(args, binary):
        seen.append((args.gtotree_runtime_probe_dir, binary))
        return proof
    monkeypatch.setattr(rt, 'runtime_from_arguments', selected)
    assert gate.main([str(path), '--root', str(synthetic.root),
        '--gtotree-runtime-probe-dir', str(synthetic.root / 'explicit_next_probe')]) == 0
    assert seen == [(str(synthetic.root / 'explicit_next_probe'), packet['gtotree']['path'])]
