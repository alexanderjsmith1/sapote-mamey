"""Conditional scan evidence is not an unconditional package requirement."""
import json

from mamey.manifest_schema import check_package_contract
from tests.test_manifest_contract_checker_v97407 import _example, _package, SCHEMA
from tests.test_manifest_root_contract_v97407 import _run


def test_contract_accepts_absent_conditional_blda_tier(tmp_path):
    # Actual producer for SYNTHETIC-001 / NODE_1_length_1000_cov_1 /
    # region001 / BGC001 has no bldA scan evidence.
    produced = _run().to_dict()['bgcs'][0]
    assert 'blda_tier' not in produced
    package = _package(tmp_path)
    schema = json.loads(SCHEMA.read_text())
    item = _example(schema['$defs']['manifest']['properties']['bgcs']['items'])
    for key in ('bgc_id', 'node_id', 'contig', 'antismash_region', 'region_number'):
        item[key] = produced[key]
    item.pop('blda_tier', None)
    path = package / 'manifest.json'
    manifest = json.loads(path.read_text())
    manifest['strain_id'] = 'SYNTHETIC-001'
    manifest['bgcs'] = [item]
    path.write_text(json.dumps(manifest))
    result = check_package_contract(package)
    assert result['status'] == 'PASS', result['errors']
