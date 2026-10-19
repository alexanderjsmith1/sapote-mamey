"""Controlled shared-interpreter worker; importing this file performs no work."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
import importlib.util
import io
import stat
import json
import logging
import os
from pathlib import Path
import resource
import sys
import threading
import time
import types
from importlib.machinery import EXTENSION_SUFFIXES


_font_spec = importlib.util.spec_from_file_location('_release_font_cache_machinery', Path(__file__).with_name('_release_font_cache.py'))
_font_cache = importlib.util.module_from_spec(_font_spec)
sys.modules[_font_spec.name] = _font_cache
_font_bytecode = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    _font_spec.loader.exec_module(_font_cache)
finally:
    sys.dont_write_bytecode = _font_bytecode

THRESHOLD = min(sys.maxsize, 2**31 - 1)


class ImportOperationRefused(RuntimeError):
    """An import attempted work outside the declared no-analysis policy."""


def digest(value) -> str:
    """Hash selected state without exposing environment values."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()



IMPORT_READY_STATES = frozenset({'PASS', 'READY_WITH_OPTIONAL_UNAVAILABLE'})
WORKER_SCHEMA = 'sapote-mamey.shared-import-worker.v2'
PATH_SCHEMA = 'sapote-mamey.trusted-import-path-equivalence.v1'
OPTIONAL_SCHEMA = 'sapote-mamey.vendored-ijson-availability.v1'


def _file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pack_paths(paths):
    """Lossless table encoding avoids repeating long approved paths hundreds of times."""
    values = []; indices = []; lookup = {}
    for value in paths:
        key = json.dumps(value, sort_keys=True)
        if key not in lookup:
            lookup[key] = len(values); values.append(value)
        indices.append(lookup[key])
    return {'values': values, 'indices': indices}


def unpack_paths(packed):
    if not isinstance(packed, dict) or set(packed) != {'values', 'indices'} or not isinstance(packed['values'], list) or not isinstance(packed['indices'], list):
        raise ValueError('path evidence encoding differs')
    if any(type(index) is not int or not 0 <= index < len(packed['values']) for index in packed['indices']):
        raise ValueError('path evidence index is invalid')
    paths = [packed['values'][index] for index in packed['indices']]
    if pack_paths(paths) != packed:
        raise ValueError('path evidence encoding is not canonical')
    return paths



def supported_paths(paths):
    """Only exact strings are supported import-path entries, including baselines."""
    return isinstance(paths,list) and all(type(value) is str for value in paths)


def unsupported_path_guard(before, after):
    """Keep typed unsupported observations without granting readiness."""
    if supported_paths(before) and supported_paths(after):
        return None
    return {'status':'HOLD','reason':'UNSUPPORTED_MODULE_SEARCH_PATH_ENTRY',
            'before':pack_paths(before),'after':pack_paths(after)}


def _path_kind(path):
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(mode):
        raise ValueError('trusted import entry contains symlink')
    if stat.S_ISDIR(mode):
        return 'directory'
    if stat.S_ISREG(mode):
        return 'file'
    raise ValueError('trusted import entry is nonregular')


def _module_entry(directory, name):
    """Model standard file-finder precedence without importing any module."""
    package = directory/name
    package_kind = _path_kind(package)
    if package_kind == 'directory':
        for suffix in (*EXTENSION_SUFFIXES, '.py', '.pyc'):
            candidate = package/('__init__'+suffix)
            if _path_kind(candidate) == 'file':
                return ('package', str(candidate.resolve()))
    for suffix in (*EXTENSION_SUFFIXES, '.py', '.pyc'):
        candidate = directory/(name+suffix)
        if _path_kind(candidate) == 'file':
            return ('module', str(candidate.resolve()))
    return ('namespace', str(package.resolve())) if package_kind == 'directory' else None


def _import_names(directory):
    names = set()
    for path in directory.iterdir():
        kind = _path_kind(path)
        if kind is None:
            raise ValueError('trusted import entry disappeared')
        if kind == 'directory' and path.name.isidentifier():
            names.add(path.name)
        elif kind == 'file':
            for suffix in (*EXTENSION_SUFFIXES, '.py', '.pyc'):
                if path.name.endswith(suffix):
                    name = path.name[:-len(suffix)]
                    if name.isidentifier():
                        names.add(name)
                    break
    return names


def _resource_tree(directory):
    """Bind namespace resources and reject link/file-directory ambiguities."""
    rows = {}
    def fail(error):
        raise error
    for parent, directories, names in os.walk(directory, followlinks=False, onerror=fail):
        for name in sorted(directories+names):
            path = Path(parent)/name
            relative = path.relative_to(directory).as_posix().casefold()
            kind = _path_kind(path)
            if kind is None or relative in rows:
                raise ValueError('namespace resource is ambiguous')
            rows[relative] = kind
    return rows


