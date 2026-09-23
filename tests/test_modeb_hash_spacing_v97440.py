"""Valid provenance hashes are not prose spacing defects; review binding stays enforced."""
from __future__ import annotations
import hashlib
import json
import pytest
from mamey.modeb_publication_gate import _word_number_spacing_findings
from mamey.mode_b_receipt import validate_finished_review_request
from tests.test_modeb_finished_review_request_v97410 import (
    _fixture, _upgrade_to_v10, _rewrite_card_and_rebind_verification, _snapshot,
)
from tests.test_modeb_finished_review_reconciliation_v11_v97410 import _upgrade_to_v11


@pytest.mark.parametrize('digest', ['abc1' + '0' * 60, 'abC1' + 'F' * 60, '1' * 64])
def test_complete_bare_sha256_is_not_prose(digest):
    assert _word_number_spacing_findings(f'| Receipt | {digest} |\n') == []


@pytest.mark.parametrize('token', ['abc1' + '0' * 59, 'abc1' + '0' * 61, 'prefix' + 'abc1' + '0' * 60])
def test_partial_or_embedded_hex_does_not_gain_sha256_exemption(token):
    assert _word_number_spacing_findings(token)


def test_real_spacing_error_beside_digest_still_fires():
    result = _word_number_spacing_findings('engine1.9.169 ' + 'abc1' + '0' * 60)
    assert len(result) == 1
    assert result[0]['found'] == 'engine…'


def _bind_nonce(path, payload, predicate):
    for nonce in range(10000):
        payload['synthetic_hash_fixture_nonce'] = nonce
        raw = (json.dumps(payload, sort_keys=True) + '\n').encode()
        digest = hashlib.sha256(raw).hexdigest()
        if predicate(digest):
            path.write_bytes(raw)
            return digest
    raise AssertionError('deterministic hash fixture search exhausted')


@pytest.mark.parametrize('upgrade', [_upgrade_to_v10, _upgrade_to_v11])
def test_letter_prefixed_bound_figure_receipt_remains_ready_and_read_only(tmp_path, upgrade):
    pkg, root, request_path, request = _fixture(tmp_path)
    upgrade(pkg, root, request_path, request)
    # Keep the map digest digit-prefixed; isolate the spacing trigger in the visual receipt.
    spec = request['locus_map_v8_receipt']
    path = root / spec['locator']
    payload = json.loads(path.read_text())
    old_map = spec['sha256']
    spec['sha256'] = _bind_nonce(path, payload, lambda h: h[0].isdigit())
    _rewrite_card_and_rebind_verification(root, request_path, request, old_map, spec['sha256'])
    visual = request['locus_map_visual_review_receipt']
    path = root / visual['locator']
    payload = json.loads(path.read_text())
    payload['locus_map_v8_receipt_sha256'] = spec['sha256']
    old_visual = visual['sha256']
    visual['sha256'] = _bind_nonce(path, payload, lambda h: h[:3].isalpha() and h[3].isdigit())
    _rewrite_card_and_rebind_verification(root, request_path, request, old_visual, visual['sha256'])
    before = _snapshot(tmp_path)
    result = validate_finished_review_request(pkg, request_path, root)
    assert result['status'] == 'READY_FOR_OWNER_REVIEW', result['findings']
    assert result['mutation_performed'] is False
    assert _snapshot(tmp_path) == before
    # A whitespace-lint exemption must not waive provenance integrity.
    path.write_text(path.read_text() + ' ')
    rejected = validate_finished_review_request(pkg, request_path, root)
    assert rejected['status'] == 'HOLD_FINISHED_REVIEW_REQUEST'
    assert 'REVIEW_MEMBER_SHA256_MISMATCH' in rejected['finding_codes'], rejected['findings']
