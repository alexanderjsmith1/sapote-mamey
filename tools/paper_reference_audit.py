#!/usr/bin/env python3
"""paper_reference_audit.py — Offline DOCX citation, reference and caption audit.

Read cached visible OOXML text without modifying inputs or fetching literature.
Reports parsing holds separately from confirmed missing reference/callout keys.
See docs/PAPER_REFERENCE_AUDIT.md for supported syntax and claim limits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
YEAR = r'(?:18|19|20)\d{2}[a-z]?'
YEAR_RE = re.compile(r'\b(' + YEAR + r')\b')
REF_HEADING = re.compile(r'^(?:(?:supplementary|supporting)\s+)?(?:references|bibliography|literature cited)\s*[:.]?$', re.I)
NUMBER = re.compile(r'^\s*(?:\[(\d+)\]|(\d+)[.)])\s+(.+)$')
CAPTION = re.compile(r'^\s*(Figure|Fig\.?|Table)\s+(S?\d+)\s*[.:]\s*', re.I)
CALLOUT = re.compile(r'\b(Figs?\.?|Figures?|Tables?)\s+(S?\d+(?:\s*(?:,\s*(?:and\s+)?|and\s+|[–-]\s*)S?\d+)*)', re.I)
MAX_XML = 8 * 1024 * 1024
MAX_TOTAL_XML = 32 * 1024 * 1024
MAX_RANGE = 200


def norm(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split())


def issue(code, location, token='', detail=''):
    return dict(code=code, location=location, token=token, detail=detail)


def _has_tag(element, name):
    """Element presence is independent of its child count or truth value."""
    return next(element.iter(W + name), None) is not None


def _stream_sha256(stream):
    """Hash the selected descriptor in bounded chunks and rewind it."""
    stream.seek(0)
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
        digest.update(chunk)
    stream.seek(0)
    return digest.hexdigest()


def read_docx(path, scope):
    """Bounded ZIP reads from one descriptor; no extraction or external targets."""
    path = Path(path)
    selector = str(path.absolute())
    paragraphs, holds, part_hashes = [], [], {}
    with path.open('rb', buffering=0) as source:
        source_hash = _stream_sha256(source)
        with zipfile.ZipFile(source) as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                raise ValueError('duplicate ZIP members')
            if 'word/document.xml' not in names:
                raise ValueError('missing word/document.xml')
            parts = ['word/document.xml'] + sorted(n for n in names if re.fullmatch(r'word/(?:footnotes|endnotes|header\d+|footer\d+)\.xml', n))
            total = 0
            for part in parts:
                info = archive.getinfo(part)
                total += info.file_size
                if info.file_size > MAX_XML or total > MAX_TOTAL_XML:
                    raise ValueError('DOCX XML size limit exceeded')
                raw = archive.read(part)
                part_hashes[part] = hashlib.sha256(raw).hexdigest()
                if b'\x00' in raw:
                    raise ValueError('only UTF-8 DOCX XML is supported')
                try:
                    raw.decode('utf-8-sig')
                except UnicodeDecodeError as exc:
                    raise ValueError('only UTF-8 DOCX XML is supported') from exc
                if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
                    raise ValueError('DTD/entity declarations unsupported')
                root = ET.fromstring(raw)
                if _has_tag(root, 'altChunk'):
                    holds.append(issue('UNSUPPORTED_ALTCHUNK', f'{path}:{part}'))
                revision_tags = {W + name for name in ('ins', 'del', 'moveFrom', 'moveTo')}
                removed_tags = {W + 'del', W + 'moveFrom'}
                removed_paragraphs = set()
                has_revision = False
                pending = [(root, False)]
                while pending:
                    element, removed = pending.pop()
                    has_revision = has_revision or element.tag in revision_tags
                    removed = removed or element.tag in removed_tags
                    if removed and element.tag == W + 'p':
                        removed_paragraphs.add(element)
                    pending.extend((child, removed) for child in element)
                if has_revision:
                    holds.append(issue('TRACKED_CHANGES_PRESENT', f'{path}:{part}',
                                       detail='Revision markup may wrap whole paragraphs.'))
                for index, p in enumerate(root.iter(W + 'p'), 1):
                    if p in removed_paragraphs:
                        continue
                    location = f'{path}:{part}:p{index}'
                    # A paragraph in a text box is visited separately, never twice.
                    pieces = []
                    def visible(node):
                        if node.tag in {W + 'del', W + 'moveFrom', W + 'txbxContent'}:
                            return
                        if node.tag == W + 't':
                            pieces.append(node.text or '')
                        elif node.tag in {W + 'tab', W + 'br', W + 'cr'}:
                            pieces.append(' ')
                        else:
                            for child in node:
                                visible(child)
                    visible(p)
                    text = ' '.join(''.join(pieces).split())
                    style = p.find('./' + W + 'pPr/' + W + 'pStyle')
                    style = style.get(W + 'val', '') if style is not None else ''
                    numbered = p.find('./' + W + 'pPr/' + W + 'numPr') is not None
                    if numbered:
                        holds.append(issue('UNSUPPORTED_AUTONUMBER', location, text))
                    if any(_has_tag(p, name) for name in ('ins', 'del', 'moveFrom', 'moveTo')):
                        holds.append(issue('TRACKED_CHANGES_PRESENT', location, text))
                    if any(_has_tag(p, name) for name in ('instrText', 'fldSimple')):
                        holds.append(issue('CACHED_FIELD_TEXT', location, text, 'Word fields were not refreshed.'))
                    if p.find('.//' + W + 'vertAlign[@' + W + 'val="superscript"]') is not None:
                        holds.append(issue('UNSUPPORTED_SUPERSCRIPT', location, text))
                    if not text:
                        continue
                    paragraphs.append(dict(text=text, location=location, style=style, scope=scope, part=part))
        if _stream_sha256(source) != source_hash:
            raise ValueError('SOURCE_CHANGED_DURING_READ: selected DOCX bytes changed')
    return paragraphs, holds, dict(path=selector, sha256=source_hash, scope=scope,
                                  xml_parts_sha256=part_hashes)


def author_key(prefix):
    """First surname (including particles), or full corporate name before year."""
    prefix = prefix.strip(' (.,;')
    # Surname-first bibliography forms: Aylward FO, Van Arnam EB, Aylward, F. O.
    prefix = re.split(r',|\s+(?:and|&)\s+|\s+et al\.?', prefix, maxsplit=1, flags=re.I)[0]
    prefix = re.sub(r'\s+(?:[A-Z](?:\.?\s*)){1,5}\.?$', '', prefix).strip()
    if not prefix or not any(c.isalpha() for c in prefix) or any(c.isdigit() for c in prefix) or len(prefix.split()) > 8:
        return None
    # Initial-first references require manual interpretation.
    if re.match(r'^[A-Z]\.\s', prefix):
        return None
    return norm(prefix)


def number_list(text):
    """Expand bounded explicit lists/ranges; S prefix carries only across ranges."""
    tokens = re.findall(r'S?\d+|[–-]|,|\band\b', text, re.I)
    if not tokens:
        raise ValueError('empty number list')
    result, index = [], 0
    while index < len(tokens):
        first = tokens[index].upper()
        if not re.fullmatch(r'S?\d+', first):
            raise ValueError('malformed number list')
        index += 1
        if index < len(tokens) and tokens[index] in {'-', '–'}:
            index += 1
            if index >= len(tokens) or not re.fullmatch(r'S?\d+', tokens[index], re.I):
                raise ValueError('malformed range')
            last = tokens[index].upper()
            index += 1
            prefix = 'S' if first.startswith('S') else ''
            if last.startswith('S') and not prefix:
                raise ValueError('mixed main/supplement range')
            start, end = int(first.lstrip('S')), int(last.lstrip('S'))
            if end < start or end - start >= MAX_RANGE:
                raise ValueError('descending or oversized range')
            result.extend(prefix + str(n) for n in range(start, end + 1))
        else:
            result.append(('S' if first.startswith('S') else '') + str(int(first.lstrip('S'))))
        if index < len(tokens):
            if tokens[index] not in {',', 'and'}:
                raise ValueError('missing separator')
            index += 1
            if index < len(tokens) and tokens[index] == 'and':
                index += 1
            if index == len(tokens):
                raise ValueError('trailing separator')
    return result


def split_sections(paragraphs):
    refs, body, holds = [], [], []
    in_refs = False
    for paragraph in paragraphs:
        text = paragraph['text']
        if paragraph['part'] != 'word/document.xml':
            body.append(paragraph)
            continue
        if REF_HEADING.fullmatch(text):
            in_refs = True
            continue
        heading = paragraph['style'].casefold().startswith('heading')
        if in_refs and (heading or re.fullmatch(r'(?:supplementary|supporting) (?:information|material)|(?:figure|table) legends', text, re.I)):
            in_refs = False
        if in_refs:
            refs.append(paragraph)
        else:
            body.append(paragraph)
    if not refs:
        holds.append(issue('NO_REFERENCE_SECTION', '', detail='Use a References/Bibliography heading and one reference per paragraph.'))
    return refs, body, holds


def citations(text, style, known_authors):
    found, holds = [], []
    if style == 'numbered':
        for match in re.finditer(r'\(\s*\d+(?:\s*[,–-]\s*\d+)*\s*\)', text):
            holds.append(('AMBIGUOUS_PARENTHESIZED_NUMBER', match.group(0), 'May be a citation or a measurement; manual review required.'))
        for match in re.finditer(r'\[([^\[\]]+)\]', text):
            token = match.group(1)
            if re.fullmatch(r'[\d\s,–-]+', token):
                try:
                    found.extend((number, match.group(0)) for number in number_list(token))
                except ValueError as exc:
                    holds.append(('UNSUPPORTED_CITATION', match.group(0), str(exc)))
        return found, holds
    occupied = []
    # Parenthetical author-year groups, including repeated years for one author.
    for match in re.finditer(r'\(([^()]*)\)', text):
        inner = match.group(1)
        if not YEAR_RE.search(inner):
            continue
        if re.fullmatch(YEAR + r'(?:\s*,\s*' + YEAR + r')*', inner):
            continue  # narrative handled below
        if not re.search(r'[A-Za-z]', inner):
            continue  # measurements/years are not author keys
        occupied.append(match.span())
        for group in inner.split(';'):
            years = list(YEAR_RE.finditer(group))
            if not years:
                holds.append(('UNSUPPORTED_CITATION', group, 'Mixed parenthetical syntax.'))
                continue
            prefix = group[:years[0].start()].strip(' ,')
            key = author_key(prefix)
            tail = group[years[0].start():]
            expected = re.fullmatch(YEAR + r'(?:\s*,\s*' + YEAR + r')*', tail)
            if not key or not expected:
                holds.append(('UNSUPPORTED_CITATION', group, 'Use author-year groups separated by semicolons.'))
                continue
            found.extend(((key, year.group(1)), group) for year in years)
    # Known complete surname/corporate suffix avoids reading preceding prose as an author.
    narrative = re.compile(r'\(('+YEAR+r'(?:\s*,\s*'+YEAR+r')*)\)')
    for match in narrative.finditer(text):
        if any(a <= match.start() < b for a, b in occupied):
            continue
        before = text[:match.start()].rstrip()
        before = re.sub(r'\s+et al\.?$', '', before, flags=re.I)
        normalized = norm(before)
        matches = [name for name in known_authors if normalized == name or normalized.endswith(' ' + name)]
        if matches:
            name = max(matches, key=len)
            found.extend(((name, year), match.group(0)) for year in YEAR_RE.findall(match.group(1)))
        else:
            holds.append(('UNSUPPORTED_NARRATIVE_CITATION', match.group(0), 'No unambiguous known author suffix; inspect manually.'))
    return found, holds


def audit(paths, style='auto', reference_scope='combined'):
    """Audit main plus supplementary DOCX files. Combined scope is explicit default."""
    if style not in {'auto', 'author-year', 'numbered'}:
        raise ValueError('invalid citation style')
    if reference_scope not in {'combined', 'document'}:
        raise ValueError('invalid reference scope')
    all_refs, body, holds, inputs = [], [], [], []
    for scope, path in paths:
        paragraphs, warnings, binding = read_docx(path, scope)
        refs, prose, section_holds = split_sections(paragraphs)
        all_refs.extend(refs)
        body.extend(prose)
        holds.extend(warnings)
        # A supplementary file can share the main reference list.
        if section_holds and reference_scope == 'document':
            for warning in section_holds:
                warning['location'] = str(path)
            holds.extend(section_holds)
        inputs.append(binding)
    if not all_refs:
        holds.append(issue('NO_REFERENCE_SECTION', '', detail='No recognized references in supplied documents.'))
    numbered = [bool(NUMBER.match(r['text'])) for r in all_refs]
    if style == 'auto':
        if numbered and all(numbered):
            style = 'numbered'
        elif any(numbered):
            holds.append(issue('MIXED_REFERENCE_STYLES', ''))
            style = 'author-year'
        else:
            style = 'author-year'
    references, bad_ref_groups = [], set()
    def group(row):
        return row['location'].split(':word/', 1)[0] if reference_scope == 'document' else 'combined'
    for row in all_refs:
        text = row['text']
        number = NUMBER.match(text)
        key = None
        if style == 'numbered' and number:
            key = str(int(number.group(1) or number.group(2)))
        elif style == 'author-year' and not number:
            year = YEAR_RE.search(text)
            name = author_key(text[:year.start()]) if year else None
            if name:
                key = (name, year.group(1))
        if key is None:
            bad_ref_groups.add(group(row))
            holds.append(issue('UNSUPPORTED_REFERENCE', row['location'], text, 'One surname-first or corporate reference per paragraph required.'))
            continue
        references.append(dict(row, key=key, cited=False, possible=False))
    index = {}
    for ref in references:
        index.setdefault((group(ref), ref['key']), []).append(ref)
    for key, values in index.items():
        if len(values) > 1:
            holds.append(issue('AMBIGUOUS_REFERENCE_KEY', values[0]['location'], str(key[1]), 'Multiple records share this key.'))
            for ref in values:
                ref['possible'] = True
    known = {r['key'][0] for r in references if isinstance(r['key'], tuple)}
    missing, defined, called, caption_holds = [], {}, {}, set()
    uncertain_citation_groups = set()
    for row in body:
        text, location = row['text'], row['location']
        found, warnings = citations(text, style, known)
        for code, token, detail in warnings:
            holds.append(issue(code, location, token, detail))
            uncertain_citation_groups.add(group(row))
        for key, token in found:
            choices = index.get((group(row), key), [])
            if len(choices) == 1:
                choices[0]['cited'] = True
            elif not choices:
                complete = group(row) not in bad_ref_groups and any(group(r) == group(row) for r in references)
                missing.append(dict(issue('MISSING_REFERENCE' if complete else 'UNRESOLVED_CITATION', location, token), key=key, confirmed=complete))
        unsupported_label = re.search(r'\b(Figs?\.?|Figures?|Tables?)\s+(?:\d+(?:\.\d+)+|[IVXLC]+\b)', text, re.I)
        if unsupported_label:
            holds.append(issue('UNSUPPORTED_CAPTION_NUMBER', location, unsupported_label.group(0)))
            caption_holds.add('table' if unsupported_label.group(1).lower().startswith('table') else 'figure')
            continue
        caption = CAPTION.match(text)
        if caption:
            kind = 'table' if caption.group(1).lower().startswith('table') else 'figure'
            key = (kind, number_list(caption.group(2))[0])
            defined.setdefault(key, []).append(location)
            text = text[caption.end():]  # other caption callouts are real cross-references
        elif row['style'].casefold() == 'caption' or re.match(r'^\s*(?:Figure|Fig\.?|Table)\s+S?\d+', text, re.I):
            holds.append(issue('AMBIGUOUS_CAPTION_OR_CALLOUT', location, text, 'Definitions require singular Figure/Fig./Table N. or N: syntax.'))
            caption_holds.add('table' if re.match(r'^\s*Table', text, re.I) else 'figure')
        for match in CALLOUT.finditer(text):
            kind = 'table' if match.group(1).lower().startswith('table') else 'figure'
            try:
                numbers = number_list(match.group(2))
            except ValueError as exc:
                holds.append(issue('UNSUPPORTED_CALLOUT', location, match.group(0), str(exc)))
                caption_holds.add(kind)
                continue
            if re.match(r'[A-Za-z]|\s*[–-]\s*[A-Za-z]', text[match.end():]):
                holds.append(issue('UNSUPPORTED_PANEL_CALLOUT', location, match.group(0), 'Panel letters require manual review.'))
                caption_holds.add(kind)
                continue
            for number in numbers:
                called.setdefault((kind, number), []).append(location)
    for key, locations in defined.items():
        if len(locations) > 1:
            holds.append(issue('DUPLICATE_CAPTION', locations[0], str(key)))
    global_uncertain = any(h['code'] in {'UNSUPPORTED_SUPERSCRIPT', 'UNSUPPORTED_ALTCHUNK', 'TRACKED_CHANGES_PRESENT', 'CACHED_FIELD_TEXT', 'UNSUPPORTED_AUTONUMBER'} for h in holds)
    unused = [dict(issue('UNCITED_REFERENCE', r['location'], r['text']), confirmed=not (r['possible'] or global_uncertain or group(r) in uncertain_citation_groups)) for r in references if not r['cited']]
    # A parser uncertainty cannot prove the absence of a caption or a callout.
    undefined = [dict(issue('UNDEFINED_CALLOUT', locations[0], f'{kind} {number}'), confirmed=not global_uncertain and kind not in caption_holds) for (kind, number), locations in called.items() if (kind, number) not in defined]
    uncalled = [dict(issue('UNCALLED_CAPTION', locations[0], f'{kind} {number}'), confirmed=not global_uncertain and kind not in caption_holds) for (kind, number), locations in defined.items() if (kind, number) not in called]
    if global_uncertain:
        for finding in missing:
            finding['confirmed'] = False
            finding['code'] = 'UNRESOLVED_CITATION'
    return dict(schema_version='paper_reference_audit_v1', status='INCOMPLETE' if holds else 'PARSED_SUPPORTED_SYNTAX', style=style, reference_scope=reference_scope, network='OFF', inputs=inputs, references_parsed=len(references), missing_references=missing, uncited_references=unused, undefined_callouts=undefined, uncalled_captions=uncalled, parsing_holds=holds)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('docx', type=Path, nargs='+', help='main DOCX followed by supplementary DOCX files')
    parser.add_argument('--style', choices=('auto', 'author-year', 'numbered'), default='auto')
    parser.add_argument('--reference-scope', choices=('combined', 'document'), default='combined')
    parser.add_argument('--strict', action='store_true', help='exit 1 for confirmed findings, 2 for parsing holds')
    # No Crossref flag or network implementation: entirely offline by contract.
    args = parser.parse_args(argv)
    try:
        if any(path.suffix.casefold() != '.docx' for path in args.docx):
            raise ValueError('all inputs must be .docx')
        report = audit([('main' if i == 0 else 'supplementary', path) for i, path in enumerate(args.docx)], args.style, args.reference_scope)
    except (OSError, ValueError, zipfile.BadZipFile, ET.ParseError, RuntimeError) as exc:
        sys.stderr.write(f'paper reference audit refused: {exc}\n')
        return 2
    sys.stdout.write(json.dumps(report, indent=2, ensure_ascii=False) + '\n')
    if args.strict:
        if report['parsing_holds']:
            return 2
        return int(any(row['confirmed'] for key in ('missing_references', 'uncited_references', 'undefined_callouts', 'uncalled_captions') for row in report[key]))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