def _winner(directories, name):
    namespaces = []
    for directory in directories:
        entry = _module_entry(directory, name)
        if entry and entry[0] != 'namespace':
            return entry, []
        if entry:
            namespaces.append(Path(entry[1]))
    return None, namespaces


def _namespace_proof(before, after, qualified, checks):
    """Check every concrete leaf and resource of merged namespace portions."""
    before = list(dict.fromkeys(before)); after = list(dict.fromkeys(after))
    if set(before) != set(after):
        raise ValueError('namespace portions changed: '+qualified)
    trees = [_resource_tree(path) for path in before]
    for i, left in enumerate(trees):
        for right in trees[i+1:]:
            conflicts = [name for name in left.keys() & right.keys()
                         if left[name] != 'directory' or right[name] != 'directory']
            if conflicts:
                raise ValueError('namespace resource collision: '+qualified+'/'+sorted(conflicts)[0])
    checks.append({'namespace': qualified, 'portions': sorted(map(str, before)),
                   'resource_tree_sha256': digest([sorted(tree.items()) for tree in trees])})
    names = sorted(set().union(*(_import_names(path) for path in before)))
    for name in names:
        one, ns_one = _winner(before, name); two, ns_two = _winner(after, name)
        if one != two:
            raise ValueError('namespace module origin collision: '+qualified+'.'+name)
        if one is None and ns_one:
            _namespace_proof(ns_one, ns_two, qualified+'.'+name, checks)


def trusted_path_equivalence(source, before, after):
    """Normalize only proven leading approved-root changes; preserve raw proof."""
    source = Path(source).resolve(strict=True)
    approved = [str(source/'tools'), str(source)]
    proof = {'schema': PATH_SCHEMA, 'before': pack_paths(before) if isinstance(before,list) else before, 'after': pack_paths(after) if isinstance(after,list) else after,
             'approved_roots': approved, 'equivalent': False}
    if not isinstance(before, list) or not isinstance(after, list) or any(
            type(value) is not str for value in [*before, *after]):
        return proof | {'reason': 'unsupported path entry'}
    if before == after:
        return proof | {'equivalent': True, 'reason': 'unchanged'}
    def split(paths):
        prefix = []
        for value in paths:
            if not value or not Path(value).is_absolute():
                break
            canonical = str(Path(value).resolve())
            if canonical not in approved:
                break
            prefix.append(canonical)
        return prefix, paths[len(prefix):]
    one, tail_one = split(before); two, tail_two = split(after)
    if set(one) != set(approved) or set(two) != set(approved) or tail_one != tail_two:
        return proof | {'reason': 'not an isolated leading approved-root change'}
    if any(value and Path(value).is_absolute() and str(Path(value).resolve()) in approved for value in tail_one):
        return proof | {'reason': 'approved root outside leading block'}
    left = list(dict.fromkeys(map(Path, one))); right = list(dict.fromkeys(map(Path, two)))
    checks = []; resolutions = []
    try:
        names = sorted(set().union(*(_import_names(path) for path in left)))
        for name in names:
            first, ns_first = _winner(left, name); second, ns_second = _winner(right, name)
            if first != second:
                raise ValueError('concrete module/package origin collision: '+name)
            resolutions.append([name, first])
            if first is None and ns_first:
                _namespace_proof(ns_first, ns_second, name, checks)
    except (OSError, ValueError) as exc:
        return proof | {'reason': str(exc)}
    return proof | {'equivalent': True, 'reason': 'proven leading trusted-root equivalence',
                    'resolution_count': len(resolutions), 'resolution_sha256': digest(resolutions),
                    'namespace_checks': checks}


# Filled from the exact source155 vendored3.5.0 bytes by the proposal builder.
VENDOR_PINS = {'mamey/_vendor/ijson/__init__.py': '81ed045d45c8b79dd9de89ea4607988c01159b8bb2064d3431758a6628683134', 'mamey/_vendor/ijson/common.py': '9386ea5c8b9f2cf951b385e2bb8b57b31a2ce1da8f6046ec26738cf39f34f0d9', 'mamey/_vendor/ijson/version.py': 'ead542dc59545eac19208042670fab48161625f9a5a35978d81f06987be0e67d', 'mamey/_vendor/ijson/backends/__init__.py': '937acec96f63d5ce6bbdc2df10f7862dbaf117693111814cef8b89aa8f2feac8', 'mamey/_vendor/ijson/backends/_yajl2_ctypes_common.py': '57e8f7e541054aec920ada3b2bf7b67b5d628f52dd2ffd1b06aa958906e41d2a', 'mamey/_vendor/ijson/backends/python.py': 'ea1d1df5236aca793454929197084e821215ca1af56b59ed5c743c820ad6d3f4', 'mamey/_vendor/ijson/backends/yajl.py': '655a5a5c0f8b74eff21e00ce534d56b4c31c8dc1485a82e44f6aa12b5f82bcf0', 'mamey/_vendor/ijson/backends/yajl2.py': '10f14730ab3fb076137c9352f93c92585d1f761e2904413379dce0579092191e', 'mamey/_vendor/ijson/backends/yajl2_c.py': 'bdaf82803d13e9da509a6f1066635282ed0e972f331406557e082bab96d9f3a4', 'mamey/_vendor/ijson/backends/yajl2_cffi.py': '94cb5d69e447ba3bb56762fae90f725810466d9ba755efa0b85b53f8baeb6eed'}
VENDOR_BASE = 'mamey/_vendor/ijson/'
OPTIONAL_BACKENDS = {'yajl', 'yajl2', 'yajl2_c', 'yajl2_cffi'}
RUNTIME_COMMON_SHA256 = 'aa791ea098889306331bdec1e1f3bae0cfd4a78af73e9094ae0138e1b050de91'
FALLBACK_MODULE = 'mamey._vendor.ijson.backends.python'
FALLBACK_INVALID_INPUTS = [('incomplete',b'{"import_contract":','IncompleteJSONError'),
    ('malformed',b'{"import_contract":]}','UnexpectedSymbol'),('trailing_garbage',b'{} garbage','JSONError')]
