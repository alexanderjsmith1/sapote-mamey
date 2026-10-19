"""Synthetic OOXML parser acceptance inputs; no papers, network or renderers."""
import importlib.util
import json
from pathlib import Path
import zipfile
from xml.sax.saxutils import escape

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools' / 'paper_reference_audit.py'
W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def test_requested_offline_docx_audit_exists():
    # This is a test-body assertion: missing capability is a FAIL, not collection/setup ERROR.
    assert TOOL.is_file(), 'Missing requested offline DOCX reference audit capability'


@pytest.fixture
def auditor():
    # Baseline fails this explicit capability assertion, never at collection/import.
    assert TOOL.is_file(), 'Missing requested offline DOCX reference audit capability'
    spec = importlib.util.spec_from_file_location('paper_reference_audit', TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def docx(tmp_path, paragraphs, name='synthetic.docx', extra_parts=None):
    """Minimal deterministic OPC/DOCX fixture built only inside pytest tmp_path.

    Strings produce visible paragraphs; (text, style) tuples supply paragraph styles.
    No binary DOCX artifact is authored or delivered during card preparation.
    """
    body = []
    for value in paragraphs:
        text, style = value if isinstance(value, tuple) else (value, '')
        props = f'<w:pPr><w:pStyle w:val="{escape(style)}"/></w:pPr>' if style else ''
        body.append(f'<w:p>{props}<w:r><w:t>{escape(text)}</w:t></w:r></w:p>')
    document = f'<w:document xmlns:w="{W}"><w:body>{"".join(body)}<w:sectPr/></w:body></w:document>'
    content_types = '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'
    rels = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
    path = tmp_path / name
    parts = {'[Content_Types].xml': content_types, '_rels/.rels': rels, 'word/document.xml': document}
    parts.update(extra_parts or {})
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_STORED) as archive:
        for key, value in sorted(parts.items()):
            info = zipfile.ZipInfo(key, date_time=(2020, 1, 1, 0, 0, 0))
            archive.writestr(info, value)
    return path


def audit(auditor, path, **kwargs):
    return auditor.audit([('main', path)], **kwargs)


def codes(report):
    return {row['code'] for row in report['parsing_holds']}


def test_author_year_reports_missing_and_uncited(auditor, tmp_path):
    path = docx(tmp_path, ['Read (Aylward et al., 2012; Missing, 2020).', 'References', 'Aylward FO, Currie CR. 2012. Synthetic alpha.', 'Unused AB. 2021. Synthetic beta.'])
    report = audit(auditor, path)
    assert report['status'] == 'PARSED_SUPPORTED_SYNTAX'
    assert [(r['key'], r['confirmed']) for r in report['missing_references']] == [(('missing', '2020'), True)]
    assert [r['token'] for r in report['uncited_references']] == ['Unused AB. 2021. Synthetic beta.']


def test_aylward_fo_initials_are_not_surname(auditor, tmp_path):
    path = docx(tmp_path, ['Aylward et al. (2012) and (Aylward, 2012).', 'References', 'Aylward FO, Currie CR. 2012. Synthetic title.'])
    report = audit(auditor, path)
    assert not report['missing_references']
    assert not report['uncited_references']
    assert not report['parsing_holds']


@pytest.mark.parametrize('name,reference', [('Van Arnam', 'Van Arnam EB, Currie CR. 2018. Synthetic title.'), ('van der Waals', 'van der Waals, J. D. (1873). Synthetic title.'), ("O’Neill", "O’Neill AB. 2020. Synthetic title.")])
def test_particle_and_unicode_surnames(auditor, tmp_path, name, reference):
    year = '2018' if name == 'Van Arnam' else ('1873' if name == 'van der Waals' else '2020')
    report = audit(auditor, docx(tmp_path, [f'{name} ({year}) and ({name}, {year}).', 'References', reference]))
    assert not report['missing_references']
    assert not report['uncited_references']
    assert not report['parsing_holds']


def test_corporate_author(auditor, tmp_path):
    path = docx(tmp_path, ['World Health Organization (2020); (World Health Organization, 2020).', 'References', 'World Health Organization. (2020). Synthetic title.'])
    report = audit(auditor, path)
    assert not report['missing_references']
    assert not report['uncited_references']
    assert not report['parsing_holds']


