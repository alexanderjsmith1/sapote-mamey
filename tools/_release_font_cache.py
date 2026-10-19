"""Explicit dependency-only font-cache preparation; imports perform no probes.

The controller owns sandbox/process-watch admission. A cache is accepted only
with a separately bound request and manifest digest, before AND after imports.
Validation uses stdlib only and never preloads a production/Matplotlib module.
"""
from __future__ import annotations

import argparse
import ast
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

SCHEMA = 'sapote-mamey.font-cache.v1'


class FontCacheRefused(ValueError):
    """Cache preparation or validation could not establish its bindings."""


def require(condition, message):
    if not condition:
        raise FontCacheRefused(message)


@contextmanager
def regular_reader(path):
    """Reject nonregular inputs before opening; bind no-follow reads to fstat."""
    path = no_links(Path(path).absolute())
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode), 'regular input required')
    token = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as handle:
        require(token(os.fstat(handle.fileno())) == token(before), 'input changed before read')
        yield handle
        require(token(os.fstat(handle.fileno())) == token(before), 'input changed during read')
    require(token(path.lstat()) == token(before), 'input path changed during read')


def sha256_file(path):
    digest = hashlib.sha256()
    with regular_reader(path) as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def regular_text(path):
    with regular_reader(path) as handle:
        require(os.fstat(handle.fileno()).st_size <= 10_000_000, 'text input exceeds bound')
        return handle.read(10_000_001).decode('utf-8')


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def no_links(path):
    path = Path(path)
    require(path.is_absolute() and '..' not in path.parts, 'absolute nontraversing path required')
    for node in [*reversed(path.parents), path]:
        require(not node.is_symlink(), 'symlink in selected path')
    return path


def private_directory(path):
    path = no_links(path)
    info = path.lstat()
    require(stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid()
            and stat.S_IMODE(info.st_mode) == 0o700, 'private owned directory required')
    return path


def private_file(path):
    path = no_links(path)
    info = path.lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
            and info.st_nlink == 1 and stat.S_IMODE(info.st_mode) == 0o600,
            'private owned single-link regular file required')
    return {'bytes': info.st_size, 'sha256': sha256_file(path)}


def read_json(path):
    def pairs(values):
        result = {}
        for key, value in values:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    try:
        return json.loads(regular_text(path), object_pairs_hook=pairs,
                          parse_constant=lambda value: require(False, 'nonfinite JSON'))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FontCacheRefused('invalid JSON input') from exc


def write_new_json(path, value):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, 'wb') as stream:
        stream.write(canonical(value) + b'\n')


def tree_binding(root):
    root = no_links(root).resolve(strict=True)
    rows = []
    def walk_error(error):
        raise FontCacheRefused('dependency walk failed') from error
    for folder, directories, names in os.walk(root, followlinks=False, onerror=walk_error):
        for name in directories + names:
            require(not (Path(folder) / name).is_symlink(), 'dependency tree contains symlink')
        for name in names:
            path = Path(folder) / name
            require(path.is_file(), 'nonregular dependency input')
            rows.append([path.relative_to(root).as_posix(), path.stat().st_size, sha256_file(path)])
    require(rows, 'empty dependency tree')
    return {'root': str(root), 'files': len(rows), 'sha256': hashlib.sha256(canonical(sorted(rows))).hexdigest()}


def runtime_identity():
    target = Path(sys.executable).resolve(strict=True)
    return {'executable': str(target), 'executable_sha256': sha256_file(target),
            'version': sys.version, 'implementation': sys.implementation.name,
            'cache_tag': sys.implementation.cache_tag, 'prefix': sys.prefix,
            'base_prefix': sys.base_prefix}


