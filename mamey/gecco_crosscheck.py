"""Optional GECCO 0.11 reader cross-check; preserves original package bytes."""
from __future__ import annotations
import csv
import hashlib
import io
import math
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from Bio import SeqIO
from .companion_evidence import (archive_member, contig_key, identity_text,
    publication, read_manifest, table, unique_contigs, write_json, write_table)
from .postseal_output import package_binding, resolve_source_archive, sha256_file

CLAIM = 'GECCO is a second opinion; a call is not cluster proof and a low score is not evidence against a cluster.'

def _p(value):
    if value in ('', None, 'NA', 'nan'):
        return None
    result = float(value)
    if not math.isfinite(result) or not 0 <= result <= 1:
        raise ValueError('GECCO_PROBABILITY_INVALID')
    return result

def _whole_genome(archive, explicit=None):
    members = [x.filename for x in archive.infolist() if not x.is_dir() and x.filename.endswith(('.gbk', '.gb')) and not re.search(r'\.region\d+\.gbk$', x.filename)]
    if explicit is not None:
        if explicit not in members:
            raise ValueError('GECCO_GENOME_MEMBER_INVALID')
        members = [explicit]
    # Whole-genome antiSMASH output should have one annotated aggregate GBK.
    if len(members) != 1:
        raise ValueError('GECCO_GENOME_MEMBER_AMBIGUOUS: select --genome-member')
    raw = archive_member(archive, members[0])
    records = list(SeqIO.parse(io.StringIO(raw.decode()), 'genbank'))
    if not records:
        raise ValueError('GECCO_GENOME_EMPTY')
    if len({r.id for r in records}) != len(records):
        raise ValueError('GECCO_DUPLICATE_GENOME_CONTIG')
    unique_contigs([r.id for r in records])
    genes = {}
    for record in records:
        for feature in record.features:
            if feature.type != 'CDS':
                continue
            tags = feature.qualifiers.get('locus_tag', [])
            if len(tags) != 1 or not tags[0] or tags[0] in genes:
                raise ValueError('GECCO_CDS_LOCUS_TAG_MISSING_OR_DUPLICATE')
            if feature.location is None:
                raise ValueError('GECCO_SOURCE_CDS_COORDINATE_INVALID')
            start, end = int(feature.location.start), int(feature.location.end)
            if not 0 <= start < end <= len(record) or any(not 0 <= int(part.start) < int(part.end) <= len(record) for part in feature.location.parts):
                raise ValueError('GECCO_SOURCE_CDS_COORDINATE_INVALID')
            genes[tags[0]] = (contig_key(record.id), start + 1, end)
    if not genes:
        raise ValueError('GECCO_GENOME_NO_CDS')
    return members[0], raw, records, genes

def _validated_tables(rawdir, records, source_genes):
    genes = table(rawdir / 'genome.genes.tsv', ['sequence_id', 'protein_id', 'start', 'end', 'average_p', 'max_p'])
    clusters = table(rawdir / 'genome.clusters.tsv', ['sequence_id', 'cluster_id', 'start', 'end', 'type', 'max_p'])
    contigs = unique_contigs([r.id for r in records])
    lengths = {contig_key(r.id): len(r) for r in records}
    seen = set()
    for gene in genes:
        pid = gene['protein_id']
        if pid in seen or pid not in source_genes:
            raise ValueError('GECCO_GENE_ID_MISMATCH')
        seen.add(pid)
        actual = (contig_key(gene['sequence_id']), int(gene['start']), int(gene['end']))
        if actual != source_genes[pid]:
            raise ValueError('GECCO_GENE_COORDINATE_MISMATCH')
        gene['gecco_mean_p'] = _p(gene['average_p'])
        gene['gecco_max_p'] = _p(gene['max_p'])
    if seen != set(source_genes):
        raise ValueError('GECCO_GENE_ROSTER_INCOMPLETE')
    seen = set()
    for cluster in clusters:
        cid = cluster['cluster_id']
        key = contig_key(cluster['sequence_id'])
        start, end = int(cluster['start']), int(cluster['end'])
        if not cid or cid in seen or key not in contigs or not 1 <= start <= end <= lengths[key]:
            raise ValueError('GECCO_CLUSTER_LOCATOR_INVALID')
        seen.add(cid)
        cluster['start0'], cluster['end0'] = start - 1, end
        cluster['max_p'] = _p(cluster['max_p'])
    return genes, clusters

