"""Exact reviewed GToTree runtime admission; no model or biological authorization.

Caller data cannot approve a profile. A fresh watched software-only probe produces
an in-process capability. Serialized receipts are diagnostic evidence only.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
from pathlib import Path

APPROVED_MANIFEST_SHA256 = 'b408acaab01b44f770d9c8f327df39ed12945477119b6a3ee97decc121370edd'
PROFILE_ID = 'editable_pyhmmer_fixed2_v1'
THREAD_ENV_KEYS = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS',
                   'NUMEXPR_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'OMP_THREAD_LIMIT')
_RESOURCE_PASS = ('PASS_EXPLICIT_CLI_RESOURCE_BOUND', 'PASS_SOURCE_BOUND_RESOURCE_PROFILE')
_SEAL = object()

class RuntimeRefused(ValueError):
    """A failed software binding cannot fall back to version-only admission."""


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def _json_new(path, value):
    with Path(path).open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2, sort_keys=True)
        f.write('\n')


def _no_symlink(path):
    p = Path(os.path.abspath(path))
    if any(q.is_symlink() for q in (p, *p.parents)):
        raise RuntimeRefused('GTOTREE_RUNTIME_SYMLINK_PATH')
    return p


def _roots(environment, editable_source):
    roots = {k: _no_symlink(v).resolve(strict=True) for k, v in
             [('environment', environment), ('editable_source', editable_source)]}
    x, y = roots.values()
    if not x.is_dir() or not y.is_dir() or x == y or x in y.parents or y in x.parents:
        raise RuntimeRefused('GTOTREE_RUNTIME_ROOT_ISOLATION')
    return roots


def _path(item, roots):
    if not isinstance(item, dict) or item.get('root') not in roots:
        raise RuntimeRefused('GTOTREE_RUNTIME_LOGICAL_ROOT')
    rel = Path(item.get('path', ''))
    if not rel.parts or rel.is_absolute() or any(x in ('.', '..') for x in rel.parts):
        raise RuntimeRefused('GTOTREE_RUNTIME_LOGICAL_PATH')
    p = roots[item['root']] / rel
    if roots[item['root']] not in p.resolve().parents:
        raise RuntimeRefused('GTOTREE_RUNTIME_PATH_ESCAPE')
    return p


def validate_manifest(manifest_path, environment, editable_source):
    """Read-only. A caller's new JSON/profile/CPU assertion is never authority."""
    p = _no_symlink(manifest_path)
    if not p.is_file() or p.stat().st_size > 1_000_000 or sha256(p) != APPROVED_MANIFEST_SHA256:
        raise RuntimeRefused('GTOTREE_RUNTIME_UNAPPROVED_MANIFEST')
    m = json.loads(p.read_text(encoding='utf-8'))
    if (m.get('schema') != 'GTOTREE_REVIEWED_RUNTIME_V1' or
            m.get('profile_id') != PROFILE_ID or m.get('version') != '2.0.0' or
            tuple(m.get('thread_environment_keys', ())) != THREAD_ENV_KEYS):
        raise RuntimeRefused('GTOTREE_RUNTIME_PROFILE')
    roots = _roots(environment, editable_source)
    if len(m['files']) > 2000:
        raise RuntimeRefused('GTOTREE_RUNTIME_PIN_LIMIT')
    for row in m['files']:
        file = _path(row, roots)
        if (file.resolve(strict=True) != _path(row['resolved'], roots) or
                not file.is_file() or file.stat().st_size != row['bytes'] or
                sha256(file) != row['sha256']):
            raise RuntimeRefused('GTOTREE_RUNTIME_FILE_DRIFT')
        # Only the exact reviewed final symlink (e.g. bin/python) may resolve.
        for ancestor in file.parents:
            if ancestor == roots[row['root']]:
                break
            if ancestor.is_symlink():
                raise RuntimeRefused('GTOTREE_RUNTIME_ANCESTOR_SYMLINK')
    source = roots['editable_source']
    roster = []
    for file in (source / 'gtotree').rglob('*.py'):
        if file.is_symlink() or len(roster) >= 500:
            raise RuntimeRefused('GTOTREE_RUNTIME_SOURCE_ROSTER_LIMIT')
        roster.append(file.relative_to(source).as_posix())
    if sorted(roster) != sorted(m['source_python_roster']):
        raise RuntimeRefused('GTOTREE_RUNTIME_SOURCE_ROSTER_DRIFT')
    sp = roots['environment'] / 'lib/python3.12/site-packages'
    if sorted(x.name for x in sp.glob('*.pth')) != sorted(m['startup_pth_roster']):
        raise RuntimeRefused('GTOTREE_RUNTIME_STARTUP_DRIFT')
    for row in m['startup_hook_rosters']:
        names = sorted(x.name for x in _path(row['root'], roots).iterdir()
                       if x.name.lower().startswith(('sitecustomize', 'usercustomize')))
        if names != sorted(row['names']):
            raise RuntimeRefused('GTOTREE_RUNTIME_STARTUP_DRIFT')
    for item in m['absent_paths']:
        p = _path(item, roots)
        if p.exists() or p.is_symlink():
            raise RuntimeRefused('GTOTREE_RUNTIME_STARTUP_DRIFT')
    return m, roots


