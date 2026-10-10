"""Progress and dependency warnings use logging; refusals keep their stderr channel."""
from pathlib import Path
import builtins
import importlib.util
import json
import logging
import os
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = Path(os.environ.get('SAPOTE_TEST_REFERENCE_ROOT', ROOT))
sys.path.insert(0, str(REFERENCE))
sys.path.insert(0, str(REFERENCE / 'tools'))
sys.path.insert(0, str(REFERENCE / 'tests'))
from mamey import logging_setup


def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(os.environ.get('SAPOTE_TEST_TOOL_ROOT', ROOT)) / 'tools' / (name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def records():
    logging_setup.configure('info')
    got = []
    class Capture(logging.Handler):
        def emit(self, record):
            got.append(record)
    handler = Capture()
    targets = [logging_setup.get_logger(name) for name in
               ['gap_rescue_gene_table', 'locus_reading_pages', 'protein_pcoa_compare',
                'protein_pcoa_compare.refusal']]
    for logger in targets:
        logger.addHandler(handler)
    yield got
    for logger in targets:
        logger.removeHandler(handler)
    logging_setup.configure('info')


def test_missing_plot_libraries_still_show_warnings(tmp_path, monkeypatch, capsys, records):
    mod = load('gap_rescue_gene_table')
    original = builtins.__import__
    def absent(name, *args, **kwargs):
        if name.split('.')[0] in {'matplotlib', 'PIL', 'pypdf'}:
            raise ImportError('synthetic missing optional dependency')
        return original(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', absent)
    logging_setup.configure('warning')
    assert mod._draw([], 'fixture', 'fixture', tmp_path/'a.png', tmp_path/'a.pdf') is False
    for name in ['gap_rescue.png', 'gap_rescue.pdf', 'gene_table.png', 'gene_table.pdf']:
        (tmp_path/name).touch()
    assert mod.pair_with_map(tmp_path) == []
    out = capsys.readouterr()
    for library in ['matplotlib', 'Pillow', 'pypdf']:
        assert library + ' absent:' in out.out
    assert out.err == ''
    assert len(records) == 3
    assert all(r.levelno == logging.WARNING for r in records)


def test_gene_table_completion_message_is_logged_and_visible(tmp_path, monkeypatch, capsys, records):
    mod = load('gap_rescue_gene_table')
    import gap_directed_rescue
    monkeypatch.setattr(gap_directed_rescue, 'load_genome', lambda *a: ({}, []))
    monkeypatch.setattr(mod, 'edge_shares', lambda *a: {})
    monkeypatch.setattr(mod, 'write_gene_table', lambda *a: {'rows': 3})
    (tmp_path/'gap_rescue_receipt.json').write_text(json.dumps({'label': 'fixture', 'core': 'fixture'}))
    (tmp_path/'gap_rescue.tsv').write_text('name\n')
    assert mod.main(['--run', str(tmp_path), '--zip', 'fixture.zip', '--reference', 'fixture.gbk']) == 0
    assert capsys.readouterr().out == f'[gap_rescue_gene_table] 3 rows -> {tmp_path}\n'
    assert [r.levelno for r in records] == [logging.INFO]


def test_pcoa_completion_and_refusal_keep_text_and_streams(tmp_path, monkeypatch, capsys, records):
    from test_449_protein_pcoa_compare import _kit
    mod = load('protein_pcoa_compare')
    kit = _kit(tmp_path)
    out = tmp_path/'output'
    argv = ['--kit', str(kit), '--cohort', str(tmp_path/'cohort.tsv'), '--out', str(out),
            '--no-figures', '--permutations', '10']
    assert mod.main(argv) == 0
    captured = capsys.readouterr()
    assert '[protein_pcoa_compare] 2 sets, collections ' in captured.out
    assert captured.err == ''
    assert any(r.levelno == logging.INFO and '2 sets' in r.getMessage() for r in records)
    logging_setup.configure('warning')
    assert mod.main(argv) == 2
    captured = capsys.readouterr()
    assert captured.out == ''
    assert '[protein_pcoa_compare] REFUSED:' in captured.err
    assert any(r.levelno == logging.ERROR and 'REFUSED:' in r.getMessage() for r in records)
    # A second redirected/captured stderr must not retain the earlier stream or duplicate a refusal.
    assert mod.main(argv) == 2
    assert capsys.readouterr().err.count('REFUSED:') == 1


def test_locus_page_completion_message_survives_stdout_capture(tmp_path, monkeypatch, capsys, records):
    import test_449_locus_reading_pages as fixtures
    mod = load('locus_reading_pages')
    monkeypatch.setattr(fixtures, 'lrp', mod)
    data = fixtures.fx.__wrapped__(tmp_path)
    assert mod.main(fixtures._argv(data, tmp_path/'pages')) == 0
    captured = capsys.readouterr()
    assert '2 pages,' in captured.out
    assert any(r.levelno == logging.INFO and '2 pages,' in r.getMessage() for r in records)
