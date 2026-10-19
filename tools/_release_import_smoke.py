"""Discover and test the complete production import surface in controlled workers.

Only an admitted macOS sandbox backend is implemented here. Other hosts refuse
before importing production code; they are never silently treated as equivalent.
"""
from __future__ import annotations

import ast
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import sys

import _release_partition_runner as partition
import _release_validation as support
import _release_import_worker as import_contract
import _release_font_cache as _font_cache

IMPORT_READY_STATES = import_contract.IMPORT_READY_STATES


SCHEMA = 'sapote-mamey.controlled-import-smoke.v2'
BLOCKED_CONTROLS = {'source_write','outside_read','native_outside_read','native_source_write',
                    'native_fork','native_network','fork','spawn_python','spawn_external','network'}


def machinery_digest() -> str:
    """Bind the worker, controller and all reused validation helpers."""
    import verify_external_validation_receipt as existing
    files = [Path(__file__), Path(__file__).with_name('_release_import_worker.py'), Path(_font_cache.__file__),
             Path(support.__file__), Path(partition.__file__), Path(partition.contract.__file__), Path(existing.__file__)]
    return hashlib.sha256(support.canonical_json({path.name:support.sha256_file(path) for path in files})).hexdigest()


def require_source_only_imports(source: Path) -> None:
    """Refuse cached code that can bypass the source bytes in the bound roster."""
    for path in source.rglob('*'):
        if path.suffix in {'.pyc','.pyo'} or path.is_symlink() and '__pycache__' in path.parts:
            raise support.ValidationRefused('source-only import admission refuses bytecode/cache links: '+str(path.relative_to(source)))


def roster(source: Path) -> list[dict]:
    """Inventory every Python file under mamey/tools, including explicit test roles."""
    source = source.resolve(strict=True)
    rows = []
    for folder in ('mamey', 'tools'):
        for path in sorted((source/folder).rglob('*.py')):
            if '__pycache__' in path.parts:
                continue
            if path.is_symlink():
                raise support.ValidationRefused('import roster contains a symlink')
            relative = path.relative_to(source)
            parts = relative.parts
            test = path.name.startswith('test_') or any(part in {'tests','fixtures','test_fixtures'} for part in parts[:-1])
            name = '.'.join(relative.with_suffix('').parts)
            if path.name == '__init__.py':
                name = '.'.join(relative.parent.parts)
            row = {'path':relative.as_posix(), 'module':name, 'sha256':support.sha256_file(path),
                   'role':'TEST_OR_FIXTURE' if test else 'PRODUCTION', 'csv_setter':False, 'parse_error':None, 'matplotlib_import':False}
            try:
                tree = ast.parse(path.read_text(encoding='utf-8'))
                row['matplotlib_import'] = any(
                    isinstance(node,ast.Import) and any(alias.name.split('.')[0]=='matplotlib' for alias in node.names)
                    or isinstance(node,ast.ImportFrom) and (node.module or '').split('.')[0]=='matplotlib'
                    for node in ast.walk(tree))
                csv_modules = {'csv'};csv_functions = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        csv_modules.update(alias.asname or alias.name for alias in node.names if alias.name=='csv')
                    if isinstance(node, ast.ImportFrom) and node.module=='csv':
                        csv_functions.update(alias.asname or alias.name for alias in node.names if alias.name=='field_size_limit')
                def is_setter(call):
                    if not isinstance(call, ast.Call) or not (call.args or call.keywords):
                        return False
                    target = call.func
                    if isinstance(target, ast.Name):
                        return target.id in csv_functions
                    if isinstance(target, ast.Attribute) and target.attr=='field_size_limit':
                        return ((isinstance(target.value, ast.Name) and target.value.id in csv_modules)
                            or isinstance(target.value, ast.Call) and isinstance(target.value.func, ast.Name)
                            and target.value.func.id=='__import__' and target.value.args
                            and isinstance(target.value.args[0], ast.Constant) and target.value.args[0].value=='csv')
                    if isinstance(target, ast.Call) and isinstance(target.func, ast.Name) and target.func.id=='getattr':
                        owner = target.args[0] if target.args else None
                        csv_owner = ((isinstance(owner, ast.Name) and owner.id in csv_modules)
                            or isinstance(owner, ast.Call) and isinstance(owner.func, ast.Name)
                            and owner.func.id=='__import__' and owner.args
                            and isinstance(owner.args[0], ast.Constant) and owner.args[0].value=='csv')
                        return (len(target.args)>=2 and csv_owner and isinstance(target.args[1], ast.Constant)
                            and target.args[1].value=='field_size_limit')
                    return False
                # Follow ordinary function aliases without evaluating any module code.
                changed = True
                while changed:
                    changed = False
                    for assignment in ast.walk(tree):
                        if not isinstance(assignment, ast.Assign):
                            continue
                        fake_call = ast.Call(func=assignment.value, args=[ast.Constant(value=1)], keywords=[])
                        if is_setter(fake_call):
                            for target in assignment.targets:
                                if isinstance(target, ast.Name) and target.id not in csv_functions:
                                    csv_functions.add(target.id); changed = True
                row['csv_setter'] = any(is_setter(node) for node in ast.walk(tree))
                row['has_main_guard'] = any(isinstance(node, ast.If) and '__name__' in ast.dump(node.test)
                    and '__main__' in ast.dump(node.test) for node in tree.body)
            except (SyntaxError, UnicodeError) as exc:
                row['parse_error'] = str(exc)
            rows.append(row)
    if not rows or len({row['module'] for row in rows}) != len(rows):
        raise support.ValidationRefused('import roster is empty or has ambiguous canonical module names')
    return rows


def roster_digest(rows: list[dict]) -> str:
    """Bind scope, classification, paths, code and static discoveries together."""
    return hashlib.sha256(support.canonical_json(rows)).hexdigest()




def font_cache_required(rows):
    return any(row.get('matplotlib_import') for row in rows if row['role'] == 'PRODUCTION')


