"""Read-only product probes using synthetic, lane-contained package fixtures."""
import hashlib
import json
import pytest

from mamey.genome_explore import _conservation_median
from mamey.mode_b.gene_first_explore import resolve_identity, _manifest_hits, _auto_observations
from mamey.mode_b.gene_first_explore import GeneFirstHold
from mamey.scan_channel_alias import load_bound_scan_manifest, ScanChannelBindingError

STRAIN = 'SYNTHETIC-001'
NODE = 'NODE_1_length_1000_cov_1'
REGION = 'region001'
ALIAS = 'BGC001'
IDENTITY = ' / '.join((STRAIN, NODE, REGION, ALIAS))


def _fixture(path, *, embedded=False):
    payload = {'per_gene_best_hit': {ALIAS: [
        {'query_gene': 'CDS_1', 'pct_identity': 25.0},
        {'query_gene': 'CDS_2', 'pct_identity': 75.0},
    ]}}
    name = f'{STRAIN}_4A2_ClusterBlast_gene_map.json'
    target = path / name
    target.write_text(json.dumps(payload))
    manifest = {'strain_id': STRAIN, 'bgcs': [
        {'bgc_id': ALIAS, 'contig': NODE, 'node_id': NODE, 'region_number': 1,
         'antismash_region': REGION}],
        'source_scans': {'clusterblast_genes': payload if embedded else {
            'schema': 'source_scan_channel_alias_v1', 'alias_of': name}}}
    (path / 'manifest.json').write_text(json.dumps(manifest))
    return manifest, target


def test_conservation_reads_identical_fields_from_alias_and_embedded_payload(tmp_path):
    manifest, target = _fixture(tmp_path)
    assert _conservation_median(tmp_path, manifest, ALIAS) == (50.0, 2, 0)
    manifest['source_scans']['clusterblast_genes'] = json.loads(target.read_text())
    assert _conservation_median(tmp_path, manifest, ALIAS) == (50.0, 2, 0)


def test_gene_first_indirect_reader_resolves_query_gene(tmp_path):
    manifest, target = _fixture(tmp_path)
    identity, _, materialized = resolve_identity(
        tmp_path, strain=STRAIN, full_node=NODE, region=REGION, bgc_alias=ALIAS)
    assert identity['exact_identity'] == IDENTITY
    assert materialized['source_scans']['clusterblast_genes'] == json.loads(target.read_text())
    observations = _manifest_hits(materialized, identity, {'CDS_1', 'CDS_2'}, 'a' * 64)
    assert {row['gene'] for row in observations} == {'CDS_1', 'CDS_2'}
    assert {row['channel'] for row in observations} == {'clusterblast'}


def test_bound_indirect_evidence_digest_tracks_payload_bytes(tmp_path):
    _, target = _fixture(tmp_path)
    manifest_path = tmp_path / 'manifest.json'
    manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    before = target.read_bytes()
    target.write_text(json.dumps({'per_gene_best_hit': {ALIAS: [{'query_gene': 'CDS_2', 'pct_identity': 99.0}]}}))
    assert before != target.read_bytes()
    assert hashlib.sha256(manifest_path.read_bytes()).hexdigest() == manifest_sha
    identity, _, materialized = resolve_identity(
        tmp_path, strain=STRAIN, full_node=NODE, region=REGION, bgc_alias=ALIAS)
    gene_table = tmp_path / 'synthetic_gene_table.csv'
    gene_table.write_text('locus_tag\nCDS_2\n')
    observations = _auto_observations(
        [{'locus_tag': 'CDS_2'}], gene_table, identity, materialized, manifest_path)
    assert len(observations) == 1 and observations[0]['gene'] == 'CDS_2'
    assert observations[0]['evidence_state'] == 'BOUND'
    # The declared source must bind the actual file supplying this observation.
    assert observations[0]['source_sha256'] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert observations[0]['source_locator'].startswith('package://' + target.name + '#')


