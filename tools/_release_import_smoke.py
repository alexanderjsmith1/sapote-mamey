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


SCHEMA = 'sapote-mamey.controlled-import-smoke.v1'
BLOCKED_CONTROLS = {'source_write','outside_read','native_outside_read','native_source_write',
                    'native_fork','native_network','fork','spawn_python','spawn_external','network'}


def machinery_digest() -> str:
    """Bind the worker, controller and all reused validation helpers."""
    import verify_external_validation_receipt as existing
    files = [Path(__file__), Path(__file__).with_name('_release_import_worker.py'),
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
                   'role':'TEST_OR_FIXTURE' if test else 'PRODUCTION', 'csv_setter':False, 'parse_error':None}
            try:
                tree = ast.parse(path.read_text(encoding='utf-8'))
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


def mac_profile(source: Path, scratch: Path, controls: Path, worker: Path, python: Path, environment: dict) -> str:
    """Permit installed runtime/source reads and scratch writes, denying work channels."""
    def quoted(path):
        return json.dumps(str(Path(path).resolve()))
    reads = [source, scratch, controls/'readonly', worker.parent,
             *admitted_runtime_reads(python, environment), Path('/System'), Path('/usr/lib'), Path('/usr/share'), Path('/private/etc')]
    profile = ['(version 1)', '(import "system.sb")', '(deny default)',
        '(deny network*)', '(deny process-fork)', '(allow file-read-metadata)',
        '(allow file-read* '+ ' '.join('(subpath '+quoted(path)+')' for path in reads)
            +' (literal "/dev/null") (literal "/dev/random") (literal "/dev/urandom"))',
        '(allow file-write* (subpath '+quoted(scratch)+') (literal "/dev/null"))',
        '(allow process-exec (literal '+quoted(python)+'))', '(allow sysctl-read)', '(allow mach-lookup)']
    return '\n'.join(profile)+'\n'


PROBE = r'''
import ctypes, errno, json, os, socket, struct, subprocess, sys
from pathlib import Path
scratch=Path(sys.argv[1]);readonly=Path(sys.argv[2]);outside=Path(sys.argv[3]);port=int(sys.argv[4])
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
sys.stdout.write(json.dumps(results,sort_keys=True))
'''


def admit_sandbox(source: Path, output: Path, python: Path, env: dict[str,str], *, environment=None) -> dict:
    """Prove controls on owned canaries before any production module import."""
    if sys.platform != 'darwin' or shutil.which('sandbox-exec') is None:
        raise support.ValidationRefused('No admitted controlled-import backend on this host; macOS sandbox-exec is required')
    controls = output/'controls';scratch = controls/'scratch'
    scratch.mkdir(parents=True);(controls/'readonly').mkdir();(controls/'outside').mkdir()
    readonly = controls/'readonly/canary';readonly.write_text('readonly canary')
    outside = controls/'outside/canary';outside.write_text('private-read canary')
    worker = Path(__file__).with_name('_release_import_worker.py')
    profile = controls/'profile.sb';profile.write_text(mac_profile(source,scratch,controls,worker,python,environment))
    with socket.socket() as listener:
        listener.bind(('127.0.0.1',0));listener.listen(8)
        command = [shutil.which('sandbox-exec'),'-f',str(profile),str(python),'-I','-c',PROBE,
            str(scratch),str(readonly),str(outside),str(listener.getsockname()[1])]
        watch = support.run_watched(command,cwd=scratch,log=controls/'probe.log',env=env,timeout=20)
    if watch['exit_code'] != 0 or watch['stop_reason'] is not None:
        raise support.ValidationRefused('controlled-import sandbox probe failed; inspect controls/probe.log')
    measured = json.loads((controls/'probe.log').read_text())
    expected = BLOCKED_CONTROLS
    if (set(measured) != expected|{'scratch_write','source_read'}
        or not all(measured[name].get('blocked') is True for name in expected)
        or not measured['scratch_write'].get('allowed') or not measured['source_read'].get('allowed')
        or readonly.read_text()!='readonly canary'):
        raise support.ValidationRefused('sandbox did not enforce every required control; no imports admitted')
    report = {'schema':'sapote-mamey.import-sandbox-admission.v1','status':'ADMITTED', 'backend':'macOS sandbox-exec',
        'backend_sha256':support.sha256_file(Path(shutil.which('sandbox-exec'))),
        'profile_sha256':support.sha256_file(profile),'measured':measured,'watch':watch}
    support.atomic_json(controls/'admission.json',report)
    return report


