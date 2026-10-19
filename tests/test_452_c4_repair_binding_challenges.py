"""Additional unexecuted C4 source-binding controls; coordinator-only runtime.

Install this file under an isolated bundle's tests/ before scheduling. Imports
are limited to stdlib, pytest and the two bound local modules. No real DOCX,
network, subprocess, renderers or analyses. Fixture writes stay under tmp_path.
"""
import hashlib
import importlib.util
from pathlib import Path
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def modules():
    parser = _load(ROOT / 'tools/paper_reference_audit.py', 'c4_independent_parser')
    fixtures = _load(ROOT / 'tests/test_452_paper_reference_audit.py', 'c4_independent_fixture_source')
    return parser, fixtures


def _part(w, root, text):
    return f'<w:{root} xmlns:w="{w}"><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:{root}>'


def _raw_hashes(path, names):
    with zipfile.ZipFile(path) as archive:
        return {name: hashlib.sha256(archive.read(name)).hexdigest() for name in names}


def test_all_consumed_xml_hashes_and_unconsumed_parts(modules, tmp_path):
    parser, fixtures = modules
    parts = {
        'word/footnotes.xml': _part(fixtures.W, 'footnotes', 'Footnote source.'),
        'word/endnotes.xml': _part(fixtures.W, 'endnotes', 'Endnote source.'),
        'word/header1.xml': _part(fixtures.W, 'hdr', 'Header source.'),
        'word/footer1.xml': _part(fixtures.W, 'ftr', 'Footer source.'),
        'word/comments.xml': _part(fixtures.W, 'comments', 'Not a citation source.'),
        'word/settings.xml': '<settings/>',
    }
    source = fixtures.docx(tmp_path, ['Main source.'], extra_parts=parts)
    consumed = {'word/document.xml', 'word/footnotes.xml', 'word/endnotes.xml',
                'word/header1.xml', 'word/footer1.xml'}
    expected = _raw_hashes(source, consumed)
    original = source.read_bytes()
    paragraphs, holds, binding = parser.read_docx(source, 'main')
    assert binding['xml_parts_sha256'] == expected
    assert {row['part'] for row in paragraphs} == consumed
    assert binding['sha256'] == hashlib.sha256(original).hexdigest()
    assert source.read_bytes() == original


def test_atomic_replacement_between_parts_keeps_original_all_parts(modules, tmp_path, monkeypatch):
    parser, fixtures = modules
    source = fixtures.docx(tmp_path, ['Original main.'], 'source.docx', {
        'word/footnotes.xml': _part(fixtures.W, 'footnotes', 'Original note.')})
    replacement = fixtures.docx(tmp_path, ['Replacement main.'], 'replacement.docx', {
        'word/footnotes.xml': _part(fixtures.W, 'footnotes', 'Replacement note.')})
    original = source.read_bytes()
    original_hashes = _raw_hashes(source, {'word/document.xml', 'word/footnotes.xml'})
    real_parse = parser.ET.fromstring
    replaced = False
    def switch_after_main(raw, *args, **kwargs):
        nonlocal replaced
        if not replaced:
            replacement.replace(source)
            replaced = True
        return real_parse(raw, *args, **kwargs)
    monkeypatch.setattr(parser.ET, 'fromstring', switch_after_main)
    paragraphs, holds, binding = parser.read_docx(source, 'main')
    assert replaced
    assert [row['text'] for row in paragraphs] == ['Original main.', 'Original note.']
    assert binding['sha256'] == hashlib.sha256(original).hexdigest()
    assert binding['xml_parts_sha256'] == original_hashes
    assert hashlib.sha256(source.read_bytes()).hexdigest() != binding['sha256']


def test_unlinked_selector_still_binds_consumed_descriptor(modules, tmp_path, monkeypatch):
    parser, fixtures = modules
    source = fixtures.docx(tmp_path, ['Original main.'])
    original = source.read_bytes()
    selector = str(source.absolute())
    real_parse = parser.ET.fromstring
    def unlink_after_xml_read(raw, *args, **kwargs):
        source.unlink()
        return real_parse(raw, *args, **kwargs)
    monkeypatch.setattr(parser.ET, 'fromstring', unlink_after_xml_read)
    paragraphs, holds, binding = parser.read_docx(source, 'main')
    assert not source.exists()
    assert paragraphs[0]['text'] == 'Original main.'
    assert binding['path'] == selector
    assert binding['sha256'] == hashlib.sha256(original).hexdigest()


def test_unconsumed_part_drift_refuses_cli_without_partial_json(modules, tmp_path, monkeypatch, capsys):
    parser, fixtures = modules
    source = fixtures.docx(tmp_path, ['Original main.'], extra_parts={
        'word/comments.xml': '<comments>old-comment</comments>'})
    original = source.read_bytes()
    assert original.count(b'old-comment') == 1
    changed = original.replace(b'old-comment', b'new-comment')
    real_parse = parser.ET.fromstring
    def mutate_unconsumed_part(raw, *args, **kwargs):
        source.write_bytes(changed)
        return real_parse(raw, *args, **kwargs)
    monkeypatch.setattr(parser.ET, 'fromstring', mutate_unconsumed_part)
    assert parser.main([str(source)]) == 2
    streams = capsys.readouterr()
    assert streams.out == ''
    assert 'SOURCE_CHANGED_DURING_READ' in streams.err


def test_small_doc_first_archive_inplace_drift_is_not_hidden_by_buffer(modules, tmp_path, monkeypatch):
    """Challenge ordinary descriptor hashing against Python's buffered read cache.

    OPC member order is unconstrained. Existing synthetic fixtures sort document.xml
    after metadata; this fixture puts it first so a small BufferedReader cache can
    include byte zero when the post-parse hash rewinds. No ABA restoration is used.
    This challenge has not been executed and is not a confirmed runtime finding.
    """
    parser, fixtures = modules
    source = fixtures.docx(tmp_path, ['Original main.'])
    with zipfile.ZipFile(source) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    ordered = tmp_path / 'document_first.docx'
    with zipfile.ZipFile(ordered, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name in ['word/document.xml'] + sorted(set(parts) - {'word/document.xml'}):
            archive.writestr(zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0)), parts[name])
    original = ordered.read_bytes()
    assert len(original) < 8192
    assert original.count(b'Original main.') == 1
    changed = original.replace(b'Original main.', b'Modified main.')
    real_parse = parser.ET.fromstring
    def mutate_after_xml_read(raw, *args, **kwargs):
        ordered.write_bytes(changed)
        return real_parse(raw, *args, **kwargs)
    monkeypatch.setattr(parser.ET, 'fromstring', mutate_after_xml_read)
    with pytest.raises(ValueError, match='SOURCE_CHANGED_DURING_READ'):
        parser.read_docx(ordered, 'main')