def make_request(output, *, source, context, matplotlib_root, metadata, font_tools=()):
    """Create fresh private output and a stdlib-only dependency/runtime request.

    Call in the SAME admitted interpreter/prefix later used by bootstrap/workers.
    Context is an externally admitted source/environment/machinery binding.
    """
    source = Path(source).resolve(strict=True)
    output = no_links(Path(output))
    require(not output.is_relative_to(source) and not source.is_relative_to(output),
            'output and source must be separate')
    require(not output.exists(), 'fresh output required')
    require(isinstance(context, dict) and context
            and all(isinstance(value, str) and re.fullmatch('[0-9a-f]{64}', value)
                    for value in context.values()), 'context must contain bound SHA256 values')
    mpl = no_links(Path(matplotlib_root)).resolve(strict=True)
    meta = no_links(Path(metadata)).resolve(strict=True)
    require(meta.parent.parent == mpl.parent and meta.parent.name.startswith('matplotlib-')
            and meta.name == 'METADATA', 'Matplotlib metadata location mismatch')
    version = re.search(r'^Version: (.+)$', regular_text(meta), re.M)
    require(version is not None, 'Matplotlib version missing')
    parsed = ast.parse(regular_text(mpl / 'font_manager.py'))
    manager = next(node for node in parsed.body if isinstance(node, ast.ClassDef) and node.name == 'FontManager')
    cache_version = next(ast.literal_eval(node.value) for node in manager.body
                         if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name)
                         and t.id == '__version__' for t in node.targets))
    require(isinstance(cache_version, (str, int)) and not isinstance(cache_version, bool)
            and re.fullmatch(r'[A-Za-z0-9._-]{1,80}', str(cache_version)), 'unsupported font cache version')
    request = {'schema': SCHEMA, 'output': str(output), 'cache_root': str(output / 'matplotlib'),
               'source': str(source), 'context': dict(context), 'runtime': runtime_identity(),
               'helper_sha256': sha256_file(__file__), 'dependency': tree_binding(mpl),
               'metadata': {'path': str(meta), 'sha256': sha256_file(meta)},
               'font_tools': [{'path': str(Path(tool).resolve(strict=True)),
                               'sha256': sha256_file(Path(tool).resolve(strict=True))} for tool in font_tools],
               'matplotlib_version': version.group(1), 'font_manager_version': cache_version,
               'font_roots': [str(mpl / 'mpl-data'), '/System', '/usr/share']}
    output.mkdir(mode=0o700)
    for name in ['matplotlib', 'home', 'config', 'data', 'tmp']:
        (output / name).mkdir(mode=0o700)
    write_new_json(output / 'request.json', request)
    return request


def validate_request(request, *, evidence_output=None):
    require(request.get('schema') == SCHEMA, 'request schema mismatch')
    # Validate original bindings lexically, without stat/read/resolve at old paths.
    original = Path(request['output'])
    original_cache = Path(request['cache_root'])
    source = Path(request['source'])
    require(all(path.is_absolute() and '..' not in path.parts
                for path in [original, original_cache, source]), 'invalid original path binding')
    require(original_cache == original / 'matplotlib', 'original cache/output relationship mismatch')
    require(not original.is_relative_to(source) and not source.is_relative_to(original),
            'original output and source must be separate')
    output = private_directory(original if evidence_output is None else Path(evidence_output))
    require(not output.is_relative_to(source) and not source.is_relative_to(output),
            'selected evidence output and source must be separate')
    cache = private_directory(output / 'matplotlib')
    require(request['runtime'] == runtime_identity(), 'runtime identity changed')
    require(request['helper_sha256'] == sha256_file(__file__), 'font helper changed')
    require(request['dependency'] == tree_binding(Path(request['dependency']['root'])), 'Matplotlib dependency changed')
    require(request['metadata']['sha256'] == sha256_file(no_links(Path(request['metadata']['path']))), 'Matplotlib metadata changed')
    require(all(tool['sha256'] == sha256_file(no_links(Path(tool['path'])))
                for tool in request['font_tools']), 'font-discovery executable changed')
    return cache


def font_bindings(payload, request):
    require(payload.get('__class__') == 'FontManager'
            and payload.get('_version') == request['font_manager_version'], 'font cache schema/version mismatch')
    require(isinstance(payload.get('ttflist'), list) and payload['ttflist']
            and isinstance(payload.get('afmlist'), list), 'font inventory missing')
    roots = [Path(root).resolve() for root in request['font_roots']]
    result = {}
    for entry in payload['ttflist'] + payload['afmlist']:
        require(isinstance(entry, dict) and entry.get('__class__') == 'FontEntry'
                and isinstance(entry.get('fname'), str), 'invalid font entry')
        named = Path(entry['fname'])
        require('..' not in named.parts, 'traversing font reference')
        original = named if named.is_absolute() else Path(request['dependency']['root']) / 'mpl-data' / named
        target = original.resolve(strict=True)
        require(any(target.is_relative_to(root) for root in roots) and target.is_file(), 'font outside admitted reads')
        result[str(original)] = {'resolved': str(target), 'bytes': target.stat().st_size,
                                 'sha256': sha256_file(target)}
    return result


