"""Strict cache bindings on declared fake dependency/font bytes; no mpl import."""
import builtins
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import types
from copy import deepcopy

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('font_helper', ROOT/'tools/_release_font_cache.py')
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


@pytest.fixture
def prepared(tmp_path):
    source = tmp_path/'source'; source.mkdir()
    mpl = tmp_path/'site/matplotlib'; mpl.mkdir(parents=True)
    (mpl/'font_manager.py').write_text("class FontManager:\n    __version__ = '3.11.0'\n")
    data = mpl/'mpl-data/fonts'; data.mkdir(parents=True)
    (data/'fake.ttf').write_bytes(b'SELF_AUTHORED_FONT_TOKEN_NOT_A_REAL_FONT')
    meta = tmp_path/'site/matplotlib-3.11.2.dist-info/METADATA'
    meta.parent.mkdir(); meta.write_text('Name: matplotlib\nVersion: 3.11.2\n')
    tool = tmp_path/'font_discovery_token'; tool.write_bytes(b'SELF_AUTHORED_TOOL_TOKEN')
    request = helper.make_request(tmp_path/'output', source=source,
        context={'source_sha256':'1'*64, 'environment_sha256':'2'*64},
        matplotlib_root=mpl, metadata=meta, font_tools=[tool])
    cache = Path(request['cache_root'])
    payload = {'__class__':'FontManager', '_version':'3.11.0', 'afmlist':[],
        'ttflist':[{'__class__':'FontEntry', 'fname':'fonts/fake.ttf'}]}
    fontfile = cache/'fontlist-v3.11.0.json'
    helper.write_new_json(fontfile, payload)
    manifest = {'schema':helper.SCHEMA,
        'request_sha256':hashlib.sha256(helper.canonical(request)).hexdigest(),
        'font_cache':helper.private_file(fontfile), 'fonts':helper.font_bindings(payload, request),
        'project_modules':[]}
    helper.write_new_json(cache/'MANIFEST.json', manifest)
    return request, helper.sha256_file(cache/'MANIFEST.json')


def test_valid_cache_validation_never_imports_matplotlib(prepared, monkeypatch):
    request, digest = prepared
    original = builtins.__import__
    def importing(name, *args, **kwargs):
        if name.startswith('matplotlib'): pytest.fail('validator imported dependency')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', importing)
    assert helper.validate_cache(request, manifest_sha256=digest)['manifest']['project_modules'] == []


@pytest.mark.parametrize('mutation', ['missing', 'tampered', 'invalid_json', 'wrong_version',
    'extra_file', 'symlink', 'hardlink', 'public_mode', 'public_directory', 'outside_cache', 'runtime',
    'context', 'dependency', 'metadata', 'font_tool', 'font', 'manifest'])
def test_invalid_or_mutated_cache_refuses(prepared, tmp_path, mutation):
    request, digest = prepared
    cache = Path(request['cache_root']); fontfile = cache/'fontlist-v3.11.0.json'
    if mutation == 'missing': fontfile.unlink()
    elif mutation == 'tampered': fontfile.write_bytes(fontfile.read_bytes()+b' ')
    elif mutation in {'invalid_json', 'wrong_version', 'font'}:
        if mutation == 'invalid_json': fontfile.write_text('{')
        else:
            payload = helper.read_json(fontfile)
            if mutation == 'wrong_version': payload['_version']='incorrect'
            else: payload['ttflist'][0]['fname']=str(tmp_path/'outside.ttf')
            if mutation == 'font': (tmp_path/'outside.ttf').write_bytes(b'OUTSIDE_TOKEN')
            fontfile.write_bytes(helper.canonical(payload))
        manifest = helper.read_json(cache/'MANIFEST.json')
        manifest['font_cache'] = helper.private_file(fontfile)
        (cache/'MANIFEST.json').write_bytes(helper.canonical(manifest))
        digest = helper.sha256_file(cache/'MANIFEST.json')
    elif mutation == 'extra_file': (cache/'unbound').write_text('not admitted')
    elif mutation in {'symlink', 'hardlink'}:
        outside = tmp_path/'other'; outside.write_bytes(fontfile.read_bytes()); fontfile.unlink()
        if mutation == 'symlink': fontfile.symlink_to(outside)
        else: os.link(outside, fontfile)
    elif mutation == 'public_mode': fontfile.chmod(0o666)
    elif mutation == 'public_directory': cache.chmod(0o755)
    elif mutation == 'outside_cache':
        outside = tmp_path/'outside'; outside.mkdir(mode=0o700)
        request['cache_root']=str(outside)
    elif mutation == 'runtime': request['runtime']['version']='different'
    elif mutation == 'context': request['context']['source_sha256']='3'*64
    elif mutation == 'dependency': (Path(request['dependency']['root'])/'font_manager.py').write_text('changed')
    elif mutation == 'metadata': Path(request['metadata']['path']).write_text('changed')
    elif mutation == 'font_tool': Path(request['font_tools'][0]['path']).write_bytes(b'CHANGED_TOOL_TOKEN')
    else: (cache/'MANIFEST.json').write_bytes((cache/'MANIFEST.json').read_bytes()+b' ')
    with pytest.raises((ValueError, OSError, KeyError, TypeError)):
        helper.validate_cache(request, manifest_sha256=digest)