def test_supplementary_only_citation_counts(auditor, tmp_path):
    main = docx(tmp_path, ['Main text.', 'References', 'Aylward FO. 2012. Synthetic title.'], 'main.docx')
    supp = docx(tmp_path, ['Supplementary information', 'Only here (Aylward, 2012).'], 'supp.docx')
    report = auditor.audit([('main', main), ('supplementary', supp)])
    assert not report['missing_references']
    assert not report['uncited_references']
    assert len(report['inputs']) == 2
    assert not report['parsing_holds']


def test_supplementary_section_after_references(auditor, tmp_path):
    path = docx(tmp_path, ['References', 'Van Arnam EB. 2018. Synthetic title.', ('Supplementary information', 'Heading1'), 'Only here (Van Arnam, 2018).'])
    report = audit(auditor, path)
    assert not report['missing_references']
    assert not report['uncited_references']


def test_figs_s19_s20_and_s21(auditor, tmp_path):
    path = docx(tmp_path, ['See Figs. S19, S20 and S21.', 'Figure S19. Synthetic alpha.', 'Figure S20. Synthetic beta.', 'Figure S21. Synthetic gamma.', 'References', 'Aylward FO. 2012. Synthetic title.', 'Supplementary information', '(Aylward, 2012).'])
    report = audit(auditor, path)
    assert not report['undefined_callouts']
    assert not report['uncalled_captions']
    assert not report['parsing_holds']


def test_figure_and_table_defined_uncalled_and_undefined(auditor, tmp_path):
    path = docx(tmp_path, ['See Fig. 2 and Tables 2, 3.', 'Figure 1. Synthetic alpha.', 'Table 2: Synthetic beta.', 'References', 'Aylward FO. 2012. Synthetic title.'])
    report = audit(auditor, path)
    assert {r['token'] for r in report['undefined_callouts']} == {'figure 2', 'table 3'}
    assert {r['token'] for r in report['uncalled_captions']} == {'figure 1'}
    assert all(r['confirmed'] for r in report['undefined_callouts'] + report['uncalled_captions'])


def test_caption_can_call_another_figure(auditor, tmp_path):
    path = docx(tmp_path, ['Figure 1. Compare Fig. 2.', 'Figure 2. Synthetic title.', 'References', 'Aylward FO. 2012. Synthetic title.'])
    report = audit(auditor, path)
    assert [r['token'] for r in report['uncalled_captions']] == ['figure 1']
    assert not report['undefined_callouts']


def test_numbered_style_lists_and_ranges(auditor, tmp_path):
    path = docx(tmp_path, ['Evidence [1, 2–3, 5].', 'References', '[1] Synthetic one.', '[2] Synthetic two.', '[3] Synthetic three.', '[4] Synthetic four.'])
    report = audit(auditor, path)
    assert report['style'] == 'numbered'
    assert [r['key'] for r in report['missing_references']] == ['5']
    assert [r['token'] for r in report['uncited_references']] == ['[4] Synthetic four.']


def test_document_reference_scope_avoids_shared_number_collisions(auditor, tmp_path):
    main = docx(tmp_path, ['Cited [1].', 'References', '[1] Synthetic main.'], 'main.docx')
    supp = docx(tmp_path, ['Cited [1].', 'References', '[1] Synthetic supp.'], 'supp.docx')
    paths = [('main', main), ('supplementary', supp)]
    combined = auditor.audit(paths)
    assert 'AMBIGUOUS_REFERENCE_KEY' in codes(combined)
    scoped = auditor.audit(paths, reference_scope='document')
    assert not scoped['parsing_holds']
    assert not scoped['uncited_references']


def test_unsupported_reference_cannot_confirm_missing(auditor, tmp_path):
    report = audit(auditor, docx(tmp_path, ['(Missing, 2020).', 'References', 'Aylward FO. 2012. Synthetic title.', 'Unparseable reference without a year.']))
    assert 'UNSUPPORTED_REFERENCE' in codes(report)
    assert report['missing_references'][0]['code'] == 'UNRESOLVED_CITATION'
    assert report['missing_references'][0]['confirmed'] is False


