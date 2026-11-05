#!/usr/bin/env python3
"""Read-only metadata and byte-binding check; never runs a biological analysis."""
import argparse
import csv
import gzip
import hashlib
import json
import re
import sys
import zipfile
import zlib
from pathlib import Path

HEX = re.compile(r'^[0-9a-f]{64}$')
KINDS = {'marker', 'genome'}
ROLES = {'query', 'ingroup', 'outgroup'}
COMPARTMENTS = {'nuclear', 'plastid', 'mitochondrial', 'bacterial', 'mixed', 'unknown'}
FILE_SCOPES = {'single_record', 'multi_record', 'archive', 'unknown'}
SEQUENCE_EXTENTS = {'single_marker', 'chromosome', 'single_contig', 'whole_assembly', 'unknown'}
MAX_ZIP_MEMBER_BYTES = 64 * 1024 * 1024
MAX_GZIP_FASTA_BYTES = 64 * 1024 * 1024
MAX_FASTA_HEADER_BYTES = 64 * 1024


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


class FastaHeaderCounter:
    """Count an exact FASTA header token with bounded buffers."""
    def __init__(self, locator):
        if not isinstance(locator, str) or not locator or locator != locator.strip() or any(ch.isspace() for ch in locator):
            raise ValueError('FASTA record locator must be an exact single header token')
        self.locator = locator
        self.count = 0
        self.at_start = True
        self.in_header = False
        self.header = bytearray()

    def _finish_header(self):
        words = bytes(self.header).strip().split(None, 1)
        if not words:
            raise ValueError('FASTA contains a blank header')
        try:
            token = words[0].decode('utf-8')
        except UnicodeError as exc:
            raise ValueError('FASTA header ID is not UTF-8') from exc
        if token == self.locator:
            self.count += 1

    def feed(self, chunk):
        segments = chunk.split(b'\n')
        for n, segment in enumerate(segments):
            if n == len(segments) - 1 and not segment:
                continue
            ended = n < len(segments) - 1
            if self.at_start:
                self.in_header = segment.startswith(b'>')
                if self.in_header:
                    self.header.clear()
                    segment = segment[1:]
            if self.in_header:
                if len(self.header) + len(segment) > MAX_FASTA_HEADER_BYTES:
                    raise ValueError('FASTA header exceeds 64 KiB read limit')
                self.header.extend(segment)
            if ended:
                if self.in_header:
                    self._finish_header()
                self.at_start, self.in_header = True, False
            else:
                self.at_start = False

    def finish(self):
        if self.in_header:
            self._finish_header()
            self.in_header = False
        return self.count


def fasta_digest_and_count(path, locator):
    """Hash the stream and count header IDs without buffering sequence lines."""
    digest_value = hashlib.sha256()
    counter = FastaHeaderCounter(locator)
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest_value.update(chunk)
            counter.feed(chunk)
    return digest_value.hexdigest(), counter.finish()


def verify_gzip_fasta(path, expected_file_hash, locator):
    """Count a FASTA token in a bounded gzip stream without extraction."""
    counter = FastaHeaderCounter(locator)
    def hash_open(handle):
        handle.seek(0)
        digest_value = hashlib.sha256()
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest_value.update(chunk)
        return digest_value.hexdigest()
    with path.open('rb') as handle:
        if hash_open(handle) != expected_file_hash:
            raise ValueError('gzip SHA-256 mismatch before stream read')
        handle.seek(0)
        count = 0
        with gzip.GzipFile(fileobj=handle, mode='rb') as source:
            while True:
                chunk = source.read(min(1024 * 1024, MAX_GZIP_FASTA_BYTES + 1 - count))
                if not chunk:
                    break
                count += len(chunk)
                if count > MAX_GZIP_FASTA_BYTES:
                    raise ValueError('gzip FASTA exceeds 64 MiB decompressed read limit')
                counter.feed(chunk)
        if hash_open(handle) != expected_file_hash:
            raise ValueError('gzip file changed during stream read')
    return count, counter.finish()