def _environment(roots, attempt):
    return {'PATH': str(roots['environment'] / 'bin') + ':/usr/bin:/bin',
            'HOME': str(attempt / 'home'), 'TMPDIR': str(attempt / 'tmp'),
            'XDG_CACHE_HOME': str(attempt / 'cache'), 'LANG': 'C', 'LC_ALL': 'C',
            'PYTHONNOUSERSITE': '1', 'PYTHONSAFEPATH': '1',
            'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONHASHSEED': '0',
            'PYTHONPYCACHEPREFIX': str(attempt / 'cache/pycache'),
            **{key: '1' for key in THREAD_ENV_KEYS}}


def resource_pass(contract):
    return contract.get('status') in _RESOURCE_PASS


class VerifiedRuntime:
    """In-process proof, deliberately not deserializable from a receipt dict."""
    __slots__ = ('_seal', '_manifest', '_roots', '_binary', '_receipt', '_receipt_sha',
                 '_environment', '_cpu_count')

    def __init__(self, seal, manifest, roots, binary, receipt, environment, cpu_count):
        if seal is not _SEAL:
            raise RuntimeRefused('GTOTREE_RUNTIME_TYPED_PROOF_REQUIRED')
        self._seal = seal
        self._manifest = manifest
        self._roots = roots
        self._binary = Path(binary).absolute()
        self._receipt = receipt
        self._receipt_sha = sha256(receipt)
        self._environment = environment
        self._cpu_count = cpu_count

    def revalidate(self, binary=None):
        if self._seal is not _SEAL or sha256(self._receipt) != self._receipt_sha:
            raise RuntimeRefused('GTOTREE_RUNTIME_PROOF_DRIFT')
        validate_manifest(self._manifest, **self._roots)
        receipt = json.loads(self._receipt.read_text())
        for name, expected in receipt['diagnostic_pins'].items():
            if sha256(self._receipt.parent / name) != expected:
                raise RuntimeRefused('GTOTREE_RUNTIME_DIAGNOSTIC_DRIFT')
        for p, expected in receipt['code_pins'].items():
            if sha256(p) != expected:
                raise RuntimeRefused('GTOTREE_RUNTIME_COORDINATOR_DRIFT')
        for name, key in [('RESOURCE_RECEIPT.json', 'resource_receipt_sha256'),
                          ('IMPORT_ORIGINS.json', 'origins_sha256'),
                          ('WORKER_RESULT.json', 'worker_result_sha256')]:
            if sha256(self._receipt.parent / name) != receipt[key]:
                raise RuntimeRefused('GTOTREE_RUNTIME_RECEIPT_CHAIN_DRIFT')
        if binary is not None and Path(binary).absolute() != self._binary:
            raise RuntimeRefused('GTOTREE_RUNTIME_BINARY_BINDING')

    def contract(self, version, threads, jobs, cpu_budget=None):
        self.revalidate()
        if str(version).strip() not in ('2.0.0', 'GToTree v2.0.0'):
            raise RuntimeRefused('GTOTREE_RUNTIME_VERSION_BINDING')
        for value in (threads, jobs):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise RuntimeRefused('GTOTREE_RUNTIME_RESOURCE_INTEGER')
        cpu_budget = 4 if cpu_budget is None else cpu_budget
        phase = max(2 * jobs, jobs * threads)
        if (isinstance(cpu_budget, bool) or not isinstance(cpu_budget, int) or
                cpu_budget < phase or phase > self._cpu_count):
            raise RuntimeRefused('GTOTREE_RUNTIME_CPU_BUDGET')
        return {'status': 'PASS_SOURCE_BOUND_RESOURCE_PROFILE', 'profile': '2.0.x',
                'jobs': jobs, 'muscle_threads': threads, 'hmm_threads': 2,
                'maximum_parallel_search_threads': 2 * jobs,
                'maximum_parallel_muscle_threads': jobs * threads, 'phase_requested_threads': phase,
                'requested_threads_per_tree': threads, 'hmm_control': 'SOURCE_FIXED_PYHMMER_CPUS',
                'source_profile': PROFILE_ID, 'manifest_sha256': APPROVED_MANIFEST_SHA256,
                'probe_receipt_sha256': self._receipt_sha, 'cpu_count_observed': self._cpu_count,
                'cpu_budget': cpu_budget, 'native_execution_validated': False,
                'scope': 'Requested HMM workers; not total CPU/OS threads or model/biological validation.'}

    def native_environment(self):
        self.revalidate()
        return dict(self._environment)


