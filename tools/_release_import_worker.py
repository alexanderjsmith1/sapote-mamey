"""Controlled shared-interpreter worker; importing this file performs no work."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib
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


THRESHOLD = min(sys.maxsize, 2**31 - 1)


class ImportOperationRefused(RuntimeError):
    """An import attempted work outside the declared no-analysis policy."""


def digest(value) -> str:
    """Hash selected state without exposing environment values."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


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
    paths = list(dict.fromkeys(str(Path(value or '.').resolve()) for value in sys.path))
    approved = [str(source/'tools'), str(source)]
    def import_names(directory):
        names = set()
        for path in directory.iterdir():
            if path.is_dir() and path.name.isidentifier():
                names.add(path.name)  # Includes namespace packages.
            elif path.is_file():
                for suffix in ['.py', '.pyc', *EXTENSION_SUFFIXES]:
                    if path.name.endswith(suffix):
                        names.add(path.name[:-len(suffix)])
                        break
        return names
    source_names = import_names(source)
    tools_names = import_names(source/'tools')
    # These two already-admitted locations may swap priority only when they
    # cannot shadow the same root module. All other path changes remain holds.
    if not source_names.intersection(tools_names) and set(paths[:2]) == set(approved):
        paths[:2] = approved
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
    active = {'module':'<bootstrap>', 'operations':[], 'native_loads':[], 'trusted_write':False}

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
            active['operations'].append({'event':event, 'disposition':'CONTROLLED_SCRATCH_OR_OS_REFUSAL'})

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
    original_start = threading.Thread.start
    def refuse_thread(thread, *positional, **keywords):
        active['operations'].append({'event':'thread.start', 'disposition':'BLOCKED'})
        raise ImportOperationRefused('import attempted to start a background thread')
    threading.Thread.start = refuse_thread
    results = []
    record({'type':'start', 'schema':'sapote-mamey.shared-import-worker.v1', 'source':str(source),
            'roster_sha256':request['roster_sha256'], 'order':order, 'mode':mode, 'count':len(roster)})
    for entry in roster:
        path = source/entry['path']; name = entry['module']
        active['module'] = name;active['operations'] = [];active['native_loads'] = []
        cached = name in sys.modules
        before = global_state(source, streams); started = time.monotonic()
        result = {'path':entry['path'], 'module':name, 'cached_before':cached, 'status':'PASS', 'csv_checks':[]}
        try:
            if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
                raise ImportOperationRefused('module differs from bound roster')
            loaded = importlib.import_module(name)
            result['csv_checks'].append({'phase':'import', 'value':csv.field_size_limit()})
            actual = Path(getattr(loaded, '__file__', '')).resolve()
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
        except KeyboardInterrupt:
            raise
        except BaseException as exc:
            result.update(status='HOLD', exception_type=type(exc).__name__, reason=str(exc),
                attempted_exit=exc.code if isinstance(exc, SystemExit) else None)
        after = global_state(source, streams)
        changes = state_difference(before, after)
        failed_checks = [check for check in result['csv_checks'] if check['value']<THRESHOLD]
        if failed_checks:
            result['csv_guard'] = {'minimum':THRESHOLD, 'failed_checks':failed_checks}
        if changes or active['operations'] or failed_checks:
            result['status'] = 'HOLD'
        result.update(state_changes=changes, operations=list(active['operations']), native_loads=list(active['native_loads']),
            csv_limit_after=after['csv_limit'], elapsed_seconds=time.monotonic()-started)
        results.append(result);record({'type':'module', **result})
    threading.Thread.start = original_start
    summary = {'type':'complete', 'schema':'sapote-mamey.shared-import-worker.v1',
        'roster_sha256':request['roster_sha256'], 'order':order, 'mode':mode, 'results':results,
        'status':'PASS' if all(row['status']=='PASS' for row in results) else 'HOLD',
        'count':len(results), 'csv_minimum':THRESHOLD}
    record(summary);trace.close()
    return 0 if summary['status']=='PASS' else 2


if __name__ == '__main__':
    raise SystemExit(main())