def verify_worker(trace: Path, selected: list[dict], order: str, mode: str, *, validate_required=False) -> dict:
    """Require a complete one-to-one roster and terminal trace, never infer a green exit."""
    events = [json.loads(line) for line in trace.read_text().splitlines()]
    digest = roster_digest(selected)
    if (not events or events[0].get('type')!='start' or events[-1].get('type')!='complete'
            or events[0].get('roster_sha256') != digest or events[-1].get('roster_sha256') != digest):
        raise support.ValidationRefused('shared import trace is incomplete or its roster binding differs')
    rows = [entry for entry in events if entry.get('type')=='module']
    if ([entry.get('path') for entry in rows] != [entry['path'] for entry in selected]
        or [entry.get('module') for entry in rows] != [entry['module'] for entry in selected]
        or len(events)!=len(selected)+2 or events[-1].get('results')!=[{key:value for key,value in entry.items() if key!='type'} for entry in rows]
        or any(event.get('order',order)!=order or event.get('mode',mode)!=mode for event in events)):
        raise support.ValidationRefused('shared import outcomes omit, duplicate or change declared modules')
    for row in rows:
        if row.get('status') not in {'PASS','HOLD'}:
            raise support.ValidationRefused('shared import module outcome is unknown')
        if row.get('status') == 'PASS':
            checks = row.get('csv_checks', [])
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
            if (phases != expected
                or any(check.get('value', 0) < min(sys.maxsize,2**31-1) for check in checks)
                or row.get('exception_type') or row.get('csv_guard')
                or row.get('operations') or row.get('state_changes')):
                raise support.ValidationRefused('shared import PASS contradicts its CSV checks or exception')
    status = 'PASS' if all(row.get('status')=='PASS' and not row.get('operations') and not row.get('state_changes')
                               and row.get('csv_limit_after',0)>=min(sys.maxsize,2**31-1) for row in rows) else 'HOLD'
    if events[-1].get('status') != status or events[-1].get('count') != len(selected):
        raise support.ValidationRefused('shared import summary differs from actual module outcomes')
    return {'status':status,'modules':len(rows),'held':sum(row['status']!='PASS' for row in rows), 'results':rows}


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
    require(data.get('schema') == SCHEMA and data.get('status') in {'PASS','HOLD'}, 'import receipt is incomplete or refused')
    partition.contract.validate_age(data)
    source_hash = partition.source_digest(source); rows = roster(source)
    require(data.get('source_sha256') == data.get('source_after_sha256') == source_hash, 'import source binding mismatch')
    require(data.get('roster') == rows and data.get('roster_sha256') == roster_digest(rows)
            and data.get('scope_counts') == dict(Counter(row['role'] for row in rows)), 'import roster binding mismatch')
    require(data.get('machinery_sha256') == machinery_digest(), 'import machinery binding mismatch')
    require(data.get('environment_identity_sha256') == environment_identity_sha256, 'import environment binding mismatch')
    environment = json.loads((root/'environment/environment.json').read_text())
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
    require(measured == sandbox.get('measured') and set(measured) == BLOCKED_CONTROLS|{'scratch_write','source_read'}
            and all(measured[name].get('blocked') is True for name in BLOCKED_CONTROLS)
            and measured['scratch_write'].get('allowed') is True and measured['source_read'].get('allowed') is True,
            'sandbox control evidence is incomplete or permissive')
    check_watch(sandbox.get('watch', {}), root/'controls/probe.log', 20, 0)
    python = Path(environment['resolved_executable']); worker = Path(__file__).with_name('_release_import_worker.py')
    probe_watch = sandbox['watch']; old_scratch = Path(probe_watch.get('cwd',''))
    require(old_scratch.is_absolute() and old_scratch.parts[-2:] == ('controls','scratch'), 'sandbox probe location differs')
    old_root = old_scratch.parent.parent
    require((root/'controls/profile.sb').read_text() == mac_profile(source,old_scratch,old_root/'controls',worker,python,environment),
            'sandbox probe policy differs')
    probe_argv = probe_watch.get('argv', [])
    port = str(probe_argv[-1]) if probe_argv else ''
    require(port.isdecimal() and 0 < int(port) < 65536, 'sandbox probe listener port is invalid')
    command = [backend,'-f',str(old_root/'controls/profile.sb'),str(python),'-I','-c',PROBE,
        str(old_scratch),str(old_root/'controls/readonly/canary'),str(old_root/'controls/outside/canary'),port]
    nice = shutil.which('nice')
    require(probe_argv == ([nice,'-n','15',*command] if nice else command), 'sandbox probe command differs')
    child_env = partition.test_environment(source,env)
    require(hashlib.sha256(support.canonical_json(child_env)).hexdigest() == environment.get('test_environment_sha256'),
            'current import environment variables differ')
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
                               validate_required=(source/'mamey/validate.py').is_file())
        require(all(recorded.get(key) == value for key,value in actual.items()), 'recorded import outcomes differ from trace')
        require(support.sha256_file(directory/'scratch/trace.jsonl') == recorded.get('trace_sha256'), 'import trace hash differs')
        require(support.sha256_file(directory/'profile.sb') == recorded.get('profile_sha256'), 'import profile hash differs')
        request = json.loads((directory/'request.json').read_text())
        require(request == {'source':str(source),'roster':selected,'roster_sha256':roster_digest(selected),'mode':mode,'order':order},
                'import request binding differs')
        original_scratch = Path(watch.get('cwd', ''))
        require(original_scratch.is_absolute() and original_scratch.parts[-2:] == (mode+'-'+order,'scratch'),
                'import worker scratch location is invalid')
        original_root = original_scratch.parent.parent
        expected_profile = mac_profile(source,original_scratch,original_root/'controls',worker,python,environment)
        expected_profile += '(allow file-read* (literal '+json.dumps(str(original_scratch.parent/'request.json'))+'))\n'
        require((directory/'profile.sb').read_text() == expected_profile, 'import profile policy differs')
        command = [backend,'-f',str(original_scratch.parent/'profile.sb'),str(python),'-I',str(worker),
                   '--request',str(original_scratch.parent/'request.json'),'--scratch',str(original_scratch)]
        nice = shutil.which('nice')
        require(watch.get('argv') == ([nice,'-n','15',*command] if nice else command), 'import worker command differs')
        worker_env = dict(child_env,HOME=str(original_scratch/'home'),XDG_CACHE_HOME=str(original_scratch/'cache'),
                          MPLCONFIGDIR=str(original_scratch/'matplotlib'),MPLBACKEND='Agg')
        require(hashlib.sha256(support.canonical_json(worker_env)).hexdigest() == recorded.get('worker_environment_sha256'),
                'import worker environment differs')
        check_watch(watch,directory/'worker.log',600,0 if actual['status']=='PASS' else 2)
    status = 'PASS' if all(row['status']=='PASS' for row in orders) else 'HOLD'
    require(data['status'] == status, 'import root summary differs from outcomes')
    require(not require_pass or status == 'PASS', 'complete import roster has unresolved HOLD outcomes')
    watches = [*environment['steps'],sandbox['watch'],*[row['watch'] for row in orders]]
    return {'status':status,'scope_counts':data['scope_counts'],
            'rss_sampling':{'zero_peak_records':sum(watch['peak_process_tree_rss']==0 for watch in watches),
                            'meaning':'Periodic observations only; zero means no positive RSS sample before exit, not zero memory use.'},
            'orders':[{key:entry[key] for key in ['mode','order','modules','held','status']} for entry in orders]}


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
        record['sandbox']=admit_sandbox(source,output,resolved,child_env,environment=environment)
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
                request={'source':str(source),'roster':chosen,'roster_sha256':roster_digest(chosen),'mode':mode,'order':order}
                support.atomic_json(directory/'request.json',request)
                profile=directory/'profile.sb';worker=Path(__file__).with_name('_release_import_worker.py')
                profile.write_text(mac_profile(source,scratch,output/'controls',worker,resolved,environment))
                worker_env=dict(child_env,HOME=str(scratch/'home'),XDG_CACHE_HOME=str(scratch/'cache'),
                    MPLCONFIGDIR=str(scratch/'matplotlib'),MPLBACKEND='Agg')
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
                    validate_required=(source/'mamey/validate.py').is_file()),trace_sha256=support.sha256_file(trace))
                if watch['exit_code'] != (0 if result['status']=='PASS' else 2):
                    raise support.ValidationRefused('worker exit differs from recorded import outcomes')
                support.atomic_json(output/'import-smoke.json',record)
        require_source_only_imports(source)
        record['source_after_sha256']=partition.source_digest(source)
        if record['source_after_sha256']!=initial:raise support.ValidationRefused('source changed during controlled imports')
        record['status']='PASS' if all(row['status']=='PASS' for row in record['orders']) else 'HOLD'
    except (ValueError,OSError) as exc:
        record.update(status='REFUSED',reason=str(exc))
    record['completed_utc']=support.utc_now();support.atomic_json(output/'import-smoke.json',record)
    return record
