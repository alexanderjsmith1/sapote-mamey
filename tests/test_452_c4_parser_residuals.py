"""Unexecuted residual controls against qualified C4 parser a20ba7a5.

Install into an isolated tests/ directory; no execution lease is implied. Uses
stdlib/pytest, the bound parser and original synthetic DOCX factory only. The
fixtures are structural OOXML controls, not real Word-render/schema acceptance.
"""
import importlib.util
from pathlib import Path
import sys

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
    return (_load(ROOT / 'tools/paper_reference_audit.py', 'c4_residual_parser'),
            _load(ROOT / 'tests/test_452_paper_reference_audit.py', 'c4_residual_fixtures'))


@pytest.mark.parametrize('tag', ['ins', 'del', 'moveFrom', 'moveTo'])
def test_block_revision_wrappers_keep_absence_provisional(modules, tmp_path, tag):
    parser, fixtures = modules
    text_tag = 'delText' if tag == 'del' else 't'
    revision = (f'<w:{tag} w:id="1" w:author="Synthetic" w:date="2020-01-01T00:00:00Z">'
                f'<w:p><w:r><w:{text_tag}>Revision content.</w:{text_tag}></w:r></w:p>'
                f'</w:{tag}>')
    content = (f'<w:document xmlns:w="{fixtures.W}"><w:body>{revision}'
               '<w:p><w:r><w:t>(Missing, 2020).</w:t></w:r></w:p>'
               '<w:p><w:r><w:t>References</w:t></w:r></w:p>'
               '<w:p><w:r><w:t>Aylward FO. 2012. Synthetic reference.</w:t></w:r></w:p>'
               '</w:body></w:document>')
    path = fixtures.docx(tmp_path, [], extra_parts={'word/document.xml': content})
    report = parser.audit([('main', path)])
    assert 'TRACKED_CHANGES_PRESENT' in {row['code'] for row in report['parsing_holds']}
    assert report['status'] == 'INCOMPLETE'
    assert report['missing_references'] and report['uncited_references']
    assert not any(row['confirmed'] for row in report['missing_references'] + report['uncited_references'])


def test_move_from_ancestor_does_not_become_visible_text(modules, tmp_path):
    """Propagate the parser's existing moveFrom exclusion to an ancestor wrapper."""
    parser, fixtures = modules
    content = (f'<w:document xmlns:w="{fixtures.W}"><w:body>'
               '<w:moveFrom w:id="1" w:author="Synthetic" w:date="2020-01-01T00:00:00Z">'
               '<w:p><w:r><w:t>Moved-away content.</w:t></w:r></w:p></w:moveFrom>'
               '<w:p><w:r><w:t>Remaining content.</w:t></w:r></w:p>'
               '</w:body></w:document>')
    path = fixtures.docx(tmp_path, [], extra_parts={'word/document.xml': content})
    paragraphs, holds, binding = parser.read_docx(path, 'main')
    assert 'Moved-away content.' not in [row['text'] for row in paragraphs]
    assert 'Remaining content.' in [row['text'] for row in paragraphs]
    assert 'TRACKED_CHANGES_PRESENT' in {row['code'] for row in holds}


@pytest.mark.parametrize('kind,callout', [('Figure', 'Fig.'), ('Table', 'Table')])
@pytest.mark.parametrize('prefix', ['', 'S'])
@pytest.mark.parametrize('callout_number', ['1', '01'])
def test_zero_padded_caption_and_callout_share_number_key(modules, tmp_path, kind, callout, prefix, callout_number):
    parser, fixtures = modules
    path = fixtures.docx(tmp_path, [f'See {callout} {prefix}{callout_number}.',
                                   f'{kind} {prefix}01. Synthetic caption.',
                                   '(Aylward, 2012).', 'References',
                                   'Aylward FO. 2012. Synthetic reference.'])
    report = parser.audit([('main', path)])
    assert not report['parsing_holds']
    assert not report['undefined_callouts']
    assert not report['uncalled_captions']


def test_range_policy_exactly_200_values_remains_accepted(modules):
    """Preservation control; not a failing-before claim or proposed limit change."""
    parser, fixtures = modules
    values = parser.number_list('1-200')
    assert len(values) == 200
    assert values[0] == '1' and values[-1] == '200'


def test_range_policy_more_than_200_values_remains_held(modules):
    parser, fixtures = modules
    with pytest.raises(ValueError, match='oversized range'):
        parser.number_list('1-201')