FALLBACK_EVENTS = [('start_map', None), ('map_key', 'import_contract'),
                   ('start_array', None), ('number', 1), ('boolean', True), ('null', None),
                   ('end_array', None), ('end_map', None)]


def vendor_policy(source, runtime_roots, environment=None):
    """Exact vendor identity, not a generic optional-exception skip list."""
    source = Path(source)
    environment = os.environ if environment is None else environment
    present = (source/VENDOR_BASE).is_dir()
    matched = present and all((source/relative).is_file() and not (source/relative).is_symlink()
                              and _file_sha(source/relative) == value for relative, value in VENDOR_PINS.items())
    return {'schema': OPTIONAL_SCHEMA, 'status': 'PINNED_VENDOR' if matched else 'UNRECOGNIZED_VENDOR' if present else 'NOT_PRESENT',
            'vendor_version': '3.5.0', 'source_pins': VENDOR_PINS if matched else {},
            'runtime_roots': list(map(str, runtime_roots)),
            'explicit_backend': environment.get('IJSON_BACKEND'),
            'explicit_yajl_dll': 'YAJL_DLL' in environment}


def _permitted_origin(path, source, runtime_roots):
    path = Path(path).resolve()
    vendor = (Path(source)/VENDOR_BASE).resolve()
    return path.is_relative_to(vendor) or any(path.is_relative_to(Path(root).resolve()) for root in runtime_roots)


def exception_evidence(exc, source, runtime_roots):
    """Retain expected dependency origins without reading foreign files."""
    def bound_file(value):
        if not value or str(value).startswith('<'):
            return None
        path = Path(value).resolve()
        if not _permitted_origin(path, source, runtime_roots) or not path.is_file():
            return {'path': str(path), 'sha256': None}
        return {'path': str(path), 'sha256': _file_sha(path)}
    owner = sys.modules.get(type(exc).__module__)
    frames = []; trace = exc.__traceback__
    while trace is not None:
        item = bound_file(trace.tb_frame.f_code.co_filename)
        if item:
            frames.append(item | {'function': trace.tb_frame.f_code.co_name, 'line': trace.tb_lineno})
        trace = trace.tb_next
    contexts = []; seen = {id(exc)}; child = exc.__cause__ or exc.__context__
    while child is not None and id(child) not in seen:
        seen.add(id(child))
        contexts.append({'type':type(child).__name__,'type_module':type(child).__module__,
                         'name':getattr(child,'name',None),'message':str(child),'errno':getattr(child,'errno',None)})
        child = child.__cause__ or child.__context__
    return {'type': type(exc).__name__, 'type_module': type(exc).__module__,
            'name': getattr(exc, 'name', None), 'message': str(exc),
            'class_origin': bound_file(getattr(owner, '__file__', None)), 'frames': frames, 'contexts':contexts}


def clean_library_absence(evidence):
    contexts = evidence.get('contexts', [])
    if not contexts or contexts[0].get('type') != 'OSError' or contexts[0].get('type_module') != 'builtins':
        return False
    message = ' '.join(item.get('message','') for item in contexts).lower()
    forbidden = ('architecture','invalid elf','wrong elf','invalid mach','not a mach','symbol not found',
                 'undefined symbol','file too short','code signature','operation not permitted','permission denied','bad cpu')
    return (not any(token in message for token in forbidden)
            and (contexts[0].get('errno') == 2 or 'no such file' in message or 'image not found' in message))