def test_embedded_evidence_stays_bound_to_manifest(tmp_path):
    manifest, _ = _fixture(tmp_path, embedded=True)
    identity, _, materialized = resolve_identity(
        tmp_path, strain=STRAIN, full_node=NODE, region=REGION, bgc_alias=ALIAS)
    table = tmp_path / 'gene_table.csv'
    table.write_text('locus_tag\nCDS_1\nCDS_2\n')
    observations = _auto_observations(
        [{'locus_tag': 'CDS_1'}, {'locus_tag': 'CDS_2'}], table, identity,
        materialized, tmp_path / 'manifest.json')
    digest = hashlib.sha256((tmp_path / 'manifest.json').read_bytes()).hexdigest()
    assert all(row['source_sha256'] == digest for row in observations)
    assert all(row['source_locator'].startswith('package://manifest.json#') for row in observations)


@pytest.mark.parametrize('bad_payload', ['[]', '{broken', 'null',
    '{"schema":"source_scan_channel_alias_v1","alias_of":"next.json"}'])
def test_invalid_payload_refuses_before_identity_is_returned(tmp_path, bad_payload):
    _, target = _fixture(tmp_path)
    target.write_text(bad_payload)
    with pytest.raises(GeneFirstHold, match='MODEB_GENE_FIRST_SOURCE_HOLD'):
        resolve_identity(tmp_path, strain=STRAIN, full_node=NODE, region=REGION, bgc_alias=ALIAS)


@pytest.mark.parametrize('target_name', ['../outside.json', '/outside.json', 'C:\\outside.json', '', 'missing.json'])
def test_unresolvable_alias_cannot_become_bound_evidence(tmp_path, target_name):
    manifest, _ = _fixture(tmp_path)
    manifest['source_scans']['clusterblast_genes']['alias_of'] = target_name
    (tmp_path / 'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ScanChannelBindingError):
        load_bound_scan_manifest(tmp_path / 'manifest.json')


def test_symlink_alias_refused(tmp_path):
    manifest, target = _fixture(tmp_path)
    link = tmp_path / 'link.json'
    link.symlink_to(target)
    manifest['source_scans']['clusterblast_genes']['alias_of'] = link.name
    (tmp_path / 'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ScanChannelBindingError, match='symlinks'):
        load_bound_scan_manifest(tmp_path / 'manifest.json')


def test_payload_change_between_identity_and_observation_refuses(tmp_path):
    _, target = _fixture(tmp_path)
    identity, _, materialized = resolve_identity(
        tmp_path, strain=STRAIN, full_node=NODE, region=REGION, bgc_alias=ALIAS)
    target.write_text('{}')
    table = tmp_path / 'gene_table.csv'
    table.write_text('locus_tag\nCDS_1\n')
    with pytest.raises(GeneFirstHold, match='source changed'):
        _auto_observations([{'locus_tag':'CDS_1'}], table, identity, materialized, tmp_path / 'manifest.json')


@pytest.mark.parametrize('channel', ['clusterblast_genes', 'mibig_per_gene', 'rggmci'])
def test_receipt_preserves_actual_observation_source(channel, tmp_path):
    from tests.test_modeb_gene_first_explore_v9_7_395 import _package, _run, TOKEN
    package = _package(tmp_path)
    path = package / 'manifest.json'
    manifest = json.loads(path.read_text())
    target = package / (channel + '.json')
    target.write_text(json.dumps(manifest['source_scans'][channel]))
    manifest['source_scans'][channel] = {'schema':'source_scan_channel_alias_v1', 'alias_of':target.name}
    path.write_text(json.dumps(manifest))
    out = tmp_path / 'out'
    out.mkdir()
    result = _run(package, out)
    persisted = json.loads((out / TOKEN / (TOKEN + '__exploration_receipt.json')).read_text())
    assert persisted['evidence_observations'] == result['evidence_observations']
    expected_channel = {'clusterblast_genes':'clusterblast','mibig_per_gene':'mibig','rggmci':'rggmci'}[channel]
    rows = [row for row in persisted['evidence_observations'] if row['channel'] == expected_channel]
    assert rows and all(row['evidence_state'] == 'BOUND' for row in rows)
    assert all(row['source_sha256'] == hashlib.sha256(target.read_bytes()).hexdigest() for row in rows)
    assert all(row['source_locator'].startswith('package://' + target.name + '#') for row in rows)