def verify_zip_member(path, expected_archive_hash, locator, expected_member_hash, fasta_locator=None):
    """Hash one unique, bounded ZIP member without extracting it.

    Hash the same open archive before and after the member read; this detects
    ordinary concurrent modifications but cannot provide filesystem locking.
    """
    if not isinstance(locator, str) or not locator or locator != locator.strip():
        raise ValueError('ZIP member locator must be a nonempty exact path')
    if not isinstance(expected_member_hash, str) or not HEX.fullmatch(expected_member_hash):
        raise ValueError('ZIP member requires lowercase member_sha256')
    counter = FastaHeaderCounter(fasta_locator) if fasta_locator is not None else None
    def hash_open(handle):
        handle.seek(0)
        h = hashlib.sha256()
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
        return h.hexdigest()
    with path.open('rb') as handle:
        if hash_open(handle) != expected_archive_hash:
            raise ValueError('ZIP archive SHA-256 mismatch before member read')
        handle.seek(0)
        with zipfile.ZipFile(handle) as archive:
            entries = [entry for entry in archive.infolist() if entry.filename == locator]
            if len(entries) != 1:
                raise ValueError(f'ZIP member path occurs {len(entries)} times; expected exactly one')
            entry = entries[0]
            if entry.is_dir() or entry.flag_bits & 1:
                raise ValueError('ZIP member must be an unencrypted non-directory member')
            if entry.file_size > MAX_ZIP_MEMBER_BYTES:
                raise ValueError('ZIP member exceeds 64 MiB read limit')
            member_hash = hashlib.sha256()
            count = 0
            with archive.open(entry) as source:
                while True:
                    chunk = source.read(min(1024 * 1024, MAX_ZIP_MEMBER_BYTES + 1 - count))
                    if not chunk:
                        break
                    count += len(chunk)
                    if count > MAX_ZIP_MEMBER_BYTES:
                        raise ValueError('ZIP member exceeds 64 MiB read limit')
                    member_hash.update(chunk)
                    if counter is not None:
                        counter.feed(chunk)
            if count != entry.file_size:
                raise ValueError('ZIP member size mismatch')
        if hash_open(handle) != expected_archive_hash:
            raise ValueError('ZIP archive changed during member check')
    if member_hash.hexdigest() != expected_member_hash:
        raise ValueError('ZIP member SHA-256 mismatch')
    return (count, counter.finish()) if counter is not None else count


def accession_key(value):
    """Normalize case only for recognized versioned NCBI accession shapes."""
    value = value.strip()
    if re.fullmatch(r'(?:GC[AF]|NG)_\d+\.\d+', value, re.IGNORECASE):
        return value.upper()
    return value


def accession_stem(value):
    """Only compare clearly versioned assembly accessions; never equate versions."""
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r'(GC[AF]_\d+)\.\d+', value.strip(), re.IGNORECASE)
    return match.group(1).upper() if match else None


def comparable_name(value):
    """Conservative textual normalization, not taxonomic synonym resolution."""
    if not isinstance(value, str):
        return None
    normalized = re.sub(r'\s+', ' ', value.replace('[', '').replace(']', '').strip()).casefold()
    return normalized or None