def test_ambiguous_key_is_not_missing_or_confirmed_uncited(auditor, tmp_path):
    report = audit(auditor, docx(tmp_path, ['(Aylward, 2012).', 'References', 'Aylward FO. 2012. Synthetic alpha.', 'Aylward FO. 2012. Synthetic beta.']))
    assert 'AMBIGUOUS_REFERENCE_KEY' in codes(report)
    assert not report['missing_references']
    assert not any(r['confirmed'] for r in report['uncited_references'])


def test_year_suffixes_and_multiple_years(auditor, tmp_path):
    report = audit(auditor, docx(tmp_path, ['(Aylward, 2012a, 2012b).', 'References', 'Aylward FO. 2012a. Synthetic alpha.', 'Aylward FO. 2012b. Synthetic beta.']))
    assert not report['missing_references']
    assert not report['uncited_references']


def test_unsupported_narrative_is_a_hold(auditor, tmp_path):
    report = audit(auditor, docx(tmp_path, ['Unknown et al. (2020).', 'References', 'Aylward FO. 2012. Synthetic title.']))
    assert 'UNSUPPORTED_NARRATIVE_CITATION' in codes(report)
    assert not report['missing_references']
    assert not report['uncited_references'][0]['confirmed']


def test_panel_and_ambiguous_caption_are_holds(auditor, tmp_path):
    report = audit(auditor, docx(tmp_path, ['See Fig. 1a.', ('Figure 1 Synthetic title', 'Caption'), 'References', 'Aylward FO. 2012. Synthetic title.']))
    assert {'UNSUPPORTED_PANEL_CALLOUT', 'AMBIGUOUS_CAPTION_OR_CALLOUT'} <= codes(report)
    assert not any(r['confirmed'] for r in report['undefined_callouts'])


def test_oversized_ranges_are_held(auditor, tmp_path):
    report = audit(auditor, docx(tmp_path, ['Evidence [1-99999]. See Figs. 1-99999.', 'References', '[1] Synthetic title.']))
    assert {'UNSUPPORTED_CITATION', 'UNSUPPORTED_CALLOUT'} <= codes(report)


def test_table_cell_and_footnote_citations(auditor, tmp_path):
    main = f'<w:document xmlns:w="{W}"><w:body><w:tbl><w:tr><w:tc><w:p><w:r><w:t>(Aylward, 2012).</w:t></w:r></w:p></w:tc></w:tr></w:tbl><w:p><w:r><w:t>References</w:t></w:r></w:p><w:p><w:r><w:t>Aylward FO. 2012. Synthetic alpha.</w:t></w:r></w:p><w:p><w:r><w:t>Van Arnam EB. 2018. Synthetic beta.</w:t></w:r></w:p></w:body></w:document>'
    foot = f'<w:footnotes xmlns:w="{W}"><w:footnote w:id="1"><w:p><w:r><w:t>(Van Arnam, 2018).</w:t></w:r></w:p></w:footnote></w:footnotes>'
    path = docx(tmp_path, [], extra_parts={'word/document.xml': main, 'word/footnotes.xml': foot})
    report = audit(auditor, path)
    assert not report['uncited_references']
    assert not report['missing_references']


@pytest.mark.parametrize('xml,code', [('<w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr><w:t>1</w:t></w:r>', 'UNSUPPORTED_SUPERSCRIPT'), ('<w:pPr><w:numPr><w:numId w:val="1"/></w:numPr></w:pPr><w:r><w:t>1</w:t></w:r>', 'UNSUPPORTED_AUTONUMBER'), ('<w:r><w:instrText>REF x</w:instrText><w:t>1</w:t></w:r>', 'CACHED_FIELD_TEXT'), ('<w:del><w:r><w:delText>old</w:delText></w:r></w:del><w:r><w:t>new</w:t></w:r>', 'TRACKED_CHANGES_PRESENT')])
def test_unsupported_ooxml_does_not_confirm_absence(auditor, tmp_path, xml, code):
    content = f'<w:document xmlns:w="{W}"><w:body><w:p>{xml}</w:p><w:p><w:r><w:t>(Missing, 2020).</w:t></w:r></w:p><w:p><w:r><w:t>References</w:t></w:r></w:p><w:p><w:r><w:t>Aylward FO. 2012. Synthetic title.</w:t></w:r></w:p></w:body></w:document>'
    report = audit(auditor, docx(tmp_path, [], extra_parts={'word/document.xml': content}))
    assert code in codes(report)
    assert not report['missing_references'][0]['confirmed']
    assert not report['uncited_references'][0]['confirmed']


