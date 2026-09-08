"""Producer-supported missing source digests remain null, never fabricated."""
import json

import pytest

from mamey.cli import _input_zip_sha256
from mamey.manifest_schema import check_package_contract
from tests.test_manifest_contract_checker_v97407 import _package


@pytest.mark.parametrize('digest', [None, 'a' * 64])
def test_contract_accepts_producer_digest_states(tmp_path, digest):
    package = _package(tmp_path)
    if digest is None:
        digest = _input_zip_sha256(tmp_path / 'absent-source.zip')
        assert digest is None
    path = package / 'manifest.json'
    manifest = json.loads(path.read_text())
    manifest['input_zip_sha256'] = digest
    path.write_text(json.dumps(manifest))
    result = check_package_contract(package)
    assert result['status'] == 'PASS', result['errors']


def test_contract_still_rejects_numeric_digest(tmp_path):
    package = _package(tmp_path)
    path = package / 'manifest.json'
    manifest = json.loads(path.read_text())
    manifest['input_zip_sha256'] = 17
    path.write_text(json.dumps(manifest))
    result = check_package_contract(package)
    assert any(error['code'] == 'TYPE_MISMATCH' and
               error['path'] == 'manifest.json.input_zip_sha256'
               for error in result['errors'])