def font_bootstrap_environment(env, request, python):
    output = Path(request['output'])
    result = dict(env, HOME=str(output/'home'), XDG_CONFIG_HOME=str(output/'config'),
                  # XDG users such as fontconfig must not write into the single-file Matplotlib cache.
                  XDG_CACHE_HOME=str(output/'home'/'.cache'), XDG_DATA_HOME=str(output/'data'),
                  TMPDIR=str(output/'tmp'), MPLCONFIGDIR=request['cache_root'], MPLBACKEND='Agg')
    for key in ('PYTHONPATH', 'PYTHONHOME', 'MATPLOTLIBRC', 'FONTCONFIG_FILE', 'FONTCONFIG_PATH'):
        result.pop(key, None)
    result['PATH'] = os.pathsep.join(dict.fromkeys([str(python.parent),
        *[str(Path(x['path']).parent) for x in request['font_tools']],
        '/usr/bin', '/bin', '/usr/sbin', '/sbin']))
    return result


def font_bootstrap_profile(source, directory, python, environment, font_tools):
    """Separate dependency-only policy; never reused by production workers."""
    def q(path):
        named = Path(path)
        return json.dumps(str(named if named.is_relative_to(directory) else named.resolve()))
    runtime = admitted_runtime_reads(python, environment)
    if any(source.is_relative_to(path) for path in runtime):
        raise support.ValidationRefused('bootstrap runtime read root contains project source')
    reads = [*runtime, Path(_font_cache.__file__), directory/'font-bootstrap-spec.json',
             Path('/System'), Path('/usr/lib'), Path('/usr/share'), Path('/private/etc')]
    for tool in font_tools:
        reads.append(Path(tool))
        # Only the selected executable's installed package, not all Homebrew.
        if str(tool).startswith('/opt/homebrew/Cellar/'):
            parts = Path(tool).parts
            reads.append(Path(*parts[:6]))
    return '\n'.join(['(version 1)', '(import "system.sb")', '(deny default)',
        '(deny network*)', '(allow file-read-metadata)', '(deny file-read* (subpath "/Network"))',
        '(allow file-read* '+' '.join('(subpath '+q(x)+')' if x != directory/'font-bootstrap-spec.json' and x.is_dir() else '(literal '+q(x)+')' for x in reads)
            +' (subpath '+q(directory/'font-bootstrap')+')'
            +' (literal "/dev/null") (literal "/dev/random") (literal "/dev/urandom"))',
        '(allow file-write* (subpath '+q(directory/'font-bootstrap')+') (literal "/dev/null"))',
        '(allow file-write-create (literal '+q(directory/'font-bootstrap')+'))',
        '(allow file-write-data (literal '+q(directory/'font-bootstrap.log')+'))',
        '(deny file-write* (subpath '+q(source)+'))', '(allow process-fork)',
        '(allow process-exec '+' '.join('(literal '+q(x)+')' for x in [python, *map(Path, font_tools)])+')',
        '(allow sysctl-read)', '(allow mach-lookup)'])+'\n'


def prepare_font_cache(source, output, python, environment, env, context):
    """Run lane07's fixed data-only helper with the actual selected interpreter."""
    current = _font_cache.runtime_identity(); selected = environment['identity']
    if any(current[key] != selected[other] for key,other in [('executable','executable_target'),('version','version'),('prefix','prefix'),('base_prefix','base_prefix')]):
        raise support.ValidationRefused('font bootstrap controller must run under the selected Python executable and prefix')
    choices = [row for row in environment['identity']['distributions']
               if row['name'].lower().replace('_', '-') == 'matplotlib']
    if len(choices) != 1:
        raise support.ValidationRefused('required font bootstrap has no unique admitted Matplotlib distribution')
    distribution = choices[0]; location = Path(distribution['location'])
    metadata = [p for p in location.glob('matplotlib-*.dist-info/METADATA')
                if ('Version: '+distribution['version']) in p.read_text().splitlines()]
    if len(metadata) != 1:
        raise support.ValidationRefused('font bootstrap Matplotlib metadata is missing or ambiguous')
    tools = [str(Path(choice).resolve()) for name in ('fc-list', 'system_profiler')
             if (choice := shutil.which(name))]
    spec = {'output': str(output/'font-bootstrap'), 'source': str(source), 'context': context,
            'matplotlib_root': str(location/'matplotlib'), 'metadata': str(metadata[0]), 'font_tools': tools}
    spec_path = output/'font-bootstrap-spec.json'; _font_cache.write_new_json(spec_path, spec)
    # Build the declared environment from data; make_request itself runs only in selected Python.
    projected = {'output': spec['output'], 'cache_root': str(Path(spec['output'])/'matplotlib'),
                 'font_tools': [{'path': path} for path in tools]}
    bootstrap_env = font_bootstrap_environment(env, projected, python)
    profile = output/'font-bootstrap.sb'
    profile.write_text(font_bootstrap_profile(source, output, python, environment, tools)); profile.chmod(0o600)
    prepared_path = Path(spec['output'])/'PREPARED.json'
    command = [shutil.which('sandbox-exec'), '-f', str(profile), str(python), '-I', '-B',
        str(Path(_font_cache.__file__)), '--prepare-spec', str(spec_path),
        '--spec-sha256', support.sha256_file(spec_path), '--receipt', str(prepared_path)]
    watch = support.run_watched(command, cwd=output, log=output/'font-bootstrap.log', env=bootstrap_env, timeout=120)
    if watch['exit_code'] != 0 or watch['stop_reason'] is not None or watch.get('cleanup_error'):
        raise support.ValidationRefused('dependency-only font bootstrap refused; preserve its bound log')
    request_path = Path(spec['output'])/'request.json'; request = _font_cache.read_json(request_path)
    prepared = _font_cache.read_json(prepared_path)
    if (request['context'] != context or prepared.get('status') != 'PREPARED'
            or prepared.get('context') != context or prepared.get('runtime') != request['runtime']
            or request['source'] != str(source) or request['output'] != spec['output']):
        raise support.ValidationRefused('font bootstrap output/context differs from declared inputs')
    _font_cache.validate_cache(request, manifest_sha256=prepared['manifest_sha256'])
    return {'status': 'PREPARED', 'request': request, 'manifest_sha256': prepared['manifest_sha256'],
            'spec_sha256': support.sha256_file(spec_path),
            'request_file_sha256': support.sha256_file(request_path),
            'prepared_sha256': support.sha256_file(prepared_path),
            'profile_sha256': support.sha256_file(profile), 'watch': watch,
            'bootstrap_environment_sha256': hashlib.sha256(support.canonical_json(bootstrap_env)).hexdigest()}


