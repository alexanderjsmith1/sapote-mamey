"""Compare the extracted front doors with source-bound pre-extraction behavior."""
import argparse
import contextlib
import io
import json
from pathlib import Path
import sys
import types

import pytest

from mamey import cli, figure_factory_cli
from mamey.console import emit


NAMES = {
    'codex-heatmaps': '_codex_heatmaps_command',
    'codex-figure-catalog': '_codex_figure_catalog_command',
    'codex-figure-sets': '_codex_figure_sets_command',
    'codex-bigscape-figure-sets': '_codex_bigscape_figure_sets_command',
    'codex-figure-sources': '_codex_figure_sources_command',
}


@pytest.fixture(scope='module')
def original():
    namespace = {'__package__': 'mamey', 'json': json, 'Path': Path,
                 '_sys': sys, 'emit': emit}
    fixture = Path(__file__).parent / 'fixtures/figure_factory_cli_v97449.py.txt'
    exec(compile(fixture.read_text(), str(fixture), 'exec'), namespace)
    return namespace


@pytest.fixture(scope='module')
def parsers(original):
    before = argparse.ArgumentParser(prog='mamey')
    original['register_commands'](before.add_subparsers(dest='command'))
    return before, cli.build_parser()


def _choices(parser):
    return next(a.choices for a in parser._actions
                if isinstance(a, argparse._SubParsersAction))


def _action(action):
    attrs = ('option_strings', 'dest', 'required', 'nargs', 'choices', 'const',
             'default', 'help', 'metavar')
    result = {key: getattr(action, key) for key in attrs}
    result['type'] = getattr(action.type, '__qualname__', action.type)
    return result


@pytest.mark.parametrize('command', NAMES)
def test_registered_contract_and_help(parsers, command):
    before, after = (_choices(p)[command] for p in parsers)
    assert [_action(a) for a in before._actions] == [_action(a) for a in after._actions]
    assert before.format_help() == after.format_help()
    assert before.format_usage() == after.format_usage()
    assert before.get_default('func').__name__ == after.get_default('func').__name__
    assert [(g.required, [a.dest for a in g._group_actions])
            for g in before._mutually_exclusive_groups] == [
                (g.required, [a.dest for a in g._group_actions])
                for g in after._mutually_exclusive_groups]


ARGS = [
    ['codex-heatmaps', '--input', 'a.csv', 'b.csv', '--outdir', 'out'],
    ['codex-heatmaps', '--input', 'a.csv', '--outdir', 'out', '--normalization', 'raw',
     '--top-rows', '0', '--rows-per-panel', '9', '--columns-per-panel', '8',
     '--annotate', 'none', '--citation', 'one', '--citation', 'two',
     '--title', 'Unicode Δ', '--claim-prefix', 'PRIVATE'],
    ['codex-figure-catalog', '--outdir', 'out'],
    ['codex-figure-catalog', '--outdir', 'out', '--family', 'MPG', '--status', 'HOLD'],
    ['codex-figure-sets', '--widget-data', 'widget.json', '--outdir', 'out'],
    ['codex-figure-sets', '--widget-data', 'widget.json', '--outdir', 'out',
     '--tranche', '6', '--source-bundle', 'source', '--lead-ledger', 'leads'],
    ['codex-bigscape-figure-sets', '--bigscape-tsv', 'source.tsv', '--bigscape-run', 'run',
     '--bigscape-cutoffs', '0.3,0.6', '--run-manifest', 'manifest', '--outdir', 'out'],
    ['codex-bigscape-figure-sets', '--bigscape-db', 'source.db', '--bigscape-run', 'run',
     '--bigscape-cutoffs', '0.3', '--bgc-bridge', 'bridge', '--lead-ledger', 'leads',
     '--outdir', 'out'],
    ['codex-figure-sources', '--widget-data', 'widget.json', '--package-dir', 'packages',
     '--outdir', 'out'],
]


@pytest.mark.parametrize('argv', ARGS)
def test_parsed_defaults_and_explicit_options(parsers, argv):
    left, right = (vars(p.parse_args(argv)) for p in parsers)
    assert left.pop('func').__name__ == right.pop('func').__name__
    assert left == right


BAD_ARGS = [
    ['codex-heatmaps', '--outdir', 'out'],
    ['codex-heatmaps', '--input', 'a', '--outdir', 'out', '--normalization', 'bad'],
    ['codex-heatmaps', '--input', 'a', '--outdir', 'out', '--top-rows', 'bad'],
    ['codex-figure-catalog'],
    ['codex-figure-sets', '--widget-data', 'w', '--outdir', 'out', '--tranche', 'bad'],
    ['codex-bigscape-figure-sets', '--bigscape-run', 'r', '--bigscape-cutoffs', '0.3', '--outdir', 'o'],
    ['codex-bigscape-figure-sets', '--bigscape-run', 'r', '--bigscape-cutoffs', '0.3',
     '--outdir', 'o', '--bigscape-db', 'd', '--bigscape-tsv', 't'],
    ['codex-figure-sources', '--widget-data', 'w', '--outdir', 'o'],
]


def _call(function, arg):
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        try:
            result = ('return', function(arg))
        except (Exception, SystemExit) as exc:
            result = ('exception', type(exc).__name__, str(exc))
    return result, stdout.getvalue(), stderr.getvalue()


@pytest.mark.parametrize('argv', BAD_ARGS)
def test_parser_refusal_bytes(parsers, argv):
    assert _call(parsers[0].parse_args, argv) == _call(parsers[1].parse_args, argv)


