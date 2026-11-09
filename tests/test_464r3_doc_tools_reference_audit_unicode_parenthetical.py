"""Synthetic OOXML only: a non-ASCII author-year parenthetical is read, not silently skipped."""
import importlib.util
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('paper_reference_audit_unicode_464r3', ROOT / 'tools' / 'paper_reference_audit.py')
pra = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pra)
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def _docx(path, paragraphs):
    body = []
    for text, style in paragraphs:
        props = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ''
        body.append(f'<w:p>{props}<w:r><w:t>{escape(text)}</w:t></w:r></w:p>')
    parts = {
        '[Content_Types].xml': '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        '_rels/.rels': '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>',
        'word/document.xml': f'<w:document xmlns:w="{W}"><w:body>{"".join(body)}<w:sectPr/></w:body></w:document>',
    }
    with zipfile.ZipFile(path, 'w') as archive:
        for key, value in sorted(parts.items()):
            archive.writestr(zipfile.ZipInfo(key, date_time=(2020, 1, 1, 0, 0, 0)), value)
    return path


@pytest.mark.parametrize('surname', ['王', 'Ωmega', '김'])
def test_non_ascii_parenthetical_cites_its_reference(tmp_path, surname):
    path = _docx(tmp_path / 'paper.docx', [
        (f'Earlier work reported this ({surname} 2020).', ''),
        ('References', 'Heading1'),
        (f'{surname} 2020. A synthetic reference title.', ''),
    ])
    report = pra.audit([('main', path)])
    assert report['uncited_references'] == [], report
    assert report['missing_references'] == []


def test_year_joined_to_name_is_held_not_confirmed_uncited(tmp_path):
    path = _docx(tmp_path / 'paper.docx', [
        ('Earlier work reported this (王2020).', ''),
        ('References', 'Heading1'),
        ('王 2020. A synthetic reference title.', ''),
    ])
    report = pra.audit([('main', path)])
    assert report['status'] == 'INCOMPLETE'
    assert any(h['code'] == 'UNSUPPORTED_CITATION' and '王2020' in h['token'] for h in report['parsing_holds'])
    assert all(not row['confirmed'] for row in report['uncited_references'])