def test_output_symlink_is_refused_before_creation(tmp_path):
    target=tmp_path/'target'; target.mkdir()
    alias=tmp_path/'alias'; alias.symlink_to(target, target_is_directory=True)
    with pytest.raises(helper.FontCacheRefused, match='symlink'):
        helper.no_links(alias/'cache')


def test_existing_output_is_never_adopted(prepared):
    request, _ = prepared
    before=Path(request['output'], 'request.json').read_bytes()
    with pytest.raises(helper.FontCacheRefused, match='fresh'):
        helper.make_request(request['output'], source=request['source'], context=request['context'],
            matplotlib_root=request['dependency']['root'], metadata=request['metadata']['path'])
    assert Path(request['output'], 'request.json').read_bytes() == before


def test_referenced_font_mutation_refuses(prepared):
    request, digest = prepared
    Path(request['dependency']['root'], 'mpl-data/fonts/fake.ttf').write_bytes(b'CHANGED_FONT_TOKEN')
    with pytest.raises(helper.FontCacheRefused):
        helper.validate_cache(request, manifest_sha256=digest)


@pytest.mark.parametrize('parent_state', ['ambient', 'preloaded'])
def test_project_preload_is_refused_before_dependency_initialization(prepared, tmp_path, monkeypatch, parent_state):
    request, _ = prepared
    cache = Path(request['cache_root'])
    # Remove only this self-authored fixture's cache files to expose bootstrap admission.
    for path in cache.iterdir(): path.unlink()
    # Normal tests/conftest.py loads Matplotlib in the parent. Never purge it.
    if parent_state == 'preloaded' and 'matplotlib' not in sys.modules:
        monkeypatch.setitem(sys.modules, 'matplotlib', types.ModuleType('matplotlib'))
    parent_modules = {name: id(module) for name, module in sys.modules.items()
                      if name == 'matplotlib' or name.startswith('matplotlib.')}
    script = tmp_path/'project_preload_child.py'
    script.write_text('''import builtins, importlib.util, json, os, sys, types
from pathlib import Path
assert not any(name == 'matplotlib' or name.startswith('matplotlib.') for name in sys.modules)
spec = importlib.util.spec_from_file_location('actual_font_helper', sys.argv[1])
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)
assert helper.sha256_file(sys.argv[1]) == sys.argv[3]
request = helper.read_json(sys.argv[2])
assert helper.runtime_identity() == request['runtime']
os.environ['MPLCONFIGDIR'] = request['cache_root']
module = types.ModuleType('planted_project_preload')
module.__file__ = str(Path(request['source'])/'planted.py')
sys.modules[module.__name__] = module
attempts = []
original = builtins.__import__
def importing(name, *args, **kwargs):
    if name == 'matplotlib' or name.startswith('matplotlib.'):
        attempts.append(name)
        raise AssertionError('dependency initialization must not be attempted')
    return original(name, *args, **kwargs)
builtins.__import__ = importing
try:
    helper.bootstrap(request)
except helper.FontCacheRefused as error:
    reason = str(error)
    assert reason == 'project modules already loaded'
else:
    raise AssertionError('expected specific project preload refusal')
assert attempts == []
assert not any(name == 'matplotlib' or name.startswith('matplotlib.') for name in sys.modules)
print(json.dumps({'reason':reason, 'matplotlib_import_attempts':attempts,
                  'matplotlib_loaded':False, 'helper_sha256':helper.sha256_file(sys.argv[1])}))
''')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    for key in ('PYTHONPATH', 'PYTHONHOME'): env.pop(key, None)
    result = subprocess.run([sys.executable, '-I', '-B', str(script), str(Path(helper.__file__).resolve()),
        str(Path(request['output'])/'request.json'), request['helper_sha256']],
        cwd=request['output'], env=env, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ''
    data = json.loads(result.stdout)
    assert data == {'reason':'project modules already loaded', 'matplotlib_import_attempts':[],
                    'matplotlib_loaded':False, 'helper_sha256':request['helper_sha256']}
    assert {name: id(module) for name, module in sys.modules.items()
            if name == 'matplotlib' or name.startswith('matplotlib.')} == parent_modules


def test_cache_output_inside_source_is_refused(prepared):
    request, _ = prepared
    output = Path(request['source'])/'cache'
    with pytest.raises(helper.FontCacheRefused, match='separate'):
        helper.make_request(output, source=request['source'], context=request['context'],
            matplotlib_root=request['dependency']['root'], metadata=request['metadata']['path'])
    assert not output.exists()


def test_data_only_prepare_cli_creates_request_in_current_runtime(prepared, tmp_path, monkeypatch):
    original, _ = prepared
    output=tmp_path/'cli_output'
    spec={'output':str(output), 'source':original['source'], 'context':original['context'],
          'matplotlib_root':original['dependency']['root'], 'metadata':original['metadata']['path']}
    spec_path=tmp_path/'spec.json'; helper.write_new_json(spec_path, spec)
    def fake_bootstrap(request):
        assert request['runtime'] == helper.runtime_identity()
        assert Path(request['output']) == output
        return {'status':'SELF_AUTHORED_CLI_INTERFACE_ONLY'}
    monkeypatch.setattr(helper,'bootstrap',fake_bootstrap)
    assert helper.main(['--prepare-spec',str(spec_path),'--spec-sha256',helper.sha256_file(spec_path),
                        '--receipt',str(output/'result.json')]) == 0
    assert helper.read_json(output/'result.json')['status'] == 'SELF_AUTHORED_CLI_INTERFACE_ONLY'


def test_dependency_walk_error_is_not_silently_omitted(prepared, monkeypatch):
    request, _ = prepared
    def walking(*args, **kwargs):
        kwargs['onerror'](PermissionError('SELF_AUTHORED_WALK_ERROR'))
        yield ('unreachable', [], [])
    monkeypatch.setattr(helper.os, 'walk', walking)
    with pytest.raises(helper.FontCacheRefused, match='dependency walk failed'):
        helper.tree_binding(request['dependency']['root'])


@pytest.mark.parametrize('target', ['metadata', 'tool', 'generic_hash'])
def test_fifo_input_refuses_before_open(prepared, tmp_path, target):
    request, _ = prepared
    fifo=tmp_path/'fifo'; os.mkfifo(fifo)
    with pytest.raises(helper.FontCacheRefused, match='regular input required'):
        if target == 'generic_hash': helper.sha256_file(fifo)
        else:
            meta=Path(request['metadata']['path'])
            tools=[fifo] if target == 'tool' else []
            if target == 'metadata':
                meta.unlink(); os.mkfifo(meta)
            helper.make_request(tmp_path/'fresh', source=request['source'], context=request['context'],
                matplotlib_root=request['dependency']['root'], metadata=meta, font_tools=tools)


@pytest.fixture
def moved(prepared, tmp_path):
    request, digest = prepared
    original = Path(request['output'])
    current = tmp_path/'moved_evidence'
    # Move only this self-authored test evidence, never source or font inputs.
    original.rename(current)
    return request, digest, original, current


@pytest.mark.parametrize('old_state', ['missing', 'poisoned'])
def test_explicit_move_preserves_bytes_and_never_accesses_old_evidence(moved, monkeypatch, old_state):
    request, digest, original, current = moved
    before = deepcopy(request)
    request_sha = helper.sha256_file(current/'request.json')
    manifest_sha = helper.sha256_file(current/'matplotlib/MANIFEST.json')
    if old_state == 'poisoned':
        original.mkdir(mode=0o700)
        os.mkfifo(original/'request.json')
        (original/'matplotlib').symlink_to(current/'matplotlib', target_is_directory=True)
    old_lstat = Path.lstat
    def no_old_stat(path, *args, **kwargs):
        if Path(path) == original or Path(path).is_relative_to(original):
            pytest.fail('accessed old evidence location')
        return old_lstat(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'lstat', no_old_stat)
    result = helper.validate_cache(request, manifest_sha256=digest, evidence_output=current)
    assert request == before
    assert helper.sha256_file(current/'request.json') == request_sha
    assert helper.sha256_file(current/'matplotlib/MANIFEST.json') == manifest_sha == digest
    assert result['cache_root'] == str((current/'matplotlib').resolve())
    assert result['evidence_output'] == str(current.resolve())
    assert result['manifest'] == helper.read_json(current/'matplotlib/MANIFEST.json')
    assert request['cache_root'] == str(original/'matplotlib')
    assert not Path(request['dependency']['root']).is_relative_to(current)


@pytest.mark.parametrize('mutation', ['missing_request', 'missing_manifest', 'missing_payload',
    'tampered_request', 'tampered_manifest', 'tampered_payload', 'public_output', 'public_cache',
    'linked_output', 'linked_cache', 'linked_request', 'linked_payload', 'outside_cache'])
def test_invalid_explicit_current_evidence_refuses(moved, tmp_path, mutation):
    request, digest, original, current = moved
    cache=current/'matplotlib'; selected=current
    if mutation.startswith('missing_') or mutation.startswith('tampered_'):
        paths={'request':current/'request.json', 'manifest':cache/'MANIFEST.json',
               'payload':cache/'fontlist-v3.11.0.json'}
        path=paths[mutation.split('_',1)[1]]
        if mutation.startswith('missing_'): path.unlink()
        else: path.write_bytes(path.read_bytes()+b' ')
    elif mutation == 'public_output': current.chmod(0o755)
    elif mutation == 'public_cache': cache.chmod(0o755)
    elif mutation == 'linked_output':
        selected=tmp_path/'alias'; selected.symlink_to(current, target_is_directory=True)
    elif mutation == 'linked_cache':
        cache.rename(tmp_path/'real_cache'); cache.symlink_to(tmp_path/'real_cache', target_is_directory=True)
    elif mutation in {'linked_request','linked_payload'}:
        path=current/'request.json' if mutation=='linked_request' else cache/'fontlist-v3.11.0.json'
        path.rename(tmp_path/'real_file'); path.symlink_to(tmp_path/'real_file')
    else:
        selected=tmp_path/'outside'; selected.mkdir(mode=0o700)
        (selected/'matplotlib').symlink_to(cache, target_is_directory=True)
    with pytest.raises((ValueError, OSError, KeyError, TypeError)):
        helper.validate_cache(request, manifest_sha256=digest, evidence_output=selected)


def test_rebase_never_bypasses_original_cache_output_relationship(moved):
    request, digest, original, current = moved
    request['cache_root']=str(original.parent/'unrelated')
    with pytest.raises(helper.FontCacheRefused, match='original cache/output relationship'):
        helper.validate_cache(request, manifest_sha256=digest, evidence_output=current)


def test_rebased_evidence_does_not_rebase_external_font_or_dependency_inputs(moved):
    request, digest, original, current = moved
    # The declared external input remains required at its independently bound path.
    Path(request['metadata']['path']).unlink()
    with pytest.raises((ValueError, OSError)):
        helper.validate_cache(request, manifest_sha256=digest, evidence_output=current)
