"""Independent named-channel controls; no sequences, homology or native tools."""
import importlib
import io
import json
import zipfile

import pytest

from mamey import antismash_evidence as ae

CONTIG = 'SYNTHETIC_FULL_CONTIG.1'


@pytest.fixture(autouse=True, params=['selected', 'python'])
def backend(request, monkeypatch):
    assert ae._HAVE_IJSON
    if request.param == 'python':
        monkeypatch.setattr(ae, 'ijson', importlib.import_module('ijson.backends.python'))


def channel(score, *, region='1', kind='RegionToRegion_RiQ', reference='reference'):
    return {'by_region': {region: {kind: {'scores_by_region': {reference: score}}}}}


def parse(document):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        archive.writestr('synthetic.json', json.dumps(document))
    stream.seek(0)
    evidence = {'by_region': {}, 'loose_hits': [], 'json_files': ['synthetic.json'],
                'json_mode': 'bounded', 'json_mode_requested': 'bounded'}
    with zipfile.ZipFile(stream) as archive:
        ae._parse_json_bounded(archive, 'synthetic.json', evidence)
    return evidence


def maxima(evidence):
    return {key: max(row['riq_score'] for row in rows if 'riq_score' in row)
            for key, rows in evidence['by_region'].items()}


@pytest.mark.parametrize('module', ['cluster_compare', 'antismash.modules.cluster_compare'])
@pytest.mark.parametrize('late', [False, True])
def test_qualified_and_legacy_channels_bind_complete_record_identity(module, late):
    record = {'modules': {module: channel(0.0)}, 'id': CONTIG} if late else {
        'id': CONTIG, 'modules': {module: channel(0.0)}}
    ev = parse({'records': [record]})
    assert maxima(ev) == {CONTIG + '_c1': 0.0}
    receipt = ev['json_bounded_walks'][0]
    assert receipt['riq_observations_seen'] == receipt['riq_observations_mapped'] == 1
    assert receipt['walk_complete'] and receipt['records_closed'] == 1


@pytest.mark.parametrize('kind', ['ProtoToRegion_RiQ', 'RegionToRegion_RiQ_fake', 'regiontoregion_riq'])
def test_other_score_kinds_do_not_inflate_region_to_region_maximum(kind):
    module = channel(0.2)
    module['by_region']['1'][kind] = {'scores_by_region': {'other_reference': 0.9}}
    ev = parse({'records': [{'id': CONTIG, 'modules': {'cluster_compare': module}}]})
    assert maxima(ev) == {CONTIG + '_c1': 0.2}
    assert ev['json_bounded_walks'][0]['riq_observations_seen'] == 1


@pytest.mark.parametrize('module', ['unrelated', 'fake.antismash.modules.cluster_compare'])
def test_unrelated_module_cannot_supply_named_channel(module):
    ev = parse({'records': [{'id': CONTIG, 'modules': {
        'cluster_compare': channel(0.2), module: channel(0.9)}}]})
    assert maxima(ev) == {CONTIG + '_c1': 0.2}
    assert ev['json_bounded_walks'][0]['riq_observations_seen'] == 1


@pytest.mark.parametrize('shape', ['record_key', 'module_key', 'region_key', 'score_key'])
def test_dotted_keys_cannot_manufacture_structural_channel_roles(shape):
    record = {'id': CONTIG, 'modules': {'cluster_compare': channel(0.2)}}
    if shape == 'record_key':
        record['modules.cluster_compare.by_region.1.RegionToRegion_RiQ.scores_by_region.poison'] = 0.9
    elif shape == 'module_key':
        record['modules']['cluster_compare']['by_region.1.RegionToRegion_RiQ.scores_by_region.poison'] = 0.9
    elif shape == 'region_key':
        record['modules']['cluster_compare']['by_region']['1.RegionToRegion_RiQ.scores_by_region.poison'] = 0.9
    else:
        record['modules']['cluster_compare']['by_region']['1']['RegionToRegion_RiQ']['scores_by_region.poison'] = 0.9
    ev = parse({'records': [record]})
    assert maxima(ev) == {CONTIG + '_c1': 0.2}
    assert ev['json_bounded_walks'][0]['riq_observations_seen'] == 1


def test_named_channel_outside_record_remains_unassigned():
    ev = parse({'records': [{'id': CONTIG, 'modules': {'cluster_compare': channel(0.2)}}],
                'other': {'modules': {'cluster_compare': channel(0.9)}}})
    assert maxima(ev) == {CONTIG + '_c1': 0.2}
    receipt = ev['json_bounded_walks'][0]
    assert receipt['riq_observations_seen'] == 2
    assert receipt['riq_observations_mapped'] == receipt['riq_observations_unassigned'] == 1
    assert ev['loose_hits'][-1]['riq_identity_status'] == 'UNMAPPED_RECORD_OR_REGION'