def validate_font_evidence(source, root, font, environment, env):
    """Recheck all cache/bootstrap evidence, including safe moved-output reads."""
    require = partition.contract.require
    require(font.get('status') in {'PREPARED', 'NOT_REQUESTED'}, 'unknown font bootstrap state')
    if font['status'] == 'NOT_REQUESTED':
        require(not font_cache_required(roster(source)), 'required font cache omitted')
        return
    request = font['request']; prepared_dir = root/'font-bootstrap'; cache = prepared_dir/'matplotlib'
    require(source.is_absolute() and not prepared_dir.is_relative_to(source), 'font output/source overlap')
    require(support.sha256_file(root/'font-bootstrap-spec.json') == font['spec_sha256'], 'font spec hash differs')
    require(support.sha256_file(prepared_dir/'request.json') == font['request_file_sha256'], 'font request hash differs')
    require(_font_cache.read_json(prepared_dir/'request.json') == request, 'font request payload differs')
    require(support.sha256_file(prepared_dir/'PREPARED.json') == font['prepared_sha256'], 'font preparation hash differs')
    prepared = _font_cache.read_json(prepared_dir/'PREPARED.json')
    require(prepared.get('status') == 'PREPARED' and prepared.get('manifest_sha256') == font['manifest_sha256']
        and prepared.get('context') == request['context'] and prepared.get('runtime') == request['runtime'],
        'font preparation result differs')
    require(request['context'] == {'source_sha256': partition.source_digest(source),
        'environment_sha256': environment['identity_sha256'], 'machinery_sha256': machinery_digest()},
        'font bootstrap source/environment/machinery binding differs')
    _font_cache.validate_cache(request, manifest_sha256=font['manifest_sha256'], evidence_output=prepared_dir)
    python = Path(environment['resolved_executable'])
    original_root = Path(request['output']).parent
    spec = _font_cache.read_json(root/'font-bootstrap-spec.json')
    require(spec == {'output': request['output'], 'source': str(source), 'context': request['context'],
        'matplotlib_root': request['dependency']['root'], 'metadata': request['metadata']['path'],
        'font_tools': [tool['path'] for tool in request['font_tools']]}, 'font spec content differs')
    expected_profile = font_bootstrap_profile(source, original_root, python, environment, spec['font_tools'])
    require((root/'font-bootstrap.sb').read_text() == expected_profile
        and support.sha256_file(root/'font-bootstrap.sb') == font['profile_sha256'], 'font bootstrap policy differs')
    bootstrap_env = font_bootstrap_environment(env, request, python)
    require(hashlib.sha256(support.canonical_json(bootstrap_env)).hexdigest() == font['bootstrap_environment_sha256'],
            'font bootstrap environment differs')
    # Resolve the locator separately and reconstruct argv as data only.
    # This validator never launches it; bootstrap admission/execution is separate.
    sandbox_executable = shutil.which('sandbox-exec')
    expected_argv = [sandbox_executable, '-f', str(original_root/'font-bootstrap.sb'), str(python), '-I', '-B',
        str(Path(_font_cache.__file__)), '--prepare-spec', str(original_root/'font-bootstrap-spec.json'),
        '--spec-sha256', font['spec_sha256'], '--receipt', str(Path(request['output'])/'PREPARED.json')]
    nice = shutil.which('nice'); watch = font['watch']
    require(watch.get('argv') == ([nice, '-n', '15', *expected_argv] if nice else expected_argv)
        and watch.get('exit_code') == 0 and watch.get('stop_reason') is None and watch.get('cleanup_error') is None
        and watch.get('rss_stop_bytes') == support.DEFAULT_RSS_LIMIT
        and watch.get('minimum_free_disk_bytes') == support.DEFAULT_MIN_DISK
        and watch.get('timeout_seconds') == 120 and watch.get('monitor_interval_seconds') == 0.2
        and isinstance(watch.get('peak_process_tree_rss'), int)
        and 0 <= watch['peak_process_tree_rss'] < support.DEFAULT_RSS_LIMIT,
        'font bootstrap watch/command/resource policy differs')
    require(support.sha256_file(root/'font-bootstrap.log') == watch.get('log_sha256'), 'font bootstrap log differs')
    partition.contract.validate_age(watch)


def admitted_runtime_reads(python: Path, environment: dict) -> list[Path]:
    """Read exact bound runtime roots; refuse unsupported dependency layouts.

    Preserve venv invocation while admitting its separate base installation.
    Installed dependency metadata is identity-bound, not a recursive code hash.
    """
    def refuse(message):
        raise support.ValidationRefused('import runtime admission: '+message)
    if not isinstance(environment, dict) or environment.get('status') != 'READY':
        refuse('bound READY environment is required')
    try:
        identity = environment['identity']
        payload = {key: environment[key] for key in
                   ('executable_sha256', 'identity', 'test_environment_sha256')}
        if hashlib.sha256(support.canonical_json(payload)).hexdigest() != environment['identity_sha256']:
            refuse('environment identity digest differs')
        invocation = Path(environment['resolved_executable'])
        target = Path(environment['executable_target'])
        if (not invocation.is_absolute() or not target.is_absolute()
                or invocation != python.absolute()
                or identity['executable'] != str(invocation)
                or identity['invocation_executable'] != str(invocation)
                or identity['invocation_target'] != str(target)
                or identity['executable_target'] != str(target)):
            refuse('invocation/target binding differs')
        if (invocation.resolve(strict=True) != target.resolve(strict=True)
                or support.sha256_file(target) != environment['executable_sha256']):
            refuse('executable target changed')
        forbidden = {path.resolve() for path in (Path('/'), Path('/Users'), Path('/private'), Path('/tmp'),
                     Path('/var'), Path('/usr'), Path('/usr/local'), Path('/opt'),
                     Path('/Library'), Path.home(), Path.home()/'.cache')}
        def directory(raw):
            path = Path(raw)
            if not path.is_absolute():
                refuse('runtime read directory is relative')
            path = path.resolve(strict=True)
            if not path.is_dir() or path in forbidden:
                refuse('runtime read directory is missing or too broad')
            return path
        base = directory(identity['base_prefix'])
        prefix = directory(identity['prefix'])
        if not target.resolve(strict=True).is_relative_to(base):
            refuse('binary target is outside admitted base runtime')
        dependencies = identity['distributions']
        if not isinstance(dependencies, list):
            refuse('installed distribution evidence is missing')
        reads = [base, prefix]
        for distribution in dependencies:
            location = directory(distribution['location'])
            if location.name not in {'site-packages', 'dist-packages'}:
                refuse('unsupported distribution read layout')
            reads.append(location)
        return list(dict.fromkeys(reads))
    except (KeyError, TypeError, OSError, RuntimeError) as exc:
        refuse('incomplete or unavailable runtime evidence: '+str(exc))