def optional_unavailability(source, entry, evidence, policy):
    """Recognize only exact clean dependency absence for known vendor code."""
    module = entry['module']; backend = module.rsplit('.', 1)[-1]
    if policy['status'] != 'PINNED_VENDOR' or backend not in OPTIONAL_BACKENDS or module != 'mamey._vendor.ijson.backends.'+backend:
        return None
    if policy['explicit_backend'] == backend or policy['explicit_yajl_dll']:
        return None
    expected = Path(source)/(VENDOR_BASE+'backends/'+backend+'.py')
    if entry['path'] != expected.relative_to(source).as_posix() or entry['sha256'] != VENDOR_PINS[entry['path']]:
        return None
    if not any(frame['path'] == str(expected.resolve()) and frame['sha256'] == entry['sha256'] for frame in evidence['frames']):
        return None
    reason = None
    if backend == 'yajl2_c':
        directory = expected.parent
        native_present = any(((directory/('_yajl2'+suffix)).exists() or (directory/('_yajl2'+suffix)).is_symlink()) for suffix in (*EXTENSION_SUFFIXES, '.py', '.pyc'))
        if not native_present and evidence['type_module'] == 'builtins' and ((evidence['type'] == 'ImportError'
                and evidence.get('name') == 'mamey._vendor.ijson.backends'
                and evidence['message'] == "cannot import name '_yajl2' from 'mamey._vendor.ijson.backends' ("+str(expected.parent/'__init__.py')+")")
                or (evidence['type'] == 'ModuleNotFoundError' and evidence['name'] == 'mamey._vendor.ijson.backends._yajl2'
                    and evidence['message'] == "No module named 'mamey._vendor.ijson.backends._yajl2'")):
            reason = 'VENDORED_NATIVE_EXTENSION_NOT_SHIPPED'
    elif evidence['type'] == 'YAJLImportError' and evidence['type_module'] in {'ijson.backends', 'mamey._vendor.ijson.backends'} and evidence['message'] in {'YAJL shared object not found.', 'Unable to load YAJL.'}:
        origin = evidence.get('class_origin') or {}
        allowed = origin.get('sha256') == VENDOR_PINS[VENDOR_BASE+'backends/__init__.py'] and origin.get('path', '').endswith('/ijson/backends/__init__.py')
        allowed = allowed and _permitted_origin(origin.get('path', ''), source, policy['runtime_roots'])
        finder = 'find_yajl_cffi' if backend == 'yajl2_cffi' else 'find_yajl_ctypes'
        allowed = allowed and (backend != 'yajl2_cffi' or evidence['message'] == 'Unable to load YAJL.')
        allowed = allowed and any(frame['sha256'] == origin['sha256']
                                  and frame['path'] == origin['path']
                                  and frame['function'] == finder
                                  for frame in evidence['frames'])
        # This exact pinned CFFI finder can report lookup absence without errno.
        # Keep the generic loader-error predicate unchanged for every other case.
        cffi_lookup_absent = (allowed and backend == 'yajl2_cffi'
            and evidence['type_module'] == 'ijson.backends' and evidence.get('name') is None
            and evidence.get('contexts') == [{'type':'OSError','type_module':'builtins','name':None,'errno':None,
                'message':"ctypes.util.find_library() did not manage to locate a library called 'yajl'"}]
            and any(frame['path'] == str(expected.resolve()) and frame['sha256'] == entry['sha256']
                    and frame['function'] == '<module>' and frame['line'] == 63 for frame in evidence['frames'])
            and any(frame['path'] == origin['path'] and frame['sha256'] == origin['sha256']
                    and frame['function'] == 'find_yajl_cffi' and frame['line'] == 53 for frame in evidence['frames']))
        allowed = allowed and (evidence['message'] != 'Unable to load YAJL.'
                               or clean_library_absence(evidence) or cffi_lookup_absent)
        if allowed:
            reason = 'YAJL_LIBRARY_UNAVAILABLE_IN_ADMITTED_ENV'
    elif backend == 'yajl2_cffi' and evidence['type'] == 'ModuleNotFoundError' and evidence['type_module'] == 'builtins' and evidence['name'] == 'cffi' and evidence['message'] == "No module named 'cffi'":
        reason = 'OPTIONAL_CFFI_UNAVAILABLE'
    if reason is None:
        return None
    return {'schema': OPTIONAL_SCHEMA, 'status': 'OPTIONAL_UNAVAILABLE', 'module': module,
            'reason': reason, 'vendor_policy_sha256': digest(policy), 'exception': evidence,
            'required_fallback': FALLBACK_MODULE}


def common_dependency_matches(path, source, policy):
    path = Path(path).resolve()
    expected = (Path(source)/(VENDOR_BASE+'common.py')).resolve()
    pinned = VENDOR_PINS[VENDOR_BASE+'common.py'] if path == expected else RUNTIME_COMMON_SHA256
    return _permitted_origin(path,source,policy['runtime_roots']) and _file_sha(path) == pinned


