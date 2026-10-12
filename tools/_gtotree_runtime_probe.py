"""Executed only by approved whole-process watched driver; software-only."""
import os, sys, json, hashlib, importlib, importlib.metadata, platform, subprocess, traceback
from pathlib import Path

def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    PLAN = Path(argv[0])
    OUT = Path(argv[1])
    plan = json.loads(PLAN.read_text())

    def sha(p):
        with Path(p).open('rb') as f:
            d = hashlib.sha256()
            for block in iter(lambda : f.read(1024 * 1024), b''):
                d.update(block)
        return d.hexdigest()

    def put(name, obj):
        with (OUT / name).open('x') as f:
            json.dump(obj, f, indent=2)
            f.write('\n')

    def inside(path, root):
        try:
            Path(path).resolve().relative_to(Path(root).resolve())
            return True
        except ValueError:
            return False
    try:
        E = Path(plan['environment'])
        S = Path(plan['editable_source'])
        if not (sys.flags.no_user_site and sys.dont_write_bytecode and sys.flags.safe_path):
            raise RuntimeError('GTOTREE_RUNTIME_WORKER_CONTRACT')
        if not ('PYTHONPATH' not in os.environ and 'PYTHONHOME' not in os.environ):
            raise RuntimeError('GTOTREE_RUNTIME_WORKER_CONTRACT')
        if not all((os.environ[k] == '1' for k in plan['thread_environment_keys'])):
            raise RuntimeError('GTOTREE_RUNTIME_WORKER_CONTRACT')
        if not Path.cwd() == OUT / 'cwd':
            raise RuntimeError('GTOTREE_RUNTIME_WORKER_CONTRACT')
        if not (sys.pycache_prefix == str(OUT / 'cache' / 'pycache') and (not Path(sys.pycache_prefix).exists())):
            raise RuntimeError('GTOTREE_RUNTIME_WORKER_CONTRACT')
        runtime = {'executable': sys.executable, 'executable_resolved': str(Path(sys.executable).resolve()), 'executable_sha256': sha(sys.executable), 'python_version': sys.version, 'pycache_prefix': sys.pycache_prefix, 'platform': platform.platform(), 'machine': platform.machine(), 'pointer_bits': 8 * __import__('struct').calcsize('P'), 'sys_path': sys.path, 'no_user_site': sys.flags.no_user_site, 'safe_path': sys.flags.safe_path, 'dont_write_bytecode': sys.dont_write_bytecode, 'thread_environment': {k: os.environ[k] for k in plan['thread_environment_keys']}, 'available_cpu_count_observed': os.cpu_count(), 'modules': []}
        for (mod, dist) in [('gtotree', 'gtotree'), ('pyhmmer', 'pyhmmer'), ('Bio', 'biopython'), ('numpy', 'numpy'), ('pandas', 'pandas')]:
            m = importlib.import_module(mod)
            path = Path(m.__file__).resolve()
            if not (inside(path, S / 'gtotree') if mod == 'gtotree' else inside(path, E)):
                raise RuntimeError('GTOTREE_RUNTIME_WORKER_CONTRACT')
            d = importlib.metadata.distribution(dist)
            runtime['modules'].append({'module': mod, 'origin': str(path), 'sha256': sha(path), 'loaded_version': getattr(m, '__version__', None), 'distribution_version': d.version, 'distribution_metadata_path': str(d._path), 'version_comparison': 'NO_MODULE_VERSION' if getattr(m, '__version__', None) is None else 'MATCH' if str(m.__version__) == d.version else 'MISMATCH'})
            if not runtime['modules'][-1]['version_comparison'] != 'MISMATCH':
                raise RuntimeError('GTOTREE_RUNTIME_WORKER_CONTRACT')
            if not (inside(d._path, E) or inside(d._path, S)):
                raise RuntimeError('GTOTREE_RUNTIME_WORKER_CONTRACT')
        import gtotree.main
        from gtotree.utils.misc.general import search_threads_per_genome
        from gtotree.utils.hmms import hmm_searching_engine
        from types import SimpleNamespace
        runtime['observed_hmm_threads_per_genome'] = [search_threads_per_genome(SimpleNamespace(num_jobs=j, num_muscle_threads=1)) for j in (1, 2)]
        if not runtime['observed_hmm_threads_per_genome'] == [2, 2]:
            raise RuntimeError('GTOTREE_RUNTIME_WORKER_CONTRACT')
        runtime['loaded_file_closure'] = []
        for (name, m) in sorted(sys.modules.items()):
            p = getattr(m, '__file__', None)
            if not p:
                continue
            p = Path(p).resolve()
            if not p.is_file():
                continue
            if not (inside(p, E) or inside(p, S) or p == Path(__file__).resolve()):
                raise RuntimeError('UNEXPECTED_MODULE_ORIGIN: ' + name)
            runtime['loaded_file_closure'].append({'module': name, 'origin': str(p), 'sha256': sha(p), 'bytes': p.stat().st_size})
        put('IMPORT_ORIGINS.json', runtime)
        commands = []
        for (i, (name, *args)) in enumerate(plan['commands']):
            cmd = [str(E / 'bin' / name), *args]
            stdout = OUT / f'command_{i:02d}.stdout'
            stderr = OUT / f'command_{i:02d}.stderr'
            with stdout.open('xb') as a, stderr.open('xb') as b:
                r = subprocess.run(cmd, cwd=OUT / 'cwd', env=os.environ.copy(), stdout=a, stderr=b, timeout=60, check=False)
            row = {'argv': cmd, 'exit_code': r.returncode, 'stdout_sha256': sha(stdout), 'stderr_sha256': sha(stderr)}
            commands.append(row)
            put(f'command_{i:02d}.json', row)
            if not r.returncode == 0:
                raise RuntimeError('SOFTWARE_PROBE_NONZERO: ' + name)
            if name in ('gtotree', 'GToTree') and args == ['-v']:
                if not 'GToTree v2.0.0' in stdout.read_text():
                    raise RuntimeError('CLI_VERSION_DISAGREEMENT')
            if name == 'gtotree' and args == ['-s']:
                t = stdout.read_text()
                if not ('--num-jobs' in t and '--muscle-threads' in t):
                    raise RuntimeError('CLI_HELP_CONTRACT_MISSING')
        put('WORKER_RESULT.json', {'status': 'PASS_SOFTWARE_PROBE_ONLY', 'commands': commands, 'native_job': False, 'model_validation': False, 'scientific_validation': False})
    except BaseException as exc:
        put('WORKER_FAILURE.json', {'status': 'FAILED', 'type': type(exc).__name__, 'message': str(exc), 'traceback': traceback.format_exc()})
        raise
if __name__ == '__main__':
    raise SystemExit(main())