def mac_profile(source: Path, scratch: Path, controls: Path, worker: Path, python: Path, environment: dict, font=None) -> str:
    """Permit installed runtime/source reads and scratch writes, denying work channels."""
    def quoted(path):
        named = Path(path)
        if font and font.get('status') == 'PREPARED' and named.is_relative_to(Path(font['request']['output'])):
            return json.dumps(str(named))
        return json.dumps(str(named.resolve()))
    reads = [source, scratch, controls/'readonly', worker.parent,
             *admitted_runtime_reads(python, environment), Path('/System'), Path('/usr/lib'), Path('/usr/share'), Path('/private/etc')]
    if font and font.get('status') == 'PREPARED':
        reads += [Path(font['request']['output']), *[Path(item['path']) for item in font['request']['font_tools']]]
    profile = ['(version 1)', '(import "system.sb")', '(deny default)',
        '(deny network*)', '(deny process-fork)', '(allow file-read-metadata)',
        '(allow file-read* '+ ' '.join('(subpath '+quoted(path)+')' for path in reads)
            +' (literal "/dev/null") (literal "/dev/random") (literal "/dev/urandom"))',
        '(allow file-write* (subpath '+quoted(scratch)+') (literal "/dev/null"))',
        '(allow process-exec (literal '+quoted(python)+'))', '(allow sysctl-read)', '(allow mach-lookup)']
    if font and font.get('status') == 'PREPARED':
        profile.append('(allow file-write-create file-write-data (literal '+quoted(font['request']['cache_root'])+'))')
    return '\n'.join(profile)+'\n'


PROBE = r'''
import ctypes, errno, json, os, socket, struct, subprocess, sys
from pathlib import Path
scratch=Path(sys.argv[1]);readonly=Path(sys.argv[2]);outside=Path(sys.argv[3]);cache=Path(sys.argv[4]) if sys.argv[4] else None;port=int(sys.argv[5])
results={}
def blocked(name, operation):
    try:
        operation()
    except OSError as exc:
        results[name]={'blocked':exc.errno in {errno.EPERM,errno.EACCES},'errno':exc.errno}
    except subprocess.SubprocessError as exc:
        results[name]={'blocked':False,'reason':str(exc)}
    else:
        results[name]={'blocked':False}
(scratch/'allowed').write_text('safe scratch write')
results['scratch_write']={'allowed':(scratch/'allowed').is_file()}
results['source_read']={'allowed':readonly.read_text()=='readonly canary'}
blocked('source_write',lambda:readonly.write_text('forbidden mutation'))
blocked('outside_read',lambda:outside.read_bytes())
libc=ctypes.CDLL(None,use_errno=True);libc.open.argtypes=[ctypes.c_char_p,ctypes.c_int];libc.open.restype=ctypes.c_int
ctypes.set_errno(0)
fd=libc.open(os.fsencode(outside),os.O_RDONLY)
if fd>=0:os.close(fd)
results['native_outside_read']={'blocked':fd<0 and ctypes.get_errno() in {errno.EPERM,errno.EACCES}}
ctypes.set_errno(0)
fd=libc.open(os.fsencode(readonly),os.O_WRONLY|os.O_TRUNC)
if fd>=0:os.close(fd)
results['native_source_write']={'blocked':fd<0 and ctypes.get_errno() in {errno.EPERM,errno.EACCES}}
libc.fork.restype=ctypes.c_int
ctypes.set_errno(0);pid=libc.fork()
if pid==0:os._exit(0)
if pid>0:os.waitpid(pid,0)
results['native_fork']={'blocked':pid<0 and ctypes.get_errno() in {errno.EPERM,errno.EACCES}}
libc.socket.restype=ctypes.c_int
fd=libc.socket(socket.AF_INET,socket.SOCK_STREAM,0)
if fd<0:
    results['native_network']={'blocked':ctypes.get_errno() in {errno.EPERM,errno.EACCES}}
else:
    address=ctypes.create_string_buffer(struct.pack('BB',16,socket.AF_INET)+struct.pack('!H',port)+socket.inet_aton('127.0.0.1')+b'\0'*8)
    ctypes.set_errno(0);connected=libc.connect(fd,address,16)
    results['native_network']={'blocked':connected<0 and ctypes.get_errno() in {errno.EPERM,errno.EACCES}}
    os.close(fd)
def fork():
    pid=os.fork()
    if pid==0:os._exit(0)
    os.waitpid(pid,0)
blocked('fork',fork)
blocked('spawn_python',lambda:subprocess.run([sys.executable,'-I','-c','pass'],check=True))
blocked('spawn_external',lambda:subprocess.run(['/usr/bin/true'],check=True))
def connect():
    with socket.socket() as stream:
        stream.settimeout(1);stream.connect(('127.0.0.1',port))
blocked('network',connect)
if cache is not None:
    before=cache.lstat()
    cache.mkdir(mode=0o777,exist_ok=True)
    after=cache.lstat()
    fields=lambda info:(info.st_dev,info.st_ino,info.st_mode,info.st_uid,info.st_nlink,info.st_size,info.st_mtime_ns,info.st_ctime_ns)
    results['cache_directory_noop']={'allowed':fields(before)==fields(after) and os.access(cache,os.W_OK)}
    blocked('cache_new_entry',lambda:(cache/'__protected_probe__').mkdir())
    blocked('cache_mode_change',lambda:os.chmod(cache,0o700))
    targets=list(cache.glob('fontlist-v*.json'))
    if len(targets)!=1:raise RuntimeError('prepared cache file is ambiguous')
    ctypes.set_errno(0);fd=libc.open(os.fsencode(targets[0]),os.O_WRONLY)
    if fd>=0:os.close(fd)
    results['cache_native_content_write']={'blocked':fd<0 and ctypes.get_errno() in {errno.EPERM,errno.EACCES}}
sys.stdout.write(json.dumps(results,sort_keys=True))
'''


