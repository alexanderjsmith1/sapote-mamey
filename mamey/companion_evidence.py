"""Bounded companion input admission and fresh-directory publication.

Stable inputs and no concurrent writers are required. Publication renames a
complete staged directory; this is not a multi-directory transaction.
"""
from __future__ import annotations
import csv
import hashlib
import io
import json
import os
import re
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from .csv_safety import SafeDictWriter
from .postseal_output import output_directory, package_binding, sha256_file

CAPACITY_CEILING = 'capacity; an expected class to look for, not a predicted compound'

def read_manifest(package):
    data = json.loads((Path(package) / 'manifest.json').read_text())
    if not isinstance(data, dict) or not isinstance(data.get('bgcs'), list):
        raise ValueError('COMPANION_MANIFEST_INVALID')
    safe_name(data.get('strain_id'))
    seen = set()
    for bgc in data['bgcs']:
        if not isinstance(bgc, dict) or any(type(bgc.get(k)) is not int for k in ('start', 'end', 'region_number')) or bgc['start'] < 0 or bgc['start'] >= bgc['end'] or bgc['region_number'] < 1:
            raise ValueError('COMPANION_BGC_RECORD_INVALID')
        key = identity(data['strain_id'], bgc)
        if key in seen or bgc['bgc_id'] in {x[-1] for x in seen}:
            raise ValueError('COMPANION_DUPLICATE_BGC_IDENTITY')
        seen.add(key)
    return data

def safe_name(name):
    if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', name) or name in ('.', '..'):
        raise ValueError('COMPANION_UNSAFE_OUTPUT_NAME')
    return name

def identity(strain, bgc):
    region = bgc.get('antismash_region') or f"region{int(bgc['region_number']):03d}"
    parts = (strain, bgc.get('contig'), region, bgc.get('bgc_id'))
    if any(not isinstance(x, str) or not x.strip() or ' / ' in x for x in parts):
        raise ValueError('COMPANION_INCOMPLETE_LOCUS_IDENTITY')
    return parts

def identity_text(strain, bgc):
    return ' / '.join(identity(strain, bgc))

def contig_key(contig):
    match = re.fullmatch(r'(NODE_\d+_length_\d+)(?:_cov_[^\s]+)?', contig)
    return match.group(1) if match else contig

def unique_contigs(contigs):
    result = {}
    for contig in contigs:
        key = contig_key(contig)
        if key in result and result[key] != contig:
            raise ValueError('COMPANION_AMBIGUOUS_NORMALIZED_CONTIG')
        result[key] = contig
    return result

def archive_member(archive, member):
    matches = [x for x in archive.infolist() if x.filename == member and not x.is_dir()]
    if len(matches) != 1:
        raise ValueError('COMPANION_ARCHIVE_MEMBER_MISSING_OR_DUPLICATE: ' + str(member))
    return archive.read(matches[0])

def table(path, required, delimiter='\t'):
    with Path(path).open(newline='', encoding='utf-8') as handle:
        reader = csv.DictReader(handle, delimiter=delimiter)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames) or not set(required) <= set(reader.fieldnames):
            raise ValueError('COMPANION_TABLE_SCHEMA_INVALID: ' + str(path))
        rows = list(reader)
        if any(None in row or any(v is None for v in row.values()) for row in rows):
            raise ValueError('COMPANION_TABLE_ROW_INVALID')
        return rows

def write_table(path, rows, fields, delimiter='\t'):
    with Path(path).open('w', newline='', encoding='utf-8') as handle:
        writer = SafeDictWriter(handle, fieldnames=fields, delimiter=delimiter)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(row[k], sort_keys=True) if isinstance(row.get(k), (dict, list)) else row.get(k) for k in fields})

def write_json(path, data):
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + '\n')

@contextmanager
def publication(package, command, out=None):
    dest = output_directory(package, command, out)
    if dest.exists() or dest.is_symlink():
        raise ValueError('COMPANION_OUTPUT_EXISTS: choose a fresh --out directory')
    before = package_binding(package)
    dest.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.' + command + '-', dir=dest.parent))
    try:
        yield stage, before
        if package_binding(package) != before:
            raise ValueError('COMPANION_PACKAGE_CHANGED_DURING_RUN')
        if dest.exists() or dest.is_symlink():
            raise ValueError('COMPANION_OUTPUT_CHANGED_DURING_RUN')
        os.rename(stage, dest)
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def validated_region(raw, strain, bgc, member):
    """Verify the supplied region declaration; retain all admitted original bytes."""
    from Bio import SeqIO
    try:
        text = raw.decode('utf-8')
        if not text.lstrip().startswith('LOCUS') or len(re.findall(r'^//\s*$', text, re.M)) != 1:
            raise ValueError('region must contain exactly one terminated GenBank record')
        records = list(SeqIO.parse(io.StringIO(text), 'genbank'))
        if len(records) != 1: raise ValueError('region must contain exactly one record')
        record = records[0]
        if contig_key(record.id) != contig_key(bgc['contig']):
            raise ValueError('region record contig differs from locked locus')
        match = re.fullmatch(r'(.+)\.region(\d+)\.gbk', Path(member).name)
        expected_region = bgc.get('antismash_region') or f"region{bgc['region_number']:03d}"
        if not match or contig_key(match[1]) != contig_key(bgc['contig']) or int(match[2]) != bgc['region_number'] or expected_region != f"region{bgc['region_number']:03d}":
            raise ValueError('region number differs from locked locus')
        if len(record) != bgc['end'] - bgc['start']:
            raise ValueError('region sequence length differs from locked span')
        original = record.annotations.get('structured_comment', {}).get('antiSMASH-Data', {})
        def declared_bound(name):
            value = original.get(name)
            if not isinstance(value, str) or not re.fullmatch(r'[<>]?\d+', value):
                raise ValueError('original coordinate binding is missing or invalid')
            return int(value.lstrip('<>'))
        if (declared_bound('Orig. start'), declared_bound('Orig. end')) != (bgc['start'], bgc['end']):
            raise ValueError('original coordinates differ from locked locus')
        regions = [f for f in record.features if f.type == 'region']
        if len(regions) != 1 or len(regions[0].qualifiers.get('region_number', [])) != 1 or regions[0].qualifiers['region_number'][0] != str(bgc['region_number']):
            raise ValueError('region feature declaration missing, ambiguous or mismatched')
        if int(regions[0].location.start) != 0 or int(regions[0].location.end) != len(record):
            raise ValueError('region feature bounds differ from region sequence')
        cds = [f for f in record.features if f.type == 'CDS']
        if not cds: raise ValueError('region has no CDS declaration')
        seen = set()
        for feature in cds:
            tags = feature.qualifiers.get('locus_tag', [])
            if len(tags) != 1 or not tags[0] or tags[0] in seen:
                raise ValueError('CDS locus declaration missing or repeated')
            seen.add(tags[0])
            if not all(0 <= int(part.start) < int(part.end) <= len(record) for part in feature.location.parts):
                raise ValueError('CDS coordinates outside region')
        return dict(identity=identity_text(strain, bgc), contig=record.id,
                    start_0based=bgc['start'], end_exclusive=bgc['end'], region_number=bgc['region_number'],
                    cds_locus_tags=sorted(seen), state='REGION_DECLARATION_BOUND')
    except (KeyError, TypeError, AttributeError, ValueError, UnicodeError) as exc:
        raise ValueError(f'METABOLOMICS_REGION_DECLARATION_INVALID: {member}: {exc}') from exc