def check_python_fallback(loaded, source, policy):
    """Tiny fixed JSON capability check at its normal roster position."""
    common_path = Path(loaded.common.__file__).resolve()
    if (loaded.backend_name != 'python' or not common_dependency_matches(common_path, source, policy)):
        raise ImportOperationRefused('required Python JSON backend dependency origin differs')
    valid = b'{"import_contract":[1,true,null]}'
    events = list(loaded.basic_parse(io.BytesIO(valid)))
    if events != FALLBACK_EVENTS:
        raise ImportOperationRefused('required Python JSON backend returned unexpected events')
    invalid = []
    for label,payload,expected in FALLBACK_INVALID_INPUTS:
        try:
            list(loaded.basic_parse(io.BytesIO(payload)))
        except Exception as exc:
            allowed = {'ijson.backends.python','mamey._vendor.ijson.backends.python'} if expected == 'UnexpectedSymbol' else {'ijson.common','mamey._vendor.ijson.common'}
            if type(exc).__name__ != expected or type(exc).__module__ not in allowed:
                raise ImportOperationRefused('required Python JSON backend has unexpected invalid-input behavior') from exc
        else:
            raise ImportOperationRefused('required Python JSON backend accepted invalid JSON')
        invalid.append({'case':label,'input_sha256':hashlib.sha256(payload).hexdigest(),'exception':expected})
    return {'status': 'PASS', 'backend': 'python', 'valid_input_sha256': hashlib.sha256(valid).hexdigest(),
            'events_sha256': digest(FALLBACK_EVENTS), 'invalid_inputs': invalid,
            'common_origin': {'path': str(common_path), 'sha256': _file_sha(common_path)}}


def directory_identity(path):
    """Real lstat identity for an existing private cache directory, never a link."""
    path = Path(path)
    for parent in [*reversed(path.parents), path]:
        if parent.is_symlink():
            raise ValueError('cache directory path contains symlink')
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o700 or info.st_uid != os.getuid():
        raise ValueError('cache directory is not private and owned')
    return {'device': info.st_dev, 'inode': info.st_ino, 'mode': stat.S_IMODE(info.st_mode),
            'uid': info.st_uid, 'links': info.st_nlink, 'size': info.st_size,
            'mtime_ns': info.st_mtime_ns, 'ctime_ns': info.st_ctime_ns}


def font_directory_candidate(path, mode, dir_fd, font):
    """Only pinned Matplotlib's exist_ok probe of the exact prepared cache."""
    if font.get('status') != 'PREPARED' or dir_fd is not None or type(mode) is not int or mode != 0o777 or not isinstance(path, (str, bytes, Path)):
        return None
    request = font['request']; named = Path(os.fsdecode(path))
    target = Path(request['cache_root'])
    if not named.is_absolute() or '..' in named.parts or named != target:
        return None
    try:
        identity = directory_identity(named)
    except (OSError, ValueError):
        return None
    frame = sys._getframe(1); pathlib_ok = False; mpl_ok = False
    while frame is not None:
        # Python 3.13 moved Path.mkdir into pathlib._local; 3.12 defines it in pathlib.
        if frame.f_globals.get('__name__') in ('pathlib', 'pathlib._local') and frame.f_code.co_name == 'mkdir':
            pathlib_ok = frame.f_locals.get('exist_ok') is True and Path(frame.f_locals.get('self')) == target
        if (frame.f_code.co_name == '_get_config_or_cache_dir'
                and Path(frame.f_code.co_filename).resolve() == Path(request['dependency']['root'])/'__init__.py'):
            mpl_ok = True
        frame = frame.f_back
    if not pathlib_ok or not mpl_ok:
        return None
    caller = Path(request['dependency']['root'])/'__init__.py'
    return {'path': str(target), 'before': identity, 'exist_ok': True, 'mkdir_mode': mode, 'dir_fd': None,
            'caller': {'path': str(caller), 'sha256': _file_sha(caller), 'function': '_get_config_or_cache_dir'},
            'request_payload_sha256': hashlib.sha256(_font_cache.canonical(request)).hexdigest(),
            'manifest_sha256': font['manifest_sha256']}


def blocking_operations(row, font):
    """Every raw event blocks unless its exact EEXIST no-op proof is complete."""
    operations = row.get('operations', [])
    proofs = row.get('directory_noops', [])
    accepted = set()
    for proof in proofs:
        index = proof.get('event_index')
        if type(index) is not int or not 0 <= index < len(operations) or index in accepted:
            raise ValueError('directory probe event index is invalid')
        event = operations[index]; request = font.get('request', {})
        before = proof.get('before', {}); after = proof.get('after', {})
        caller = proof.get('caller', {})
        if (font.get('status') != 'PREPARED' or event.get('event') != 'os.mkdir'
                or event.get('path') != request.get('cache_root') or proof.get('path') != event['path']
                or proof.get('result') != 'EEXIST' or proof.get('exist_ok') is not True
                or proof.get('mkdir_mode') != 0o777 or proof.get('dir_fd') is not None
                or event.get('mode') != 0o777 or event.get('dir_fd') is not None
                or before != after or set(before) != {'device', 'inode', 'mode', 'uid', 'links', 'size', 'mtime_ns', 'ctime_ns'}
                or any(type(value) is not int for value in before.values())
                or before['mode'] != 0o700 or before['uid'] != os.getuid() or before['inode'] <= 0
                or caller.get('path') != str(Path(request.get('dependency', {}).get('root', ''))/'__init__.py')
                or caller.get('function') != '_get_config_or_cache_dir'
                or not Path(caller['path']).is_file() or _file_sha(caller['path']) != caller.get('sha256')
                or proof.get('request_payload_sha256') != hashlib.sha256(_font_cache.canonical(request)).hexdigest()
                or proof.get('manifest_sha256') != font.get('manifest_sha256')):
            raise ValueError('directory probe is not a proven bound no-op')
        accepted.add(index)
    return [event for index, event in enumerate(operations) if index not in accepted]