@pytest.mark.parametrize('region', ['0', '-1', '1x', ''])
def test_invalid_one_based_region_key_does_not_become_physical_identity(region):
    ev = parse({'records': [{'id': CONTIG, 'modules': {'cluster_compare': channel(0.9, region=region)}}]})
    assert maxima(ev) == {}
    assert ev['json_bounded_walks'][0]['riq_observations_seen'] == 0


def test_literal_dots_in_reference_key_remain_valid():
    ev = parse({'records': [{'id': CONTIG, 'modules': {
        'antismash.modules.cluster_compare': channel(1.0, reference='reference.accession.1')}}]})
    assert maxima(ev) == {CONTIG + '_c1': 1.0}
    assert ev['json_bounded_walks'][0]['riq_observations_mapped'] == 1


def test_supported_channels_share_one_record_region_maximum():
    ev = parse({'records': [{'id': CONTIG, 'modules': {
        'cluster_compare': channel(0.2), 'antismash.modules.cluster_compare': channel(0.9)}}]})
    assert maxima(ev) == {CONTIG + '_c1': 0.9}
    receipt = ev['json_bounded_walks'][0]
    assert receipt['riq_groups_kept'] == receipt['riq_mapped_maxima'] == 1
    assert receipt['riq_observations_seen'] == receipt['riq_observations_mapped'] == 2


@pytest.mark.parametrize('module', ['cluster_compare', 'antismash.modules.cluster_compare'])
@pytest.mark.parametrize('late', [False, True])
def test_current_database_container_preserves_full_record_binding(module, late):
    payload = {'db_results': {'source.database.1': channel(0.4)}, 'record_id': CONTIG}
    record = {'modules': {module: payload}, 'id': CONTIG} if late else {
        'id': CONTIG, 'modules': {module: payload}}
    ev = parse({'records': [record]})
    assert maxima(ev) == {CONTIG + '_c1': 0.4}
    assert ev['json_bounded_walks'][0]['riq_observations_mapped'] == 1


@pytest.mark.parametrize('declared', ['OTHER_FULL_CONTIG.1', '', None, {}])
def test_declared_module_record_identity_conflict_cannot_assign_score(declared):
    payload = {'db_results': {'database': channel(0.9)}, 'record_id': declared}
    ev = parse({'records': [{'modules': {'antismash.modules.cluster_compare': payload}, 'id': CONTIG}]})
    assert maxima(ev) == {}
    receipt = ev['json_bounded_walks'][0]
    assert receipt['riq_observations_seen'] == receipt['riq_observations_unassigned'] == 1
    assert receipt['riq_observations_mapped'] == 0
    assert ev['loose_hits'][-1]['riq_identity_status'] == 'UNMAPPED_MODULE_RECORD_ID_CONFLICT'


@pytest.mark.parametrize('late', [False, True])
def test_declared_matching_module_identity_preserves_maximum(late):
    payload = channel(0.2)
    payload['record_id'] = CONTIG
    payload['by_region']['1']['RegionToRegion_RiQ']['scores_by_region']['second'] = 0.8
    record = {'modules': {'cluster_compare': payload}, 'id': CONTIG} if late else {
        'id': CONTIG, 'modules': {'cluster_compare': payload}}
    ev = parse({'records': [record]})
    assert maxima(ev) == {CONTIG + '_c1': 0.8}
    assert ev['json_bounded_walks'][0]['riq_observations_mapped'] == 2


def test_current_database_container_excludes_proto_score():
    region = channel(0.2)
    region['by_region']['1']['ProtoToRegion_RiQ'] = {'scores_by_region': {'other': 0.9}}
    ev = parse({'records': [{'id': CONTIG, 'modules': {'antismash.modules.cluster_compare': {
        'record_id': CONTIG, 'db_results': {'database': region}}}}]})
    assert maxima(ev) == {CONTIG + '_c1': 0.2}
    assert ev['json_bounded_walks'][0]['riq_observations_seen'] == 1


def test_current_multiple_databases_keep_record_region_maximum():
    ev = parse({'records': [{'id': CONTIG, 'modules': {'antismash.modules.cluster_compare': {
        'record_id': CONTIG, 'db_results': {'first': channel(0.3), 'second': channel(0.8)}}}}]})
    assert maxima(ev) == {CONTIG + '_c1': 0.8}
    assert ev['json_bounded_walks'][0]['riq_observations_mapped'] == 2