def admit_sandbox(source: Path, output: Path, python: Path, env: dict[str,str], *, environment=None, font=None) -> dict:
    """Prove controls on owned canaries before any production module import."""
    if sys.platform != 'darwin' or shutil.which('sandbox-exec') is None:
        raise support.ValidationRefused('No admitted controlled-import backend on this host; macOS sandbox-exec is required')
    controls = output/'controls';scratch = controls/'scratch'
    scratch.mkdir(parents=True);(controls/'readonly').mkdir();(controls/'outside').mkdir()
    readonly = controls/'readonly/canary';readonly.write_text('readonly canary')
    outside = controls/'outside/canary';outside.write_text('private-read canary')
    worker = Path(__file__).with_name('_release_import_worker.py')
    profile = controls/'profile.sb';profile.write_text(mac_profile(source,scratch,controls,worker,python,environment,font))
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0));listener.listen(8)
        command = [shutil.which('sandbox-exec'),'-f',str(profile),str(python),'-I','-c',PROBE,
            str(scratch),str(readonly),str(outside),font['request']['cache_root'] if font and font['status']=='PREPARED' else '',str(listener.getsockname()[1])]
        watch = support.run_watched(command,cwd=scratch,log=controls/'probe.log',env=env,timeout=20)
    if watch['exit_code'] != 0 or watch['stop_reason'] is not None:
        raise support.ValidationRefused('controlled-import sandbox probe failed; inspect controls/probe.log')
    measured = json.loads((controls/'probe.log').read_text())
    expected = BLOCKED_CONTROLS | ({'cache_new_entry','cache_mode_change','cache_native_content_write'} if font and font['status']=='PREPARED' else set())
    if (set(measured) != expected|{'scratch_write','source_read'}|({'cache_directory_noop'} if font and font['status']=='PREPARED' else set())
        or not all(measured[name].get('blocked') is True for name in expected)
        or not measured['scratch_write'].get('allowed') or not measured['source_read'].get('allowed')
        or (font and font['status']=='PREPARED' and measured['cache_directory_noop'].get('allowed') is not True)
        or readonly.read_text()!='readonly canary'):
        raise support.ValidationRefused('sandbox did not enforce every required control; no imports admitted')
    report = {'schema':'sapote-mamey.import-sandbox-admission.v1','status':'ADMITTED', 'backend':'macOS sandbox-exec',
        'backend_sha256':support.sha256_file(Path(shutil.which('sandbox-exec'))),
        'profile_sha256':support.sha256_file(profile),'measured':measured,'watch':watch}
    support.atomic_json(controls/'admission.json',report)
    return report


def verify_worker(trace: Path, selected: list[dict], order: str, mode: str, *, validate_required=False,
                  source=None, policy=None, font=None, context=None) -> dict:
    """Verify complete raw observations and narrow, independently replayed exceptions."""
    require = partition.contract.require
    events = [json.loads(line) for line in trace.read_text().splitlines()]
    digest = roster_digest(selected)
    require(bool(events) and events[0].get('type') == 'start' and events[-1].get('type') == 'complete'
        and events[0].get('roster_sha256') == digest and events[-1].get('roster_sha256') == digest,
        'shared import trace is incomplete or its roster binding differs')
    rows = [entry for entry in events if entry.get('type') == 'module']
    require([entry.get('path') for entry in rows] == [entry['path'] for entry in selected]
        and [entry.get('module') for entry in rows] == [entry['module'] for entry in selected]
        and len(events) == len(selected)+2
        and events[-1].get('results') == [{key:value for key,value in entry.items() if key != 'type'} for entry in rows]
        and all(event.get('order',order) == order and event.get('mode',mode) == mode for event in events),
        'shared import outcomes omit, duplicate or change declared modules')
    require(source is not None and policy is not None and font is not None and context is not None,
            'shared import verifier requires explicitly selected source and policy')
    source = Path(source).resolve(strict=True)
    start = events[0]; complete = events[-1]
    require(start.get('schema') == complete.get('schema') == import_contract.WORKER_SCHEMA
        and start.get('source') == str(source) and start.get('context') == context
        and start.get('vendor_policy_sha256') == import_contract.digest(policy)
        and start.get('font_descriptor_sha256') == import_contract.digest(font)
        and start.get('count') == len(selected), 'shared import worker context/schema differs')
    previous = import_contract.unpack_paths(start.get('initial_paths'))
    initial_supported = import_contract.supported_paths(previous)
    threshold = min(sys.maxsize,2**31-1)
    for entry, row in zip(selected, rows):
        require(row.get('status') in {'PASS','OPTIONAL_UNAVAILABLE','HOLD'}, 'shared import module outcome is unknown')
        state = row.get('path_state', {})
        before = import_contract.unpack_paths(state.get('before'))
        after = import_contract.unpack_paths(state.get('after'))
        require(before == previous, 'shared import raw path state is discontinuous')
        previous = after
        path_guard = import_contract.unsupported_path_guard(before,after)
        if path_guard is not None:
            require(row['status']=='HOLD' and row.get('path_guard')==path_guard,
                    'unsupported import path entries cannot claim ready module outcomes')
        else:
            require('path_guard' not in row,'supported import paths have unexpected refusal evidence')
        changes = row.get('state_changes')
        require(isinstance(changes,dict), 'shared import state changes are missing')
        if before != after:
            proof = import_contract.trusted_path_equivalence(source,before,after)
            require(row.get('trusted_path_change') == proof, 'trusted path change proof differs from current source')
            expected = {'before':import_contract.pack_paths(before),'after':import_contract.pack_paths(after)}
            require(('module_search_paths' not in changes if proof['equivalent'] else changes.get('module_search_paths') == expected),
                    'raw import path change was omitted or misclassified')
        else:
            require('trusted_path_change' not in row and 'module_search_paths' not in changes,
                    'unchanged import paths have unexpected change evidence')
        blocked = import_contract.blocking_operations(row,font)
        require(isinstance(row.get('operations'),list) and isinstance(row.get('directory_noops'),list),
                'raw operation evidence is missing')
        checks = row.get('csv_checks', [])
        require(isinstance(checks,list) and all(type(check.get('value')) is int for check in checks),
                'CSV observation evidence is malformed')
        safe = path_guard is None and not blocked and not changes and not row.get('csv_guard') and row.get('csv_limit_after',0) >= threshold
        if row['status'] == 'PASS':
            expected = ['import']
            if mode == 'csv':
                expected.append('reload')
            elif row.get('cached_before'):
                expected.append('reload_cached')
            phases = [check.get('phase') for check in checks]
            if mode == 'csv' and validate_required:
                if phases[len(expected):len(expected)+1] == ['initial_validate']:
                    expected.append('initial_validate')
                expected.append('cached_validate')
            require(safe and phases == expected and all(check['value'] >= threshold for check in checks)
                and not row.get('exception_type') and not row.get('exception_evidence')
                and not row.get('optional_availability')
                and row.get('resolved_module_path') == str((source/entry['path']).resolve()),
                'shared import PASS contradicts its CSV checks, origin or exception')
        if row.get('optional_availability'):
            evidence = row.get('exception_evidence', {})
            for item in [evidence.get('class_origin'), *evidence.get('frames',[])]:
                if item and item.get('sha256') is not None:
                    require(import_contract._permitted_origin(item['path'],source,policy['runtime_roots'])
                        and Path(item['path']).is_file() and support.sha256_file(Path(item['path'])) == item['sha256'],
                        'optional dependency exception origin differs')
            availability = import_contract.optional_unavailability(source,entry,evidence,policy)
            require(availability is not None and row['optional_availability'] == availability
                and row.get('exception_type') == evidence.get('type') and row.get('reason') == evidence.get('message'),
                'optional dependency availability evidence differs')
        if row['status'] == 'OPTIONAL_UNAVAILABLE':
            require(safe and row.get('optional_availability') and all(check['value'] >= threshold for check in checks),
                    'optional dependency absence conceals protected operations or state changes')
        capability = row.get('fallback_capability')
        if capability is not None:
            origin = capability.get('common_origin', {})
            expected = {'status':'PASS','backend':'python',
                'valid_input_sha256':hashlib.sha256(b'{"import_contract":[1,true,null]}').hexdigest(),
                'events_sha256':import_contract.digest(import_contract.FALLBACK_EVENTS),
                'invalid_inputs':[{'case':label,'input_sha256':hashlib.sha256(payload).hexdigest(),'exception':expected}
                    for label,payload,expected in import_contract.FALLBACK_INVALID_INPUTS],'common_origin':origin}
            require(row['module'] == import_contract.FALLBACK_MODULE and capability == expected
                and import_contract.common_dependency_matches(origin.get('path',''),source,policy)
                and import_contract._permitted_origin(origin.get('path',''),source,policy['runtime_roots'])
                and Path(origin['path']).is_file() and support.sha256_file(Path(origin['path'])) == origin['sha256'],
                'required Python JSON fallback capability differs')
    validation = complete.get('font_cache_validation', {})
    require(validation.get('status') in ({'PASS','HOLD'} if font['status'] == 'PREPARED' else {'NOT_REQUESTED'}),
            'terminal font cache verification is missing')
    status = import_contract.import_readiness(rows,policy) if validation['status'] != 'HOLD' and initial_supported else 'HOLD'
    require(complete.get('status') == status and complete.get('count') == len(selected)
        and complete.get('csv_minimum') == threshold, 'shared import summary differs from actual module outcomes')
    return {'status':status,'modules':len(rows),'held':sum(row['status'] == 'HOLD' for row in rows),
            'optional_unavailable':sum(row['status'] == 'OPTIONAL_UNAVAILABLE' for row in rows),'results':rows}