def require_verified(value, binary=None):
    if type(value) is not VerifiedRuntime:
        raise RuntimeRefused('GTOTREE_RUNTIME_TYPED_PROOF_REQUIRED')
    value.revalidate(binary)
    return value


def probe_runtime(manifest_path, environment, editable_source, probe_dir, binary,
                  *, rss_limit=3_800_000_000, min_disk=2_147_483_648, timeout=900):
    """Explicit fresh software-only import/CLI probe under the existing watcher."""
    import _release_validation
    run_watched = _release_validation.run_watched
    if (isinstance(rss_limit, bool) or not isinstance(rss_limit, int) or rss_limit <= 0 or
            isinstance(min_disk, bool) or not isinstance(min_disk, int) or min_disk < 0 or
            not math.isfinite(timeout) or timeout <= 0):
        raise RuntimeRefused('GTOTREE_RUNTIME_WATCH_BUDGET')
    m, roots = validate_manifest(manifest_path, environment, editable_source)
    if not isinstance(binary, (str, os.PathLike)):
        raise RuntimeRefused('GTOTREE_RUNTIME_BINARY_BINDING')
    selected = Path(binary).absolute()
    if selected not in [roots['environment'] / 'bin' / x for x in ('gtotree', 'GToTree')]:
        raise RuntimeRefused('GTOTREE_RUNTIME_BINARY_BINDING')
    attempt = _no_symlink(probe_dir)
    if not attempt.parent.is_dir() or attempt.exists():
        raise RuntimeRefused('GTOTREE_RUNTIME_FRESH_PROBE_DIRECTORY')
    for root in (*roots.values(), Path(__file__).resolve().parent.parent):
        if attempt == root or root in attempt.parents or attempt in root.parents:
            raise RuntimeRefused('GTOTREE_RUNTIME_DIAGNOSTIC_ISOLATION')
    attempt.mkdir(exist_ok=False)
    for rel in ('cwd', 'home', 'tmp', 'cache'):
        (attempt / rel).mkdir()
    env = _environment(roots, attempt)
    worker = Path(__file__).with_name('_gtotree_runtime_probe.py')
    code_pins = {str(p.resolve()): sha256(p) for p in (Path(__file__), worker, Path(_release_validation.__file__))}
    worker_sha = sha256(worker)
    config = {'environment': str(roots['environment']), 'editable_source': str(roots['editable_source']),
              'thread_environment_keys': list(THREAD_ENV_KEYS), 'commands': m['commands']}
    _json_new(attempt / 'REQUEST.json', config)
    _json_new(attempt / 'BEFORE.json', {'manifest_sha256': APPROVED_MANIFEST_SHA256,
                                      'worker_sha256': worker_sha, 'binary': str(selected)})
    watch = None
    error = None
    try:
        watch = run_watched([str(roots['environment'] / 'bin/python'), '-B', '-s', '-P',
                             str(worker), str(attempt / 'REQUEST.json'), str(attempt)],
                            cwd=attempt / 'cwd', log=attempt / 'watch.log', env=env,
                            rss_limit=rss_limit, min_disk=min_disk, timeout=timeout)
        _json_new(attempt / 'RESOURCE_RECEIPT.json', watch)
        if watch.get('exit_code') != 0 or watch.get('stop_reason') or watch.get('cleanup_error'):
            raise RuntimeRefused('GTOTREE_RUNTIME_PROBE_FAILED')
        origins = json.loads((attempt / 'IMPORT_ORIGINS.json').read_text())
        result = json.loads((attempt / 'WORKER_RESULT.json').read_text())
        validate_manifest(manifest_path, environment, editable_source)
        expected = {(str(_path(r['resolved'], roots)), r['sha256'], r['bytes']) for r in m['files']}
        for row in origins['loaded_file_closure']:
            if row['module'] in m['probe_worker_module_aliases'] and Path(row['origin']) == worker.resolve():
                if row['sha256'] != sha256(worker):
                    raise RuntimeRefused('GTOTREE_RUNTIME_WORKER_DRIFT')
            elif (row['origin'], row['sha256'], row['bytes']) not in expected:
                raise RuntimeRefused('GTOTREE_RUNTIME_LOADED_ORIGIN_DRIFT')
        observed = sorted((row['module'], row['origin'], row['sha256'], row['bytes'])
                          for row in origins['loaded_file_closure'] if row['module'] not in m['probe_worker_module_aliases'])
        if sorted(row['module'] for row in origins['loaded_file_closure'] if row['module'] in m['probe_worker_module_aliases']) != sorted(m['probe_worker_module_aliases']):
            raise RuntimeRefused('GTOTREE_RUNTIME_WORKER_ALIAS_DRIFT')
        wanted_roster = sorted((row['module'], str(_path(row, roots)), row['sha256'], row['bytes'])
                               for row in m['observed_loaded_module_roster'])
        if observed != wanted_roster or len(origins['modules']) != len(m['modules']):
            raise RuntimeRefused('GTOTREE_RUNTIME_LOADED_ROSTER_DRIFT')
        for wanted in m['modules']:
            actual = next((r for r in origins['modules'] if r['module'] == wanted['module']), None)
            if actual is None or any(actual[k] != wanted[k] for k in
                    ('loaded_version', 'distribution_version', 'version_comparison')) or (
                    actual['origin'] != str(_path(wanted['origin'], roots)) or
                    actual['distribution_metadata_path'] != str(_path(wanted['distribution_metadata'], roots))):
                raise RuntimeRefused('GTOTREE_RUNTIME_VERSION_OR_ORIGIN_DRIFT')
        if (origins['observed_hmm_threads_per_genome'] != [2, 2] or
                origins['thread_environment'] != {k: '1' for k in THREAD_ENV_KEYS} or
                not all(origins[k] for k in ('no_user_site', 'safe_path', 'dont_write_bytecode')) or
                origins['executable_resolved'] != str((roots['environment'] / 'bin/python').resolve()) or
                origins['executable_sha256'] != sha256(roots['environment'] / 'bin/python') or
                not isinstance(origins['available_cpu_count_observed'], int) or
                origins['available_cpu_count_observed'] < 2):
            raise RuntimeRefused('GTOTREE_RUNTIME_CONTEXT_DRIFT')
        got = [{k: row[k] for k in ('exit_code', 'stdout_sha256', 'stderr_sha256')}
               for row in result['commands']]
        if result['status'] != 'PASS_SOFTWARE_PROBE_ONLY' or got != m['probe_command_hashes']:
            raise RuntimeRefused('GTOTREE_RUNTIME_CLI_DRIFT')
        if any(sha256(p) != h for p,h in code_pins.items()):
            raise RuntimeRefused('GTOTREE_RUNTIME_WORKER_DRIFT')
    except Exception as exc:
        error = type(exc).__name__ + ': ' + str(exc)
    try:
        validate_manifest(manifest_path, environment, editable_source)
        stable = True
    except Exception as exc:
        stable = False
        error = error or type(exc).__name__ + ': ' + str(exc)
    _json_new(attempt / 'RECEIPT.json', {'status': 'FAILED' if error else 'PASS_SOFTWARE_PROBE_ONLY',
        'error': error, 'source_stable': stable, 'code_pins': code_pins,
        'diagnostic_pins': {p.name: sha256(p) for p in attempt.iterdir() if p.is_file()},
        'manifest_sha256': APPROVED_MANIFEST_SHA256,
        'resource_receipt_sha256': sha256(attempt / 'RESOURCE_RECEIPT.json') if watch else None,
        'origins_sha256': sha256(attempt / 'IMPORT_ORIGINS.json') if (attempt / 'IMPORT_ORIGINS.json').is_file() else None,
        'worker_result_sha256': sha256(attempt / 'WORKER_RESULT.json') if (attempt / 'WORKER_RESULT.json').is_file() else None,
        'native_job': False, 'model_validation': False, 'scientific_validation': False})
    if error:
        raise RuntimeRefused(error)
    return VerifiedRuntime(_SEAL, str(Path(manifest_path).absolute()), roots, selected,
                           attempt / 'RECEIPT.json', env, origins['available_cpu_count_observed'])