def test_no_reference_section_is_incomplete(auditor, tmp_path):
    report = audit(auditor, docx(tmp_path, ['(Aylward, 2012).']))
    assert 'NO_REFERENCE_SECTION' in codes(report)
    assert report['missing_references'][0]['confirmed'] is False


def test_read_only_hash_and_offline_cli(auditor, tmp_path, capsys, monkeypatch):
    import hashlib
    import socket
    def refuse(*args, **kwargs):
        raise AssertionError('Network forbidden')
    monkeypatch.setattr(socket, 'socket', refuse)
    monkeypatch.setattr(socket, 'create_connection', refuse)
    path = docx(tmp_path, ['(Aylward, 2012).', 'References', 'Aylward FO. 2012. Synthetic title.'])
    before = path.read_bytes()
    assert auditor.main([str(path), '--strict']) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['network'] == 'OFF'
    assert report['inputs'][0]['sha256'] == hashlib.sha256(before).hexdigest()
    assert path.read_bytes() == before
    with pytest.raises(SystemExit) as exc:
        auditor.main([str(path), '--crossref'])
    assert exc.value.code == 2


def test_cli_strict_findings_and_holds(auditor, tmp_path, capsys):
    path = docx(tmp_path, ['(Missing, 2020).', 'References', 'Aylward FO. 2012. Synthetic title.'])
    assert auditor.main([str(path), '--strict']) == 1
    capsys.readouterr()
    path = docx(tmp_path, ['Unknown (2020).', 'References', 'Aylward FO. 2012. Synthetic title.'])
    assert auditor.main([str(path), '--strict']) == 2


def test_zip_entities_and_size_refused(auditor, tmp_path, monkeypatch):
    path = docx(tmp_path, ['References', 'Aylward FO. 2012. Synthetic title.'])
    monkeypatch.setattr(auditor, 'MAX_XML', 8)
    with pytest.raises(ValueError, match='size limit'):
        audit(auditor, path)
    monkeypatch.setattr(auditor, 'MAX_XML', 8 * 1024 * 1024)
    content = f'<!DOCTYPE x [<!ENTITY z "x">]><w:document xmlns:w="{W}"><w:body/></w:document>'
    path = docx(tmp_path, [], extra_parts={'word/document.xml': content})
    with pytest.raises(ValueError, match='DTD/entity'):
        audit(auditor, path)


def test_unsupported_chapter_numbers_and_parenthesized_numbers(auditor, tmp_path):
    report = audit(auditor, docx(tmp_path, ['See Fig. 1.2 and (2).', 'References', '[1] Synthetic title.']))
    assert {'UNSUPPORTED_CAPTION_NUMBER', 'AMBIGUOUS_PARENTHESIZED_NUMBER'} <= codes(report)
    assert not report['undefined_callouts']
    assert not report['uncited_references'][0]['confirmed']


def test_utf16_entity_input_is_refused(auditor, tmp_path):
    content = ('<?xml version="1.0" encoding="UTF-16"?><!DOCTYPE x [<!ENTITY z "x">]>'
               f'<w:document xmlns:w="{W}"><w:body/></w:document>').encode('utf-16')
    path = docx(tmp_path, [], extra_parts={'word/document.xml': content})
    with pytest.raises(ValueError, match='UTF-8'):
        audit(auditor, path)


def test_deleted_only_paragraph_still_sets_hold(auditor, tmp_path):
    content = f'<w:document xmlns:w="{W}"><w:body><w:p><w:del><w:r><w:delText>Old text</w:delText></w:r></w:del></w:p><w:p><w:r><w:t>References</w:t></w:r></w:p><w:p><w:r><w:t>Aylward FO. 2012. Synthetic title.</w:t></w:r></w:p></w:body></w:document>'
    report = audit(auditor, docx(tmp_path, [], extra_parts={'word/document.xml': content}))
    assert 'TRACKED_CHANGES_PRESENT' in codes(report)
    assert not report['uncited_references'][0]['confirmed']