def verify_import_receipt(source: Path, receipt: Path, expected_sha256: str,
                          environment_identity_sha256: str, *, require_pass=True, env=None) -> dict:
    """Check complete source-bound import evidence without executing production imports.

    The consumer must first re-admit its current environment and pass that measured
    identity. Old absolute output paths are used only to reconstruct commands and
    profiles; every evidence read stays under the current receipt directory.
    """
    require = partition.contract.require
    source = source.resolve(strict=True); receipt = receipt.resolve(strict=True); root = receipt.parent
    require_source_only_imports(source)
    require(support.sha256_file(receipt) == expected_sha256, 'import receipt SHA-256 mismatch')
    data = json.loads(receipt.read_text())
    require(data.get('schema') == SCHEMA and data.get('status') in IMPORT_READY_STATES|{'HOLD'}, 'import receipt is incomplete or refused')
    partition.contract.validate_age(data)
    source_hash = partition.source_digest(source); rows = roster(source)
    require(data.get('source_sha256') == data.get('source_after_sha256') == source_hash, 'import source binding mismatch')
    require(data.get('roster') == rows and data.get('roster_sha256') == roster_digest(rows)
            and data.get('scope_counts') == dict(Counter(row['role'] for row in rows)), 'import roster binding mismatch')
    require(data.get('machinery_sha256') == machinery_digest(), 'import machinery binding mismatch')
    require(data.get('environment_identity_sha256') == environment_identity_sha256, 'import environment binding mismatch')
    environment = json.loads((root/'environment/environment.json').read_text())
    font = data.get('font_cache',{})
    require(environment.get('status') == 'READY' and environment.get('identity_sha256') == environment_identity_sha256,
            'import environment admission is not bound')

    def check_watch(watch, log, timeout, code):
        require(watch.get('exit_code') == code and watch.get('stop_reason') is None and watch.get('cleanup_error') is None,
                'import worker failed, stopped or did not clean up')
        require(watch.get('rss_stop_bytes') == support.DEFAULT_RSS_LIMIT
                and watch.get('minimum_free_disk_bytes') == support.DEFAULT_MIN_DISK
                and watch.get('timeout_seconds') == timeout and watch.get('monitor_interval_seconds') == 0.2
                and isinstance(watch.get('peak_process_tree_rss'),int)
                and 0 <= watch['peak_process_tree_rss'] < support.DEFAULT_RSS_LIMIT,
                'import worker resource policy differs')
        require(log.is_file() and support.sha256_file(log) == watch.get('log_sha256'), 'import log hash differs')
        partition.contract.validate_age(watch)

    for name, watch in zip(['identity.log','venv-create.log','venv-import.log'], environment.get('steps', [])):
        check_watch(watch, root/'environment'/name, 120, 0)
    require(len(environment.get('steps', [])) == 3, 'import environment admission steps are incomplete')
    sandbox = json.loads((root/'controls/admission.json').read_text())
    require(data.get('sandbox') == sandbox and sandbox.get('status') == 'ADMITTED'
            and sandbox.get('backend') == 'macOS sandbox-exec', 'import sandbox admission differs')
    backend = shutil.which('sandbox-exec')
    require(sys.platform == 'darwin' and backend and support.sha256_file(Path(backend)) == sandbox.get('backend_sha256'),
            'import sandbox backend differs or is unavailable')
    require(support.sha256_file(root/'controls/profile.sb') == sandbox.get('profile_sha256'), 'sandbox profile hash differs')
    measured = json.loads((root/'controls/probe.log').read_text())
    require(measured == sandbox.get('measured') and set(measured) == BLOCKED_CONTROLS|{'scratch_write','source_read'}|({'cache_new_entry','cache_mode_change','cache_native_content_write','cache_directory_noop'} if font['status']=='PREPARED' else set())
            and all(measured[name].get('blocked') is True for name in BLOCKED_CONTROLS|({'cache_new_entry','cache_mode_change','cache_native_content_write'} if font['status']=='PREPARED' else set()))
            and measured['scratch_write'].get('allowed') is True and measured['source_read'].get('allowed') is True
            and (font['status']!='PREPARED' or measured['cache_directory_noop'].get('allowed') is True),
            'sandbox control evidence is incomplete or permissive')
    check_watch(sandbox.get('watch', {}), root/'controls/probe.log', 20, 0)
    python = Path(environment['resolved_executable']); worker = Path(__file__).with_name('_release_import_worker.py')
    probe_watch = sandbox['watch']; old_scratch = Path(probe_watch.get('cwd',''))
    require(old_scratch.is_absolute() and old_scratch.parts[-2:] == ('controls','scratch'), 'sandbox probe location differs')
    old_root = old_scratch.parent.parent
    require((root/'controls/profile.sb').read_text() == mac_profile(source,old_scratch,old_root/'controls',worker,python,environment,font),
            'sandbox probe policy differs')
    probe_argv = probe_watch.get('argv', [])
    port = str(probe_argv[-1]) if probe_argv else ''
    require(port.isdecimal() and 0 < int(port) < 65536, 'sandbox probe listener port is invalid')
    command = [backend,'-f',str(old_root/'controls/profile.sb'),str(python),'-I','-c',PROBE,
        str(old_scratch),str(old_root/'controls/readonly/canary'),str(old_root/'controls/outside/canary'),font['request']['cache_root'] if font['status']=='PREPARED' else '',port]
    nice = shutil.which('nice')
    require(probe_argv == ([nice,'-n','15',*command] if nice else command), 'sandbox probe command differs')
    child_env = partition.test_environment(source,env)
    require(hashlib.sha256(support.canonical_json(child_env)).hexdigest() == environment.get('test_environment_sha256'),
            'current import environment variables differ')
    font = data.get('font_cache',{})
    validate_font_evidence(source,root,font,environment,child_env)
    policy = import_contract.vendor_policy(source,admitted_runtime_reads(python,environment),child_env)
    require(data.get('vendor_policy') == policy,'vendor optional policy differs')
    context = {'source_sha256':source_hash,'environment_sha256':environment_identity_sha256,'machinery_sha256':machinery_digest()}
    production = [row for row in rows if row['role'] == 'PRODUCTION']
    require(bool(production),'production import roster is empty')
    setters = [row for row in production if row['csv_setter']]
    expected_orders = [(mode, order, chosen if order == 'forward' else list(reversed(chosen)))
        for mode, chosen in [('general',production),('csv',setters)] if chosen for order in ['forward','reverse']]
    orders = data.get('orders', [])
    require([(row.get('mode'),row.get('order')) for row in orders] == [(mode,order) for mode,order,_ in expected_orders],
            'import orders are omitted, duplicated or reordered')
    if not setters:
        require(data.get('csv_roster_status') == 'NO_SETTERS_DISCOVERED', 'empty CSV roster is not explicit')
    for recorded, (mode,order,selected) in zip(orders, expected_orders):
        directory = root/(mode+'-'+order); watch = recorded['watch']
        actual = verify_worker(directory/'scratch/trace.jsonl',selected,order,mode,
                               validate_required=(source/'mamey/validate.py').is_file(), source=source,policy=policy,font=font,context=context)
        require(all(recorded.get(key) == value for key,value in actual.items()), 'recorded import outcomes differ from trace')
        require(support.sha256_file(directory/'scratch/trace.jsonl') == recorded.get('trace_sha256'), 'import trace hash differs')
        require(support.sha256_file(directory/'profile.sb') == recorded.get('profile_sha256'), 'import profile hash differs')
        request = json.loads((directory/'request.json').read_text())
        require(request == {'source':str(source),'roster':selected,'roster_sha256':roster_digest(selected),'mode':mode,'order':order,
            'context':context,'runtime_roots':policy['runtime_roots'],'vendor_policy':policy,'font_cache':font},
                'import request binding differs')
        original_scratch = Path(watch.get('cwd', ''))
        require(original_scratch.is_absolute() and original_scratch.parts[-2:] == (mode+'-'+order,'scratch'),
                'import worker scratch location is invalid')
        original_root = original_scratch.parent.parent
        expected_profile = mac_profile(source,original_scratch,original_root/'controls',worker,python,environment,font)
        expected_profile += '(allow file-read* (literal '+json.dumps(str(original_scratch.parent/'request.json'))+'))\n'
        require((directory/'profile.sb').read_text() == expected_profile, 'import profile policy differs')
        command = [backend,'-f',str(original_scratch.parent/'profile.sb'),str(python),'-I',str(worker),
                   '--request',str(original_scratch.parent/'request.json'),'--scratch',str(original_scratch)]
        nice = shutil.which('nice')
        require(watch.get('argv') == ([nice,'-n','15',*command] if nice else command), 'import worker command differs')
        worker_env = dict(child_env,HOME=str(original_scratch/'home'),XDG_CACHE_HOME=str(original_scratch/'cache'),
                          MPLCONFIGDIR=font['request']['cache_root'] if font['status']=='PREPARED' else str(original_scratch/'matplotlib'),MPLBACKEND='Agg')
        require(hashlib.sha256(support.canonical_json(worker_env)).hexdigest() == recorded.get('worker_environment_sha256'),
                'import worker environment differs')
        check_watch(watch,directory/'worker.log',600,0 if actual['status'] in IMPORT_READY_STATES else 2)
    status = ('PASS' if all(row['status']=='PASS' for row in orders) else
              'READY_WITH_OPTIONAL_UNAVAILABLE' if all(row['status'] in IMPORT_READY_STATES for row in orders) else 'HOLD')
    require(data['status'] == status, 'import root summary differs from outcomes')
    require(not require_pass or status in IMPORT_READY_STATES, 'complete import roster has unresolved HOLD outcomes')
    watches = [*environment['steps'],sandbox['watch'],*[row['watch'] for row in orders]]
    return {'status':status,'scope_counts':data['scope_counts'],
            'rss_sampling':{'zero_peak_records':sum(watch['peak_process_tree_rss']==0 for watch in watches),
                            'meaning':'Periodic observations only; zero means no positive RSS sample before exit, not zero memory use.'},
            'orders':[{key:entry[key] for key in ['mode','order','modules','held','optional_unavailable','status']} for entry in orders]}