def import_readiness(rows, policy):
    if any(row['status'] == 'HOLD' for row in rows):
        return 'HOLD'
    unavailable = [row for row in rows if row['status'] == 'OPTIONAL_UNAVAILABLE']
    if unavailable:
        fallback = [row for row in rows if row['module'] == FALLBACK_MODULE]
        if policy['status'] != 'PINNED_VENDOR' or len(fallback) != 1 or fallback[0]['status'] != 'PASS' or fallback[0].get('fallback_capability', {}).get('status') != 'PASS':
            return 'HOLD'
        return 'READY_WITH_OPTIONAL_UNAVAILABLE'
    return 'PASS'


def logger_state():
    """Ignore ordinary empty logger creation; retain configuration and handlers."""
    result = {}
    loggers = {'<root>': logging.getLogger(), **logging.Logger.manager.loggerDict}
    for name, logger in loggers.items():
        if not isinstance(logger, logging.Logger):
            continue
        if name != '<root>' and not logger.handlers and logger.level == logging.NOTSET and not logger.disabled:
            continue
        result[name] = {'level':logger.level, 'disabled':logger.disabled, 'propagate':logger.propagate,
            'handlers':[{'type':type(handler).__module__+'.'+type(handler).__qualname__,
                         'level':handler.level, 'formatter':digest(getattr(handler.formatter, '_fmt', None))}
                        for handler in logger.handlers]}
    return result


def global_state(source: Path, streams: tuple) -> dict:
    """Compare cwd, environment, CSV, logging, limits, threads and import paths."""
    limits = {}
    for name in ('RLIMIT_AS','RLIMIT_DATA','RLIMIT_RSS','RLIMIT_CPU','RLIMIT_NOFILE','RLIMIT_NPROC','RLIMIT_STACK','RLIMIT_CORE'):
        if hasattr(resource, name):
            limits[name] = list(resource.getrlimit(getattr(resource, name)))
    paths = [value if type(value) is str else {'unsupported_path_type': type(value).__name__} for value in sys.path]
    return {'cwd':str(Path.cwd()), 'environment':dict(os.environ), 'csv_limit':csv.field_size_limit(),
        'logging':logger_state(), 'resource_limits':limits,
        'threads':sorted((thread.name, thread.daemon) for thread in threading.enumerate()),
        'streams_unchanged':[sys.stdout is streams[0], sys.stderr is streams[1]], 'module_search_paths':paths}


def state_difference(before: dict, after: dict) -> dict:
    """Keep changed environment keys and hashes, never their values."""
    changes = {}
    for key in before:
        if key == 'csv_limit':
            if after[key] < THRESHOLD:
                changes[key] = {'before':before[key], 'after':after[key], 'minimum':THRESHOLD}
        elif key == 'environment':
            if before[key] != after[key]:
                changes[key] = {'changed_keys':sorted(k for k in before[key].keys() | after[key].keys()
                    if before[key].get(k) != after[key].get(k)), 'before_sha256':digest(before[key]), 'after_sha256':digest(after[key])}
        elif key == 'module_search_paths':
            if before[key] != after[key]:
                changes[key] = {'before': pack_paths(before[key]), 'after': pack_paths(after[key])}
        elif before[key] != after[key]:
            changes[key] = {'before':before[key], 'after':after[key]}
    return changes