def crosscheck(package, source_zip=None, out=None, threshold=0.8, jobs=1, genome_member=None, gap_genes=(), executable='gecco'):
    if not math.isfinite(threshold) or not 0 <= threshold <= 1 or not isinstance(jobs, int) or jobs < 1:
        raise ValueError('GECCO_PARAMETERS_INVALID')
    binary = shutil.which(executable)
    if binary is None:
        raise ValueError('GECCO_NOT_INSTALLED: optional companion; bundle does not install it')
    probe = subprocess.run([binary, '--version'], capture_output=True, text=True, timeout=15, check=True)
    version = (probe.stdout + probe.stderr).strip()
    if not re.search(r'\b0\.11\.\d+\b', version):
        raise ValueError('GECCO_VERSION_UNSUPPORTED: this adapter targets the 0.11 CLI/table contract')
    manifest = read_manifest(package)
    archive_path, archive_receipt = resolve_source_archive(package, source_zip)
    with zipfile.ZipFile(archive_path) as archive:
        member, raw, records, source_genes = _whole_genome(archive, genome_member)
    genome_keys = unique_contigs([r.id for r in records])
    genome_lengths = {contig_key(r.id): len(r) for r in records}
    unique_contigs([b['contig'] for b in manifest['bgcs']])
    for b in manifest['bgcs']:
        if contig_key(b['contig']) not in genome_keys or not 0 <= b['start'] < b['end'] <= genome_lengths.get(contig_key(b['contig']), 0):
            raise ValueError('GECCO_PACKAGE_CONTIG_NOT_IN_GENOME')
    with publication(package, 'gecco-crosscheck', out) as (stage, pkg_binding):
        (stage / 'genome.gbk').write_bytes(raw)
        rawdir = stage / 'raw'
        command = [binary, 'run', '--genome', str(stage / 'genome.gbk'), '-o', str(rawdir), '--cds-feature', 'CDS', '--locus-tag', 'locus_tag', '--threshold', str(threshold), '--jobs', str(jobs), '--force-tsv']
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        (stage / 'gecco.log').write_text(result.stdout + result.stderr)
        genes, clusters = _validated_tables(rawdir, records, source_genes)
        overlaps, support, used = [], {}, set()
        strain = manifest['strain_id']
        for b in manifest['bgcs']:
            found = [c for c in clusters if contig_key(c['sequence_id']) == contig_key(b['contig']) and c['start0'] < b['end'] and c['end0'] > b['start']]
            used.update(c['cluster_id'] for c in found)
            probs = [c['max_p'] for c in found if c['max_p'] is not None]
            row = {'identity': identity_text(strain, b), 'gecco_clusters': [c['cluster_id'] for c in found], 'gecco_types': sorted({c['type'] for c in found}), 'gecco_max_probability': max(probs) if probs else None, 'state': 'OVERLAP_OBSERVED' if found else 'NO_OVERLAP_OBSERVED', 'claim_ceiling': CLAIM}
            overlaps.append(row)
            support[row['identity']] = row
        only = [{'strain': strain, 'contig': genome_keys[contig_key(c['sequence_id'])], 'cluster_id': c['cluster_id'], 'start_0based': c['start0'], 'end_exclusive': c['end0'], 'gecco_type': c['type'], 'max_probability': c['max_p'], 'claim_ceiling': CLAIM} for c in clusters if c['cluster_id'] not in used]
        gene_rows = [{'strain': strain, 'contig': genome_keys[contig_key(g['sequence_id'])], 'locus_tag': g['protein_id'], 'start_1based': g['start'], 'end_inclusive': g['end'], 'gecco_mean_p': g['gecco_mean_p'], 'gecco_max_p': g['gecco_max_p'], 'claim_ceiling': CLAIM} for g in genes]
        write_table(stage / (strain + '_7_gecco_vs_antismash.csv'), overlaps, ['identity', 'gecco_clusters', 'gecco_types', 'gecco_max_probability', 'state', 'claim_ceiling'], ',')
        write_table(stage / (strain + '_7_gecco_only_clusters.csv'), only, ['strain', 'contig', 'cluster_id', 'start_0based', 'end_exclusive', 'gecco_type', 'max_probability', 'claim_ceiling'], ',')
        write_table(stage / (strain + '_7_gecco_gene_probabilities.csv'), gene_rows, ['strain', 'contig', 'locus_tag', 'start_1based', 'end_inclusive', 'gecco_mean_p', 'gecco_max_p', 'claim_ceiling'], ',')
        gene_idx = {g['locus_tag']: g for g in gene_rows}
        joins = []
        names = set()
        for path in gap_genes:
            path = Path(path)
            delimiter = '\t' if path.suffix == '.tsv' else ','
            with path.open(newline='') as handle:
                fields = next(csv.reader(handle, delimiter=delimiter), [])
            keys = [k for k in ('locus_tag', 'query_gene', 'protein_id') if k in fields]
            if not keys or any(k in fields for k in ('gecco_mean_p', 'gecco_join_state', 'gecco_binding_scope')):
                raise ValueError('GECCO_GAP_GENE_SCHEMA_UNSUPPORTED')
            key = keys[0]
            rows = table(path, keys, delimiter)
            name = path.stem + '_gecco' + path.suffix
            if name in names:
                raise ValueError('GECCO_GAP_OUTPUT_NAME_DUPLICATE')
            names.add(name)
            coordinate_pairs = [('start_1based', 'end_inclusive', 1), ('start_0based', 'end_exclusive', 0), ('start', 'end', 1)]
            if any((left in fields) != (right in fields) for left, right, _ in coordinate_pairs):
                raise ValueError('GECCO_GAP_COORDINATE_SCHEMA_INCOMPLETE')
            for row in rows:
                if len({row[k] for k in keys}) != 1 or not row[key].strip():
                    raise ValueError('GECCO_GAP_GENE_ID_AMBIGUOUS')
                for strain_key in ('strain', 'strain_id'):
                    if strain_key in fields and row[strain_key] != strain:
                        raise ValueError('GECCO_GAP_GENE_STRAIN_MISMATCH')
                g = gene_idx.get(row[key])
                supplied_contigs = [row[k] for k in ('contig', 'sequence_id', 'query_contig') if k in fields]
                if supplied_contigs and (any(not value for value in supplied_contigs) or len({contig_key(value) for value in supplied_contigs}) != 1):
                    raise ValueError('GECCO_GAP_GENE_CONTIG_AMBIGUOUS')
                if g and supplied_contigs and contig_key(supplied_contigs[0]) != contig_key(g['contig']):
                    raise ValueError('GECCO_GAP_GENE_CONTIG_MISMATCH')
                checked_coordinates = False
                for left, right, base in coordinate_pairs:
                    if left not in fields: continue
                    try:
                        if not re.fullmatch(r'\d+', row[left]) or not re.fullmatch(r'\d+', row[right]): raise ValueError()
                        start, end = int(row[left]), int(row[right])
                        if not (base <= start <= end) or (base == 0 and start == end): raise ValueError()
                    except (TypeError, ValueError) as exc:
                        raise ValueError('GECCO_GAP_GENE_COORDINATE_INVALID') from exc
                    if g and (start + (1 - base), end) != (int(g['start_1based']), int(g['end_inclusive'])):
                        raise ValueError('GECCO_GAP_GENE_COORDINATE_MISMATCH')
                    checked_coordinates = True
                row['gecco_mean_p'] = g['gecco_mean_p'] if g else None
                row['gecco_join_state'] = 'SOURCE_LOCUS_TAG_MATCH' if g else 'NO_SOURCE_LOCUS_TAG_MATCH'
                row['gecco_binding_scope'] = ('SOURCE_LOCUS_TAG_AND_SUPPLIED_COORDINATES' if checked_coordinates else 'SOURCE_LOCUS_TAG_ONLY') if g else 'UNMATCHED'
            write_table(stage / name, rows, fields + ['gecco_mean_p', 'gecco_join_state', 'gecco_binding_scope'], delimiter)
            joins.append({'path': str(path.resolve()), 'sha256': sha256_file(path), 'output': name})
        if sha256_file(archive_path) != archive_receipt['sha256']:
            raise ValueError('GECCO_ARCHIVE_CHANGED')
        write_json(stage / 'support.json', support)
        outputs = {p.relative_to(stage).as_posix(): sha256_file(p) for p in sorted(stage.rglob('*')) if p.is_file()}
        write_json(stage / 'receipt.json', {'schema': 'sapote.gecco-crosscheck.v1', 'package_binding': pkg_binding, 'source_archive': archive_receipt, 'genome_member': member, 'genome_sha256': hashlib.sha256(raw).hexdigest(), 'version': version, 'threshold': threshold, 'jobs': jobs, 'command': command, 'gap_gene_sources': joins, 'gap_join_policy': 'Exact locus tags; validate every supplied strain/contig and supported coordinate pair; missing coordinates retain explicitly tag-only binding. start/end and start_1based/end_inclusive are 1-based inclusive; start_0based/end_exclusive is zero-based half-open.', 'outputs_sha256': outputs, 'claim_ceiling': CLAIM, 'coordinate_policy': 'GECCO 1-based inclusive converted to antiSMASH zero-based half-open; CDS roster and coordinates verified'})
    return overlaps

def bound_support(package, directory):
    directory = Path(directory)
    receipt = __import__('json').loads((directory / 'receipt.json').read_text())
    if receipt.get('schema') != 'sapote.gecco-crosscheck.v1' or receipt.get('package_binding') != package_binding(package):
        raise ValueError('GECCO_SUPPORT_PACKAGE_BINDING_MISMATCH')
    expected = receipt.get('outputs_sha256', {}).get('support.json')
    if not expected or sha256_file(directory / 'support.json') != expected:
        raise ValueError('GECCO_SUPPORT_DIGEST_MISMATCH')
    return __import__('json').loads((directory / 'support.json').read_text())