def validate_cache(request, *, manifest_sha256, evidence_output=None):
    """Fail closed before guard installation and after imports; never loads mpl.

    The caller must bind request bytes AND manifest_sha256 in its immutable worker
    request/receipt. Passing self-reported values from the cache is not admission.
    """
    cache = validate_request(request, evidence_output=evidence_output)
    # The selected evidence location is exclusive, including the request copy.
    # Its canonical bytes/context remain those of the original request.
    request_path = cache.parent / 'request.json'
    require(private_file(request_path)['sha256'] == hashlib.sha256(canonical(request) + b'\n').hexdigest(),
            'selected evidence request bytes mismatch')
    require(read_json(request_path) == request, 'selected evidence request differs')
    manifest_path = cache / 'MANIFEST.json'
    require(private_file(manifest_path)['sha256'] == manifest_sha256, 'font manifest digest mismatch')
    manifest = read_json(manifest_path)
    require(manifest['schema'] == SCHEMA and manifest['request_sha256'] == hashlib.sha256(canonical(request)).hexdigest(),
            'font manifest request binding mismatch')
    name = f"fontlist-v{request['font_manager_version']}.json"
    require({path.name for path in cache.iterdir()} == {name, 'MANIFEST.json'}, 'missing or unexpected cache entries')
    font_file = cache / name
    require(private_file(font_file) == manifest['font_cache'], 'font cache bytes changed')
    require(font_bindings(read_json(font_file), request) == manifest['fonts'], 'referenced font inputs changed')
    require(manifest['project_modules'] == [], 'bootstrap preloaded project modules')
    # Validation metadata is a separate envelope, not a rewritten manifest.
    return {'manifest': manifest, 'manifest_sha256': manifest_sha256,
            'evidence_output': str(cache.parent.resolve(strict=True)),
            'cache_root': str(cache.resolve(strict=True)),
            'request_path': str(request_path.resolve(strict=True)),
            'manifest_path': str(manifest_path.resolve(strict=True))}


def bootstrap(request):
    """Only explicit dependency initialization; controller MUST sandbox/watch it."""
    cache = validate_request(request)
    require(not list(cache.iterdir()) and 'matplotlib' not in sys.modules, 'cold isolated bootstrap required')
    require(Path(os.environ.get('MPLCONFIGDIR', '')).absolute() == cache, 'MPLCONFIGDIR mismatch')
    source = Path(request['source'])
    def project_modules():
        return sorted(name for name, module in sys.modules.items()
                      if getattr(module, '__file__', None)
                      and Path(module.__file__).resolve().is_relative_to(source)
                      and Path(module.__file__).resolve() != Path(__file__).resolve())
    require(not project_modules(), 'project modules already loaded')
    import matplotlib
    require(Path(matplotlib.__file__).resolve().parent == Path(request['dependency']['root'])
            and matplotlib.__version__ == request['matplotlib_version'], 'selected Matplotlib origin/version differs')
    import matplotlib.font_manager as font_manager
    require(font_manager.FontManager.__version__ == request['font_manager_version'], 'font manager version differs')
    require(Path(matplotlib.get_cachedir()).resolve() == cache, 'Matplotlib cache fell back outside output')
    require(not project_modules(), 'dependency bootstrap loaded project modules')
    name = f"fontlist-v{request['font_manager_version']}.json"
    require({path.name for path in cache.iterdir()} == {name}, 'unexpected generated cache entries')
    font_file = cache / name
    info = no_links(font_file).lstat()
    require(stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
            and info.st_nlink == 1, 'generated cache is not an owned regular file')
    os.chmod(font_file, 0o600)
    manifest = {'schema': SCHEMA, 'request_sha256': hashlib.sha256(canonical(request)).hexdigest(),
                'font_cache': private_file(font_file), 'fonts': font_bindings(read_json(font_file), request),
                'project_modules': []}
    write_new_json(cache / 'MANIFEST.json', manifest)
    digest = private_file(cache / 'MANIFEST.json')['sha256']
    validate_cache(request, manifest_sha256=digest)
    return {'status': 'PREPARED', 'manifest_sha256': digest, 'font_files': len(manifest['fonts']),
            'runtime': request['runtime'], 'dependency': request['dependency'], 'context': request['context']}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--request', type=Path)
    group.add_argument('--prepare-spec', type=Path)
    parser.add_argument('--request-sha256')
    parser.add_argument('--spec-sha256')
    parser.add_argument('--receipt', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.prepare_spec is not None:
        require(private_file(args.prepare_spec)['sha256'] == args.spec_sha256, 'bootstrap spec bytes changed')
        # Data-only fixed API; no arbitrary modules, code snippets or callbacks.
        request = make_request(**read_json(args.prepare_spec))
    else:
        require(private_file(args.request)['sha256'] == args.request_sha256, 'bootstrap request bytes changed')
        request = read_json(args.request)
    require(no_links(args.receipt).parent == private_directory(request['output']), 'receipt outside output')
    write_new_json(args.receipt, bootstrap(request))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