def main(argv=None) -> int:
    """Execute the complete declared roster in one process and retain every outcome."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', required=True, type=Path)
    parser.add_argument('--scratch', required=True, type=Path)
    args = parser.parse_args(argv)
    request = json.loads(args.request.read_text())
    source = Path(request['source']).resolve(strict=True); scratch = args.scratch.resolve(strict=True)
    roster = request['roster']; order = request['order']; mode = request['mode']
    policy = vendor_policy(source, request['runtime_roots'], os.environ)
    if policy != request['vendor_policy']:
        raise ImportOperationRefused('vendor availability policy differs from bound request')
    font = request['font_cache']
    if font['status'] == 'PREPARED':
        font_path = Path(font['request']['output'])/'request.json'
        if _file_sha(font_path) != font['request_file_sha256'] or _font_cache.read_json(font_path) != font['request']:
            raise ImportOperationRefused('font request bytes differ')
        if font['request']['context'] != request['context']:
            raise ImportOperationRefused('font bootstrap context differs')
        _font_cache.validate_cache(font['request'], manifest_sha256=font['manifest_sha256'])
    elif font['status'] != 'NOT_REQUESTED':
        raise ImportOperationRefused('unknown font bootstrap status')
    sys.dont_write_bytecode = True
    sys.path[:0] = [str(source/'tools'), str(source)]
    if (source/'tools').is_dir() and not (source/'tools/__init__.py').is_file():
        package = types.ModuleType('tools');package.__path__ = [str(source/'tools')];package.__package__ = 'tools'
        package.__spec__ = importlib.machinery.ModuleSpec('tools', loader=None, is_package=True)
        sys.modules['tools'] = package
    sys.argv = ['import-smoke']
    null = os.open('/dev/null', os.O_RDONLY);os.dup2(null, 0);os.close(null)
    csv.field_size_limit(THRESHOLD)
    streams = (sys.stdout, sys.stderr)
    trace = (scratch/'trace.jsonl').open('x', encoding='utf-8')
    active = {'module':'<bootstrap>', 'operations':[], 'native_loads':[], 'trusted_write':False, 'directory_noops':[]}

    def record(event):
        active['trusted_write'] = True
        try:
            trace.write(json.dumps(event, sort_keys=True, default=str)+'\n');trace.flush();os.fsync(trace.fileno())
        finally:
            active['trusted_write'] = False

    def audit(event, arguments):
        if active['trusted_write']:
            return
        denied = (event.startswith('subprocess.') or event.startswith('os.exec') or event.startswith('os.spawn')
                  or event in {'os.system','os.fork','os.forkpty','socket.connect','socket.bind',
                               'resource.setrlimit'})
        # The admitted OS profile blocks native reads/writes, forks and sockets
        # below Python hooks. Obtaining a loader handle is normal initialization.
        if event == 'ctypes.dlopen':
            active['native_loads'].append(str(arguments[0]))
        if denied:
            active['operations'].append({'event':event, 'disposition':'BLOCKED'})
            raise ImportOperationRefused('import attempted protected operation: '+event)
        if event == 'open':
            path, mode, flags = arguments
            writing = (isinstance(mode, str) and any(character in mode for character in 'wax+')) or (
                isinstance(flags, int) and bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND)))
            if writing:
                active['operations'].append({'event':'file-write', 'path':os.fspath(path) if isinstance(path,(str,bytes,Path)) else '<fd>',
                                             'disposition':'CONTROLLED_SCRATCH_OR_OS_REFUSAL'})
        elif event in {'os.mkdir','os.remove','os.rename','os.rmdir','shutil.copyfile'}:
            item = {'event':event, 'disposition':'CONTROLLED_SCRATCH_OR_OS_REFUSAL',
                    'path':os.fsdecode(arguments[0]) if isinstance(arguments[0],(str,bytes,Path)) else '<fd>'}
            if event == 'os.mkdir':
                item.update(mode=arguments[1],dir_fd=None if arguments[2] == -1 else arguments[2])
            active['operations'].append(item)

    class TrackedStream:
        def __init__(self, stream, name):
            self.stream = stream; self.name = name
        def write(self, text):
            if text and not active['trusted_write']:
                active['operations'].append({'event':'terminal-write', 'stream':self.name,
                    'characters':len(text), 'sha256':hashlib.sha256(text.encode()).hexdigest()})
            return self.stream.write(text)
        def __getattr__(self, name):
            return getattr(self.stream, name)
    sys.stdout = TrackedStream(sys.stdout, 'stdout');sys.stderr = TrackedStream(sys.stderr, 'stderr')
    streams = (sys.stdout, sys.stderr)
    sys.addaudithook(audit)
    original_mkdir = os.mkdir
    def observed_mkdir(path, mode=0o777, *, dir_fd=None):
        candidate = font_directory_candidate(path, mode, dir_fd, font)
        index = len(active['operations'])
        try:
            return original_mkdir(path, mode, dir_fd=dir_fd)
        except FileExistsError:
            if candidate and len(active['operations']) == index+1:
                after = directory_identity(Path(candidate['path']))
                if after == candidate['before']:
                    active['directory_noops'].append(candidate | {'event_index':index,'after':after,'result':'EEXIST'})
            raise
    os.mkdir = observed_mkdir
    original_start = threading.Thread.start
    def refuse_thread(thread, *positional, **keywords):
        active['operations'].append({'event':'thread.start', 'disposition':'BLOCKED'})
        raise ImportOperationRefused('import attempted to start a background thread')
    threading.Thread.start = refuse_thread
    results = []
    initial_paths = global_state(source,streams)['module_search_paths']
    record({'type':'start', 'schema':WORKER_SCHEMA, 'source':str(source),
            'roster_sha256':request['roster_sha256'], 'order':order, 'mode':mode, 'count':len(roster),
            'context':request['context'], 'vendor_policy_sha256':digest(policy),
            'font_descriptor_sha256':digest(font), 'initial_paths':pack_paths(initial_paths)})
    for entry in roster:
        path = source/entry['path']; name = entry['module']
        active['module'] = name;active['operations'] = [];active['native_loads'] = [];active['directory_noops'] = []
        cached = name in sys.modules
        before = global_state(source, streams); started = time.monotonic()
        result = {'path':entry['path'], 'module':name, 'cached_before':cached, 'status':'PASS', 'csv_checks':[]}
        try:
            if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
                raise ImportOperationRefused('module differs from bound roster')
            loaded = importlib.import_module(name)
            result['csv_checks'].append({'phase':'import', 'value':csv.field_size_limit()})
            actual = Path(getattr(loaded, '__file__', '')).resolve()
            result['resolved_module_path'] = str(actual)
            if actual != path.resolve():
                raise ImportOperationRefused('import resolved outside its declared module path')
            if mode == 'general' and cached:
                importlib.reload(loaded)
                result['csv_checks'].append({'phase':'reload_cached', 'value':csv.field_size_limit()})
            if mode == 'csv':
                importlib.reload(loaded)
                result['csv_checks'].append({'phase':'reload', 'value':csv.field_size_limit()})
                # This intentionally checks a cached import after every discovered setter.
                if (source/'mamey/validate.py').is_file():
                    cached_validate = 'mamey.validate' in sys.modules
                    importlib.import_module('mamey.validate')
                    result['csv_checks'].append({'phase':'cached_validate' if cached_validate else 'initial_validate', 'value':csv.field_size_limit()})
                    if not cached_validate:
                        importlib.import_module('mamey.validate')
                        result['csv_checks'].append({'phase':'cached_validate', 'value':csv.field_size_limit()})
            if name == FALLBACK_MODULE and policy['status'] == 'PINNED_VENDOR':
                result['fallback_capability'] = check_python_fallback(loaded,source,policy)
        except KeyboardInterrupt:
            raise
        except BaseException as exc:
            result.update(status='HOLD', exception_type=type(exc).__name__, reason=str(exc),
                attempted_exit=exc.code if isinstance(exc, SystemExit) else None)
            result['exception_evidence'] = exception_evidence(exc,source,policy['runtime_roots'])
            candidate = optional_unavailability(source,entry,result['exception_evidence'],policy)
            if candidate is not None:
                result['optional_availability'] = candidate
        after = global_state(source, streams)
        changes = state_difference(before, after)
        result['path_state'] = {'before':pack_paths(before['module_search_paths']), 'after':pack_paths(after['module_search_paths'])}
        if before['module_search_paths'] != after['module_search_paths']:
            proof = trusted_path_equivalence(source,before['module_search_paths'],after['module_search_paths'])
            result['trusted_path_change'] = proof
            if proof['equivalent']:
                changes.pop('module_search_paths',None)
        path_guard = unsupported_path_guard(before['module_search_paths'],after['module_search_paths'])
        if path_guard is not None:
            result['path_guard'] = path_guard
        result.update(operations=list(active['operations']), directory_noops=list(active['directory_noops']))
        failed_checks = [check for check in result['csv_checks'] if check['value']<THRESHOLD]
        if failed_checks:
            result['csv_guard'] = {'minimum':THRESHOLD, 'failed_checks':failed_checks}
        blocking = blocking_operations(result,font)
        if changes or blocking or failed_checks or path_guard is not None or after['csv_limit'] < THRESHOLD:
            result['status'] = 'HOLD'
        elif result.get('optional_availability'):
            result['status'] = 'OPTIONAL_UNAVAILABLE'
        result.update(state_changes=changes, operations=list(active['operations']), native_loads=list(active['native_loads']),
            csv_limit_after=after['csv_limit'], elapsed_seconds=time.monotonic()-started)
        results.append(result);record({'type':'module', **result})
    threading.Thread.start = original_start
    os.mkdir = original_mkdir
    font_validation = {'status':'NOT_REQUESTED'}
    if font['status'] == 'PREPARED':
        try:
            _font_cache.validate_cache(font['request'],manifest_sha256=font['manifest_sha256'])
            font_validation = {'status':'PASS'}
        except (ValueError,OSError,KeyError,TypeError) as exc:
            font_validation = {'status':'HOLD','reason':str(exc)}
    summary = {'type':'complete', 'schema':WORKER_SCHEMA,
        'roster_sha256':request['roster_sha256'], 'order':order, 'mode':mode, 'results':results,
        'status':import_readiness(results,policy) if font_validation['status'] != 'HOLD' and supported_paths(initial_paths) else 'HOLD',
        'font_cache_validation':font_validation,
        'count':len(results), 'csv_minimum':THRESHOLD}
    record(summary);trace.close()
    return 0 if summary['status'] in IMPORT_READY_STATES else 2


if __name__ == '__main__':
    raise SystemExit(main())