@pytest.mark.parametrize('command,name', NAMES.items())
def test_legacy_handler_binding_remains_patchable(monkeypatch, command, name):
    sentinel = lambda args: 17
    monkeypatch.setattr(cli, name, sentinel)
    assert _choices(cli.build_parser())[command].get_default('func') is sentinel
    assert getattr(figure_factory_cli, name).__name__ == name


MODULES = {
    'codex_heatmap_pack': 'build_codex_heatmap_pack',
    'figure_set_registry': 'emit_registry',
    'figure_set_renderer': 'render_tranche',
    **{f'figure_set_renderer_tranche{i}': f'render_tranche_{i}' for i in range(2, 7)},
    'figure_atlas': 'render_implemented_atlas',
    'bigscape_extension': 'render_bigscape_extension',
    'figure_source_bundle': 'build_source_bundle',
}


HANDLER_CASES = [
    ('_codex_heatmaps_command', {}),
    ('_codex_heatmaps_command', {'normalization': 'raw', 'top_rows': 0, 'title': 'Δ',
     'rows_per_panel': 2, 'columns_per_panel': 3, 'annotate': 'none',
     'citation': ['one', 'two'], 'claim_prefix': 'PRIVATE'}),
    ('_codex_figure_catalog_command', {}),
    ('_codex_figure_catalog_command', {'family': 'MPG', 'status': 'HOLD'}),
    *[('_codex_figure_sets_command', {'tranche': str(i), 'source_bundle': 'source',
        'lead_ledger': 'leads'}) for i in range(1, 7)],
    ('_codex_figure_sets_command', {'tranche': 'all', 'source_bundle': 'source'}),
    ('_codex_figure_sets_command', {'tranche': 'all', 'source_bundle': 'source', 'lead_ledger': 'leads'}),
    ('_codex_bigscape_figure_sets_command', {'bigscape_tsv': 'table', 'bigscape_db': None}),
    ('_codex_bigscape_figure_sets_command', {'bigscape_tsv': None, 'bigscape_db': 'database'}),
    ('_codex_figure_sources_command', {}),
]


def _stubs(monkeypatch, calls, result, error=None):
    for module, name in MODULES.items():
        fake = types.ModuleType('mamey.interactive_figures.' + module)
        def target(*args, _name=name, **kwargs):
            calls.append((_name, args, kwargs))
            if error:
                raise error
            return result
        setattr(fake, name, target)
        monkeypatch.setitem(sys.modules, fake.__name__, fake)


def _args(tmp_path, values):
    matrix = tmp_path / 'matrix.csv'
    matrix.write_text('id,value\na,1\n')
    defaults = dict(input=[str(matrix)], outdir='out', widget_data='widget',
                    package_dir='packages', bigscape_run='run', bigscape_cutoffs='0.3',
                    run_manifest='manifest', bgc_bridge='bridge', lead_ledger=None)
    defaults.update(values)
    return argparse.Namespace(**defaults)


@pytest.mark.parametrize('status', ['PASS', 'PASS_WITH_ISSUES', 'HOLD'])
@pytest.mark.parametrize('name,values', HANDLER_CASES)
def test_delegation_outputs_and_return_codes(original, monkeypatch, tmp_path, status, name, values):
    calls = []
    result = dict(status=status, implemented_count=2, implemented_ids=['Δ', 'two'],
                  extension_ids=['x'], run_id='run', cutoffs=[0.3], strain_count=3,
                  present_package_count=2, missing_member_count=1, outputs={'csv': 'a.csv'},
                  extra='not all handlers emit this')
    _stubs(monkeypatch, calls, result)
    args = _args(tmp_path, values)
    before = _call(original[name], args)
    before_calls = list(calls)
    calls.clear()
    assert _call(getattr(figure_factory_cli, name), args) == before
    assert calls == before_calls
    assert len(calls) == 1
    assert before[0] == ('return', 0 if status == 'PASS' or (
        name == '_codex_figure_sources_command' and status == 'PASS_WITH_ISSUES') else 1)


@pytest.mark.parametrize('values', [{'tranche': '2'}, {'tranche': '6', 'source_bundle': 'source'}])
def test_missing_tranche_dependencies_preserve_refusal(original, monkeypatch, tmp_path, values):
    calls = []
    _stubs(monkeypatch, calls, {'status': 'PASS'})
    args = _args(tmp_path, values)
    before = _call(original['_codex_figure_sets_command'], args)
    assert before[0][0:2] == ('exception', 'ValueError')
    assert _call(figure_factory_cli._codex_figure_sets_command, args) == before
    assert calls == []


@pytest.mark.parametrize('bad_kind', ['missing', 'directory', 'value_error', 'runtime_error'])
def test_heatmap_refusal_and_exception_contract(original, monkeypatch, tmp_path, bad_kind):
    calls = []
    error = {'value_error': ValueError('bad matrix'), 'runtime_error': RuntimeError('sentinel')}.get(bad_kind)
    _stubs(monkeypatch, calls, {'status': 'PASS'}, error)
    args = _args(tmp_path, {})
    if bad_kind in {'missing', 'directory'}:
        args.input = [str(tmp_path / 'absent')] if bad_kind == 'missing' else [str(tmp_path)]
    before = _call(original['_codex_heatmaps_command'], args)
    before_calls = list(calls)
    calls.clear()
    assert _call(figure_factory_cli._codex_heatmaps_command, args) == before
    assert calls == before_calls
    assert before[0] == (('exception', 'RuntimeError', 'sentinel') if bad_kind == 'runtime_error' else ('return', 1))