def run_import_smoke(source: Path, output: Path, python: str, *, env=None) -> dict:
    """Run complete forward/reverse and CSV-reload workers after admission."""
    source=source.resolve(strict=True);output=output.resolve()
    if output.is_relative_to(source) or source.is_relative_to(output):
        raise support.ValidationRefused('import source and output roots must be separate')
    output.mkdir(parents=True,exist_ok=False)
    record={'schema':SCHEMA,'status':'WORKING','started_utc':support.utc_now(),'orders':[]}
    try:
        require_source_only_imports(source)
        initial=partition.source_digest(source);rows=roster(source)
        record.update(source_sha256=initial,roster_sha256=roster_digest(rows),roster=rows,
            scope_counts=dict(Counter(row['role'] for row in rows)),
            machinery_sha256=machinery_digest())
        child_env=partition.test_environment(source,env)
        environment=support.admit_environment(python,output=output/'environment',env=child_env)
        if environment['status']!='READY':
            raise support.ValidationRefused('existing interpreter refused before import smoke')
        resolved=Path(environment['resolved_executable'])
        record['environment_identity_sha256']=environment['identity_sha256']
        if sys.platform != 'darwin' or shutil.which('sandbox-exec') is None:
            raise support.ValidationRefused('No admitted controlled-import backend on this host; macOS sandbox-exec is required')
        context={'source_sha256':initial,'environment_sha256':environment['identity_sha256'],'machinery_sha256':machinery_digest()}
        font = (prepare_font_cache(source,output,resolved,environment,child_env,context) if font_cache_required(rows)
                else {'status':'NOT_REQUESTED','reason':'NO_STATIC_MATPLOTLIB_IMPORT'})
        record['font_cache']=font
        policy=import_contract.vendor_policy(source,admitted_runtime_reads(resolved,environment),child_env)
        record['vendor_policy']=policy
        record['sandbox']=admit_sandbox(source,output,resolved,child_env,environment=environment,font=font)
        production=[row for row in rows if row['role']=='PRODUCTION']
        csv_setters=[row for row in production if row['csv_setter']]
        for mode,selected in [('general',production),('csv',csv_setters)]:
            if not selected:
                if mode=='general':raise support.ValidationRefused('production import roster is empty')
                record['csv_roster_status']='NO_SETTERS_DISCOVERED'
                continue
            for order in ('forward','reverse'):
                chosen=selected if order=='forward' else list(reversed(selected))
                directory=output/(mode+'-'+order);scratch=directory/'scratch';scratch.mkdir(parents=True)
                for name in ['home','cache','matplotlib']:(scratch/name).mkdir()
                request={'source':str(source),'roster':chosen,'roster_sha256':roster_digest(chosen),'mode':mode,'order':order,'context':context,'runtime_roots':policy['runtime_roots'],'vendor_policy':policy,'font_cache':font}
                support.atomic_json(directory/'request.json',request)
                profile=directory/'profile.sb';worker=Path(__file__).with_name('_release_import_worker.py')
                profile.write_text(mac_profile(source,scratch,output/'controls',worker,resolved,environment,font))
                worker_env=dict(child_env,HOME=str(scratch/'home'),XDG_CACHE_HOME=str(scratch/'cache'),
                    MPLCONFIGDIR=font['request']['cache_root'] if font['status']=='PREPARED' else str(scratch/'matplotlib'),MPLBACKEND='Agg')
                command=[shutil.which('sandbox-exec'),'-f',str(profile),str(resolved),'-I',str(worker),
                    '--request',str(directory/'request.json'),'--scratch',str(scratch)]
                # The request is a read-only explicit input, alongside code and scratch.
                profile.write_text(profile.read_text()+'(allow file-read* (literal '+json.dumps(str(directory/'request.json'))+'))\n')
                watch=support.run_watched(command,cwd=scratch,log=directory/'worker.log',env=worker_env,timeout=600)
                trace=scratch/'trace.jsonl'
                result={'mode':mode,'order':order,'watch':watch,'profile_sha256':support.sha256_file(profile),
                    'worker_environment_sha256':hashlib.sha256(support.canonical_json(worker_env)).hexdigest()}
                record['orders'].append(result)
                if watch['stop_reason'] is not None or not trace.is_file():
                    raise support.ValidationRefused('shared import worker stopped or produced no trace')
                result.update(verify_worker(trace,chosen,order,mode,
                    validate_required=(source/'mamey/validate.py').is_file(),source=source,policy=policy,font=font,context=context),trace_sha256=support.sha256_file(trace))
                if watch['exit_code'] != (0 if result['status'] in IMPORT_READY_STATES else 2):
                    raise support.ValidationRefused('worker exit differs from recorded import outcomes')
                support.atomic_json(output/'import-smoke.json',record)
        require_source_only_imports(source)
        record['source_after_sha256']=partition.source_digest(source)
        if record['source_after_sha256']!=initial:raise support.ValidationRefused('source changed during controlled imports')
        record['status']=('PASS' if all(row['status']=='PASS' for row in record['orders']) else
            'READY_WITH_OPTIONAL_UNAVAILABLE' if all(row['status'] in IMPORT_READY_STATES for row in record['orders']) else 'HOLD')
        validate_font_evidence(source,output,font,environment,child_env)
    except (ValueError,OSError) as exc:
        record.update(status='REFUSED',reason=str(exc))
    record['completed_utc']=support.utc_now();support.atomic_json(output/'import-smoke.json',record)
    return record