def add_runtime_arguments(parser):
    parser.add_argument('--gtotree-runtime-manifest', help='exact policy-approved logical software manifest')
    parser.add_argument('--gtotree-runtime-environment', help='caller-selected installed environment root')
    parser.add_argument('--gtotree-runtime-source', help='caller-selected editable source root')
    parser.add_argument('--gtotree-runtime-probe-dir', help='explicit fresh diagnostic directory; opts into watched software imports')
    parser.add_argument('--gtotree-rss-limit', type=int, default=3_800_000_000)
    parser.add_argument('--gtotree-min-disk', type=int, default=2_147_483_648)
    parser.add_argument('--gtotree-timeout', type=float, default=900)
    parser.add_argument('--gtotree-cpu-budget', type=int, default=4,
                        help='requested phase workers budget, checked against observed available CPUs')


def runtime_from_arguments(args, binary):
    values = [getattr(args, 'gtotree_runtime_' + k, None) for k in
              ('manifest', 'environment', 'source', 'probe_dir')]
    if not any(values):
        return None
    if not all(values):
        raise RuntimeRefused('GTOTREE_RUNTIME_OPTIONS_INCOMPLETE')
    return probe_runtime(*values[:3], values[3], binary,
        rss_limit=getattr(args, 'gtotree_rss_limit', 3_800_000_000),
        min_disk=getattr(args, 'gtotree_min_disk', 2_147_483_648),
        timeout=getattr(args, 'gtotree_timeout', 900))


