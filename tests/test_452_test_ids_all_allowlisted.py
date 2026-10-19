"""Lexical identifier diagnostics, not universal publication admission.

Names and strain-to-class associations alone are permitted under the current
policy. Genuine meanings, declared-fixture truth and actual integrity checks remain.
"""
import re
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from _identifier_role_policy import (ID, PLACEHOLDERS, normalise as _normalise,
                                     audit_test_identifiers, digest, read_regular)
ROOT=Path(__file__).resolve().parents[1]
POLICY=Path(__file__).with_name('reviewed_public_reference_sites.json')


def _allowlist():
    return {l.strip() for l in read_regular(ROOT/'tools/test_synthetic_ids.txt').decode().splitlines()
            if l.strip() and not l.lstrip().startswith('#')}


def _unreviewed_test_ids(root,allowed,policy_path):
    # Compatibility arguments cannot create an override or a new permission.
    actual={l.strip() for l in read_regular(root/'tools/test_synthetic_ids.txt').decode().splitlines()
            if l.strip() and not l.lstrip().startswith('#')}
    if set(allowed)!=actual or Path(policy_path).absolute()!=Path(root).absolute()/'tests/reviewed_public_reference_sites.json':
        return {'SOURCE_POLICY_OVERRIDE_REFUSED':['tests/']}
    record=audit_test_identifiers(root,root,digest(read_regular(policy_path)))
    if record['state']=='PASS_SOURCE_ROLE_SCOPE':return {}
    return {'SOURCE_ROLE_HOLD':record.get('findings') or record.get('issues') or ['audit unavailable']}




def test_scan_matches_the_cut_audit_shapes():
    assert ID.findall("f'AS-92{i}'")==['AS-92']
    assert ID.findall("f'AS-{970 + i}'")==[]
    assert ID.findall("AS971 as-972 AJS-001")==['AS971','as-972','AJS-001']
    assert _normalise('as971')=='AS-971'