def unique_object(pairs):
    """Refuse ambiguous JSON keys at every object nesting level."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f'duplicate JSON key: {key}')
        result[key] = value
    return result


def admit_file(path, allowed_roots):
    """Resolve paths before reading; callers must supply genuinely authorized roots."""
    candidate = Path(path)
    if not candidate.is_absolute():
        raise ValueError('absolute file path required')
    resolved = candidate.resolve(strict=True)
    if not any(resolved.is_relative_to(root) for root in allowed_roots):
        raise ValueError('resolved file is outside permitted roots')
    if not resolved.is_file():
        raise ValueError('input is not a regular file')
    return resolved


def check(manifest_path, allowed_roots):
    errors, holds, observations = [], [], []
    def error(message): errors.append(message)
    try:
        if not isinstance(allowed_roots, (list, tuple)) or not allowed_roots:
            raise ValueError('at least one permitted root is required')
        roots = []
        for value in allowed_roots:
            root = Path(value)
            if not root.is_absolute(): raise ValueError('permitted roots must be absolute')
            resolved = root.resolve(strict=True)
            if not resolved.is_dir(): raise ValueError('permitted root must be a directory')
            roots.append(resolved)
        raw = admit_file(manifest_path, roots).read_bytes()
        m = json.loads(raw, object_pairs_hook=unique_object)
        if not isinstance(m, dict): raise ValueError('root must be an object')
    except (OSError, UnicodeError, ValueError) as exc:
        return {'status': 'ERROR', 'errors': [f'manifest unreadable: {exc}'], 'holds': [], 'observations': []}
    manifest_hash = hashlib.sha256(raw).hexdigest()
    if m.get('schema') != 'cross-group-phylo-intake-v1': error('unsupported or missing schema')
    if m.get('group') not in ('fungi', 'algae', 'cyanobacteria'): error('group must be fungi, algae or cyanobacteria')
    for key in ('question', 'lineage', 'tree_scope', 'method_description'):
        if not isinstance(m.get(key), str) or not m[key].strip(): error(f'{key} is required')
    kind = m.get('data_kind')
    if not isinstance(kind, str) or kind not in KINDS: error('data_kind must be marker or genome')
    if kind == 'marker' and (not isinstance(m.get('marker'), str) or not m['marker'].strip()): error('marker is required for marker data')
    refs = m.get('records')
    if not isinstance(refs, list) or not refs:
        error('records must be a nonempty array')
        refs = []
    seen, accessions, roles, accession_roles = set(), set(), set(), {}
    declared_compartments = set()
    verified_sources = []
    verified_zip_members = []
    for i, rec in enumerate(refs, 1):
        label = f'record {i}'
        if not isinstance(rec, dict): error(f'{label}: must be an object'); continue
        rid = rec.get('id')
        if not isinstance(rid, str) or not rid.strip(): error(f'{label}: id required')
        elif rid.strip() in seen: error(f'{label}: duplicate id {rid.strip()}')
        else: seen.add(rid.strip())
        role = rec.get('role')
        if not isinstance(role, str) or role not in ROLES:
            error(f'{label}: invalid role')
            role = None
        else: roles.add(role)
        for field in ('taxon_label', 'source'):
            if not isinstance(rec.get(field), str) or not rec[field].strip(): error(f'{label}: {field} required')
        if rec.get('kind') != kind: error(f'{label}: kind does not match data_kind')
        compartment = rec.get('compartment')
        if compartment is None or compartment == 'unknown':
            holds.append(f'{label}: biological compartment is not established')
        elif not isinstance(compartment, str) or compartment not in COMPARTMENTS:
            error(f'{label}: invalid compartment declaration')
        elif compartment == 'mixed':
            holds.append(f'{label}: mixed compartments declared; source separation requires review')
        else:
            declared_compartments.add(compartment)
        extent = rec.get('sequence_extent')
        if extent is None or extent == 'unknown':
            holds.append(f'{label}: biological sequence extent is unknown; chromosome versus assembly scope requires review')
        elif not isinstance(extent, str) or extent not in SEQUENCE_EXTENTS:
            error(f'{label}: invalid sequence_extent declaration')
        else:
            observations.append(f'{label}: declared sequence extent {extent}; not verified from source bytes')
            if extent in ('chromosome', 'single_contig'):
                holds.append(f'{label}: {extent} declared; do not assume a complete multi-replicon assembly')
            if kind == 'genome' and extent == 'single_marker':
                holds.append(f'{label}: single marker declared for genome comparison; source and method scope require review')
            if kind == 'marker' and extent != 'single_marker':
                holds.append(f'{label}: marker comparison with non-marker sequence extent; extraction and provenance require review')
        scope = rec.get('file_scope')
        if scope is None or scope == 'unknown':
            holds.append(f'{label}: file scope is unknown; record-level binding is unverified')
        elif not isinstance(scope, str) or scope not in FILE_SCOPES:
            error(f'{label}: invalid file_scope declaration')
        elif scope in ('multi_record', 'archive'):
            locator = rec.get('record_locator')
            if not isinstance(locator, str) or not locator.strip():
                error(f'{label}: record_locator required for {scope} source')
            else:
                holds.append(f'{label}: {scope} locator supplied; file hash does not verify the member or record identity')
        if rec.get('source_format') == 'fasta_gzip' and scope != 'multi_record':
            error(f'{label}: fasta_gzip requires multi_record file scope')
        if rec.get('member_record_locator') is not None and not (scope == 'archive' and rec.get('source_format') == 'zip'):
            error(f'{label}: member_record_locator requires ZIP archive scope')
        acc = rec.get('accession')
        if isinstance(acc, str) and acc.strip():
            acc = accession_key(acc)
            accessions.add(acc)
            accession_roles.setdefault(acc, set()).add(role)
            if kind == 'genome' and acc.upper().startswith('NG_'): error(f'{label}: marker accession cannot be declared as a genome assembly')
            if kind == 'marker' and acc.upper().startswith(('GCA_', 'GCF_')): error(f'{label}: assembly accession cannot be declared as a marker accession')
        elif role != 'query': error(f'{label}: reference accession required')
        path, expected = rec.get('path'), rec.get('sha256')
        if not isinstance(path, str) or not Path(path).is_absolute(): error(f'{label}: absolute path required'); continue
        if not isinstance(expected, str) or not HEX.fullmatch(expected): error(f'{label}: lowercase SHA-256 required'); continue
        try:
            admitted = admit_file(path, roots)
            locator = rec.get('record_locator')
            scan = scope == 'multi_record' and rec.get('source_format') == 'fasta' and isinstance(locator, str) and bool(locator.strip())
            if scan:
                if locator != locator.strip() or any(ch.isspace() for ch in locator):
                    raise ValueError('FASTA record_locator must be an exact single header token')
                actual, count = fasta_digest_and_count(admitted, locator)
            else:
                actual = digest(admitted)
                count = None
            if actual != expected: error(f'{label}: SHA-256 mismatch')
            else:
                observations.append(f'{label}: bytes match declared SHA-256')
                if scope == 'multi_record' and rec.get('source_format') == 'fasta_gzip':
                    decoded_size, gzip_count = verify_gzip_fasta(admitted, expected, locator)
                    if gzip_count != 1:
                        error(f'{label}: gzip FASTA locator occurs {gzip_count} times; expected exactly one')
                    else:
                        observations.append(f'{label}: declared gzip FASTA header token occurs exactly once in verified compressed bytes ({decoded_size} decompressed bytes); biological identity unverified')
                if scope == 'archive' and rec.get('source_format') == 'zip':
                    member_locator = rec.get('member_record_locator')
                    if member_locator is not None and rec.get('member_format') != 'fasta':
                        raise ValueError('member_record_locator requires member_format fasta')
                    checked = verify_zip_member(admitted, expected, locator, rec.get('member_sha256'), member_locator)
                    size, member_count = checked if member_locator is not None else (checked, None)
                    observations.append(f'{label}: exact ZIP member bytes match declared SHA-256 ({size} bytes); biological identity unverified')
                    if member_count is not None:
                        if member_count != 1:
                            error(f'{label}: ZIP FASTA record locator occurs {member_count} times; expected exactly one')
                        else:
                            observations.append(f'{label}: declared ZIP FASTA header token occurs exactly once in verified member bytes; biological identity unverified')
                    verified_zip_members.append((i, role, rec['member_sha256']))
                verified_sources.append((i, role, actual, scope, locator))
                if count is not None:
                    if count != 1: error(f'{label}: FASTA locator occurs {count} times; expected exactly one')
                    else: observations.append(f'{label}: declared FASTA header token occurs exactly once in the hashed file; biological identity unverified')
        except (OSError, ValueError, RuntimeError, EOFError, zipfile.BadZipFile, zlib.error, NotImplementedError) as exc: error(f'{label}: cannot read input: {exc}')
    # Identical source bytes can conceal conflicting role assignments even when
    # accessions differ. Do not equate whole containers with their members.
    for n, (i, role, content_hash, scope, locator) in enumerate(verified_sources):
        for j, other_role, other_hash, other_scope, other_locator in verified_sources[n + 1:]:
            if content_hash != other_hash or 'outgroup' not in (role, other_role):
                continue
            if not ({role, other_role} & {'query', 'ingroup'}):
                continue
            if scope == other_scope == 'multi_record' and locator != other_locator:
                continue
            holds.append(f'records {i} and {j}: identical source bytes span outgroup and query/ingroup roles; check record identity and declarations')
    # A member can have identical bytes in different containers, even where
    # archive hashes and member paths differ. Only use successfully verified
    # member hashes; this is a review hold, not an identity conclusion.
    for n, (i, role, member_hash) in enumerate(verified_zip_members):
        for j, other_role, other_hash in verified_zip_members[n + 1:]:
            if member_hash == other_hash and 'outgroup' in (role, other_role) and ({role, other_role} & {'query', 'ingroup'}):
                holds.append(f'records {i} and {j}: identical verified ZIP member bytes span outgroup and query/ingroup roles; check record identity and declarations')
    if len(declared_compartments) > 1:
        holds.append('Records declare differing biological compartments; comparability and analytical separation require review.')
    if m.get('group') == 'cyanobacteria' and declared_compartments.intersection({'nuclear', 'plastid', 'mitochondrial'}):
        holds.append('Eukaryotic compartments declared for a cyanobacterial roster; source roles and identity require review.')
    if m.get('group') in ('algae', 'fungi') and 'bacterial' in declared_compartments:
        holds.append('Bacterial compartment declared in a eukaryotic roster; source roles and identity require review.')
    for accession, assigned in accession_roles.items():
        if 'outgroup' in assigned and len(assigned) > 1: error(f'accession assigned to conflicting outgroup and ingroup/query roles: {accession}')
    for role in ROLES:
        if role not in roles: error(f'missing {role} record')
    registry = m.get('fungal_registry')
    if m.get('group') == 'fungi':
        if not isinstance(registry, dict): error('fungal_registry path and sha256 required')
        else:
            path, expected = registry.get('path'), registry.get('sha256')
            if not isinstance(path, str) or not Path(path).is_absolute() or not isinstance(expected, str) or not HEX.fullmatch(expected):
                error('fungal_registry requires absolute path and lowercase SHA-256')
            else:
                try:
                    data = admit_file(path, roots).read_bytes()
                    if hashlib.sha256(data).hexdigest() != expected: error('fungal_registry SHA-256 mismatch')
                    else:
                        reader = csv.DictReader((line for line in data.decode('utf-8').splitlines() if line.strip() and not line.startswith('#')), delimiter='\t')
                        required = {'tree_scope', 'ingroup_taxon', 'marker_accession', 'status'}
                        columns = reader.fieldnames or []
                        rows = list(reader)
                        if len(columns) != len(set(columns)):
                            error('fungal_registry has duplicate columns')
                        elif not rows or not required.issubset(columns):
                            error('fungal_registry has missing columns or no rows')
                        else:
                            for row in rows:
                                if None in row or any(row.get(k) is None or not row[k].strip() for k in required):
                                    error('fungal_registry has malformed or incomplete row')
                                    continue
                                if row['status'] not in ('BANNED', 'LOCKED', 'CONFIRM'):
                                    error('fungal_registry contains unknown status')
                                    continue
                                registry_acc = accession_key(row['marker_accession'])
                                if registry_acc in accessions:
                                    if row['status'] == 'BANNED': error(f"registry BANNED accession present: {registry_acc}")
                                    else: observations.append(f"registry {row['status']} accession present: {registry_acc}; scope and suitability not verified")
                                if row['status'] == 'BANNED':
                                    banned_stem = accession_stem(registry_acc)
                                    banned_name = comparable_name(row.get('outgroup_species_strain'))
                                    if not banned_name:
                                        holds.append('BANNED registry row lacks a name; textual-name comparison unavailable')
                                    for number, rec in enumerate(refs, 1):
                                        if not isinstance(rec, dict):
                                            continue
                                        acc = rec.get('accession')
                                        if banned_stem and isinstance(acc, str) and accession_key(acc) != registry_acc and accession_stem(acc) == banned_stem:
                                            holds.append(f'record {number}: possible BANNED accession version match to {registry_acc}; versions are not equated')
                                        if banned_name and comparable_name(rec.get('taxon_label')) == banned_name:
                                            holds.append(f'record {number}: possible BANNED textual-name match; verify exact organism and accession')
                            if 'selection' in registry:
                                selection = registry['selection']
                                fields = ('tree_scope', 'ingroup_taxon', 'accession')
                                if not isinstance(selection, dict) or any(
                                        not isinstance(selection.get(k), str) or not selection[k] or selection[k] != selection[k].strip()
                                        for k in fields):
                                    error('fungal_registry selection requires exact nonempty tree_scope, ingroup_taxon and accession')
                                else:
                                    selected_acc = accession_key(selection['accession'])
                                    matches = [row for row in rows
                                               if row.get('tree_scope') == selection['tree_scope']
                                               and row.get('ingroup_taxon') == selection['ingroup_taxon']
                                               and isinstance(row.get('marker_accession'), str)
                                               and accession_key(row['marker_accession']) == selected_acc]
                                    if len(matches) != 1:
                                        error(f'fungal_registry selection matches {len(matches)} rows; expected exactly one')
                                    else:
                                        selected = matches[0]
                                        if selected.get('status') == 'BANNED':
                                            error('fungal_registry selected row is BANNED')
                                        outgroup_accs = {accession_key(rec['accession']) for rec in refs
                                                         if isinstance(rec, dict) and rec.get('role') == 'outgroup'
                                                         and isinstance(rec.get('accession'), str) and rec['accession'].strip()}
                                        if selected_acc not in outgroup_accs:
                                            error('fungal_registry selected accession is not a declared outgroup')
                                        else:
                                            observations.append(f"fungal_registry selected row bound to declared outgroup: {selected_acc} ({selected.get('status')})")
                                        if outgroup_accs - {selected_acc}:
                                            holds.append('Additional outgroup accessions are not bound by the selected registry row; review each separately.')
                                        holds.append('Selected registry row, tree scope, data kind, accession identity and biological suitability require independent review.')
                            holds.append('Review registry scope, exclusions, row selection and marker/genome suitability; matching accessions do not establish suitability.')
                except (OSError, UnicodeError, ValueError, csv.Error) as exc: error(f'fungal_registry unreadable: {exc}')
    elif m.get('group') == 'algae':
        holds.append('Algal lineage-specific marker, references and outgroup require source-backed human review; no algal registry is assumed.')
    elif m.get('group') == 'cyanobacteria':
        holds.append('Cyanobacteria are bacteria: review lineage-specific marker, references and outgroup; bacterial presets are not automatically suitable.')
    holds.extend(['Scientific suitability, sequence identity, alignment and tree quality were not checked.',
                  'Resource preflight, authorization and external-tool readiness were not checked; this result does not authorize computation.'])
    return {'status': 'ERROR' if errors else 'HOLD', 'manifest_sha256': manifest_hash, 'errors': errors, 'holds': holds, 'observations': observations}


def estimate_io(manifest_path, allowed_roots):
    """Stat declared inputs only; do not hash, parse data files or authorize a run."""
    try:
        if not isinstance(allowed_roots, (list, tuple)) or not allowed_roots:
            raise ValueError('at least one permitted root is required')
        roots = []
        for item in allowed_roots:
            root = Path(item)
            if not root.is_absolute():
                raise ValueError('permitted roots must be absolute')
            root = root.resolve(strict=True)
            if not root.is_dir():
                raise ValueError('permitted root must be a directory')
            roots.append(root)
        raw = admit_file(manifest_path, roots).read_bytes()
        manifest = json.loads(raw, object_pairs_hook=unique_object)
        if not isinstance(manifest, dict) or manifest.get('schema') != 'cross-group-phylo-intake-v1':
            raise ValueError('unsupported or missing schema')
        records = manifest.get('records')
        if not isinstance(records, list) or not records:
            raise ValueError('records must be a nonempty array')
        rows = []
        total = 0
        for number, rec in enumerate(records, 1):
            if not isinstance(rec, dict):
                raise ValueError(f'record {number}: object required')
            source = admit_file(rec.get('path'), roots)
            size = source.stat().st_size
            is_zip_member = rec.get('file_scope') == 'archive' and rec.get('source_format') == 'zip'
            is_gzip_fasta = rec.get('file_scope') == 'multi_record' and rec.get('source_format') == 'fasta_gzip'
            passes = 3 if is_zip_member or is_gzip_fasta else 1
            total += passes * size
            rows.append({'record': number, 'resolved_path': str(source), 'stat_bytes': size,
                         'planned_full_file_scans': passes,
                         'planned_full_scan_bytes': passes * size,
                         'additional_member_decompression': is_zip_member,
                         'additional_gzip_decompression': is_gzip_fasta})
        registry_bytes = 0
        if manifest.get('group') == 'fungi':
            registry = manifest.get('fungal_registry')
            if not isinstance(registry, dict):
                raise ValueError('fungal_registry path required for estimate')
            registry_bytes = admit_file(registry.get('path'), roots).stat().st_size
            total += registry_bytes
        return {'status': 'ESTIMATE_ONLY', 'manifest_sha256': hashlib.sha256(raw).hexdigest(),
                'records': rows, 'fungal_registry_stat_bytes': registry_bytes,
                'planned_full_scan_bytes': total,
                'scope': 'Stat-based planned scans per record, assuming valid inputs. ZIP central-directory reads, ZIP member reads and gzip decompression are additional; data may change and failures may stop early. No data files were opened, hashed or validated. Not a resource ceiling, runtime forecast, authorization or scientific preflight.'}
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        return {'status': 'ERROR', 'error': str(exc)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', help='absolute path to JSON manifest; input data are only read and hashed')
    parser.add_argument('--allow-root', action='append', required=True, help='absolute authorized read root; repeat as needed')
    parser.add_argument('--estimate-only', action='store_true', help='stat declared paths and estimate planned full scans without opening data')
    args = parser.parse_args()
    result = estimate_io(args.manifest, args.allow_root) if args.estimate_only else check(args.manifest, args.allow_root)
    sys.stdout.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
    return 2 if result['status'] == 'ERROR' else 0

if __name__ == '__main__':
    raise SystemExit(main())