def verified_interface(runtime, binary):
    require_verified(runtime, binary)
    from _gtotree_versions import profile
    selected = profile('2.0.0')
    return {'status': 'PRESENT', 'path': str(binary), 'version': 'GToTree v2.0.0',
            'normalized_version': '2.0.0', 'verified_interface': 'PASS',
            'help_contract': 'PASS', 'version_exit': 0, 'help_exit': 0,
            'probe_scope': 'fresh watched software/import/version/help proof', **selected}


class WatchedLaunch:
    """Serial native children; exact selected inputs/tools rechecked each phase.

    This does not audit all shared libraries or turn a requested phase-worker
    count into a kernel CPU limit. Each child tree has its own finite watch.
    """
    def __init__(self, runtime, workdir, inputs, executables, *, rss_limit, min_disk, timeout):
        require_verified(runtime)
        self.runtime = runtime
        self.root = Path(workdir)
        self.rows = {str(Path(p).absolute()): {'resolved': str(Path(p).resolve(strict=True)),
                     'sha256': sha256(p)} for p in [*inputs, *executables]}
        self.executables = {str(Path(p).absolute()) for p in executables}
        self.rss_limit, self.min_disk, self.timeout = rss_limit, min_disk, timeout
        self.count = 0
        self.resource_failed = False
        self.receipts = []
        _json_new(self.root / 'EXECUTION_BINDINGS.json', {'files': self.rows,
            'runtime_manifest_sha256': APPROVED_MANIFEST_SHA256,
            'scope': 'selected inputs/executables; native dynamic-library closure not established'})

    def revalidate(self):
        self.runtime.revalidate()
        for p, expected in self.rows.items():
            if (not Path(p).is_file() or str(Path(p).resolve()) != expected['resolved'] or
                    sha256(p) != expected['sha256']):
                raise RuntimeRefused('GTOTREE_EXECUTION_BINDING_DRIFT')

    def __call__(self, command, log, env):
        from _release_validation import run_watched
        self.count += 1
        path = self.root / ('watch_%03d' % self.count)
        error, receipt = None, None
        try:
            self.revalidate()
            if str(Path(command[0]).absolute()) not in self.executables:
                raise RuntimeRefused('GTOTREE_EXECUTION_UNBOUND_EXECUTABLE')
            for key, value in self.runtime.native_environment().items():
                if env.get(key) != value:
                    raise RuntimeRefused('GTOTREE_EXECUTION_ENV_DRIFT')
            if any(k in env for k in ('PYTHONPATH', 'PYTHONHOME')) or any(k.startswith('DYLD_') for k in env):
                raise RuntimeRefused('GTOTREE_EXECUTION_ENV_DRIFT')
            receipt = run_watched(list(map(str, command)), cwd=self.root,
                log=path.with_suffix('.log'), env=env, rss_limit=self.rss_limit,
                min_disk=self.min_disk, timeout=self.timeout,
                additional_disk_floors=tuple((Path(env[k]), self.min_disk) for k in
                    ('TMPDIR', 'HOME', 'XDG_CACHE_HOME')))
            self.revalidate()
            if receipt['exit_code'] != 0 or receipt.get('stop_reason') or receipt.get('cleanup_error'):
                error = 'GTOTREE_EXECUTION_CHILD_FAILED'
        except Exception as exc:
            error = type(exc).__name__ + ': ' + str(exc)
        if error and (receipt is None or receipt.get('stop_reason') or receipt.get('cleanup_error')):
            self.resource_failed = True
        _json_new(path.with_suffix('.json'), {'status': 'FAILED' if error else 'SUCCEEDED',
                                            'error': error, 'watch': receipt,
                                            'log_sha256': sha256(path.with_suffix('.log')) if path.with_suffix('.log').is_file() else None})
        self.receipts.append({'path': str(path.with_suffix('.json')), 'sha256': sha256(path.with_suffix('.json'))})
        log.write('Watched child diagnostics: ' + str(path) + '\n')
        log.flush()
        return (125 if self.resource_failed else (receipt['exit_code'] if receipt else 125)) if error else 0
