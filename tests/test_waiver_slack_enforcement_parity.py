import json
import pytest
from tools.repo_health import _ratchet_ceiling, check_waiver_slack


@pytest.mark.parametrize('drift', [-1, 1])
def test_inactive_waiver_does_not_claim_to_absorb_regression(tmp_path, drift):
    now = _ratchet_ceiling('print_calls')
    (tmp_path / 'STRICT_HEALTH_WAIVER.json').write_text(json.dumps({
        'schema_version': 'sapote.strict_health_waiver/1',
        'waivers': [{'metric': 'print_calls', 'observed': now + 100,
                    'ceiling_at_signing': now + drift, 'owner': 'fixture', 'reason': 'fixture'}],
    }))
    result = check_waiver_slack(tmp_path)
    assert 'inactive' in result.detail.lower()
    assert not any('would waive' in hit for hit in result.hits)
