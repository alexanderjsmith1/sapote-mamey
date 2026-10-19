"""Inert imports and requested execution using only fake CLI/analysis interfaces."""
import builtins
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import types

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def no_analysis_imports(monkeypatch, missing=None):
    original = builtins.__import__
    def importing(name, *args, **kwargs):
        if name.split('.')[0] in ({missing} if missing else {'pyhmmer', 'Bio'}):
            raise ModuleNotFoundError('blocked optional dependency: ' + name, name=name.split('.')[0])
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', importing)


def test_entrypoint_import_never_loads_cli_launches_or_changes_path(monkeypatch):
    original = builtins.__import__
    def importing(name, *args, **kwargs):
        if name == 'mamey.cli':
            pytest.fail('import requested the CLI')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', importing)
    before = list(sys.path)
    try:
        load('mamey/__main__.py', 'mamey.__main__')
        assert sys.path == before
    finally:
        sys.path[:] = before


@pytest.mark.parametrize('exit_code', [0, 7])
def test_python_m_preserves_local_bootstrap_argv_and_exit(tmp_path, exit_code):
    package = tmp_path / 'mamey'; package.mkdir()
    (package / '__init__.py').write_text('# self-authored CLI fixture; no real package imports\n')
    (package / '__main__.py').write_bytes((ROOT / 'mamey/__main__.py').read_bytes())
    (package / 'cli.py').write_text(
        'import json,sys\n'
        'def main():\n'
        '    print(json.dumps({"argv":sys.argv,"first_path":sys.path[0],"cli":__file__}))\n'
        '    return int(sys.argv[-1])\n')
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    for key in ('PYTHONPATH', 'PYTHONHOME'): env.pop(key, None)
    argv = ['--literal', 'argument with spaces', str(exit_code)]
    result = subprocess.run([sys.executable, '-S', '-B', '-m', 'mamey', *argv],
        cwd=tmp_path, env=env, capture_output=True, text=True, timeout=10)
    assert result.returncode == exit_code, result.stderr
    assert result.stderr == ''
    data = json.loads(result.stdout)
    assert data['argv'] == [str(package / '__main__.py'), *argv]
    assert data['first_path'] == str(tmp_path)
    assert data['cli'] == str(package / 'cli.py')


def test_bgc_walk_import_without_optional_analysis_dependencies(monkeypatch):
    no_analysis_imports(monkeypatch)
    module = load('mamey/bgc_walk.py', 'lane_test_bgc_walk')
    assert callable(module.bgc_walk) and callable(module.render_walk)


def fake_analysis(monkeypatch):
    events = []
    token = object()
    class Alphabet:
        @staticmethod
        def amino(): events.append(('amino',)); return token
    class TextSequence:
        def __init__(self, **kwargs): self.values = kwargs
        def digitize(self, alphabet):
            assert alphabet is token
            events.append(('digitize', self.values))
            return self.values
    def block(alphabet, seqs):
        assert alphabet is token
        events.append(('block', seqs))
        return seqs
    class HMMFile:
        def __init__(self, path): events.append(('HMMFile', path))
        def __enter__(self): return iter([types.SimpleNamespace(name=b'FAKE_DOMAIN')])
        def __exit__(self, *args): pass
    def hmmsearch(hmms, seqs, **kwargs):
        events.append(('hmmsearch', hmms, seqs, kwargs))
        domain = lambda included, pos, score: types.SimpleNamespace(
            included=included, score=score, alignment=types.SimpleNamespace(target_from=pos))
        hit = types.SimpleNamespace(included=True, name=b'g1',
            domains=[domain(True, 9, 8.76), domain(False, 1, 99), domain(True, 2, 3.14)])
        excluded = types.SimpleNamespace(included=False, name=b'ignored', domains=[])
        return [[hit, excluded]]
    def feature(kind, start, translation):
        return types.SimpleNamespace(type=kind, location=types.SimpleNamespace(
            start=start, end=start+3, strand=1), qualifiers={
            'translation':[translation], 'locus_tag':['g'+str(start)],
            'sec_met_domain':['FAKE description']})
    def parse(path, kind):
        events.append(('parse', path, kind))
        return iter([types.SimpleNamespace(features=[feature('CDS', 2, 'BB'),
            feature('CDS', 1, 'AA'), feature('CDS', 3, ''), feature('other', 4, 'CC')])])
    pyhmmer = types.ModuleType('pyhmmer')
    pyhmmer.plan7 = types.SimpleNamespace(HMMFile=HMMFile)
    pyhmmer.hmmer = types.SimpleNamespace(hmmsearch=hmmsearch)
    easel = types.ModuleType('pyhmmer.easel')
    easel.Alphabet = Alphabet; easel.TextSequence = TextSequence; easel.DigitalSequenceBlock = block
    bio = types.ModuleType('Bio'); bio.SeqIO = types.SimpleNamespace(parse=parse)
    for name, value in [('pyhmmer', pyhmmer), ('pyhmmer.easel', easel), ('Bio', bio)]:
        monkeypatch.setitem(sys.modules, name, value)
    return events


def test_bgc_walk_import_does_not_initialize_available_backend(monkeypatch):
    events = fake_analysis(monkeypatch)
    load('mamey/bgc_walk.py', 'lane_test_bgc_walk')
    assert events == []


def test_text_render_needs_no_analysis_backend(monkeypatch):
    no_analysis_imports(monkeypatch)
    module = load('mamey/bgc_walk.py', 'lane_test_bgc_walk')
    genes = [{'lt':'fixture', 'seq':'AA', 'strand':1}]
    assert module.render_walk(genes, {'fixture':[(1, 'FAKE', 2)]}, {'FAKE'}) == (
        'fixture        (   2aa)[+1]  *FAKE*')


@pytest.mark.parametrize('missing', ['pyhmmer', 'Bio'])
def test_requested_analysis_truthfully_refuses_missing_dependency(monkeypatch, missing):
    fake_analysis(monkeypatch)
    module = load('mamey/bgc_walk.py', 'lane_test_bgc_walk')
    no_analysis_imports(monkeypatch, missing)
    with pytest.raises(ModuleNotFoundError) as error:
        module.bgc_walk('not-opened.gbk', 'not-opened.hmm')
    assert error.value.name == missing


def test_requested_analysis_preserves_algorithm_parameters_with_fake_tokens(monkeypatch):
    events = fake_analysis(monkeypatch)
    module = load('mamey/bgc_walk.py', 'lane_test_bgc_walk')
    assert events == []
    genes, hits = module.bgc_walk('fake.gbk', 'fake.hmm')
    assert [gene['lt'] for gene in genes] == ['g1', 'g2']
    assert all(gene['as_dom'] == ['FAKE'] for gene in genes)
    assert hits == {'g1':[(2, 'FAKE_DOMAIN', 3.1), (9, 'FAKE_DOMAIN', 8.8)]}
    search = next(event for event in events if event[0] == 'hmmsearch')
    assert search[3] == {'cpus':4, 'bit_cutoffs':'gathering'}
    assert [seq['name'] for seq in search[2]] == [b'g1', b'g2']
    assert [event[0] for event in events].count('amino') == 1
