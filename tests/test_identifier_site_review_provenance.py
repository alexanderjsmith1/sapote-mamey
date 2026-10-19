"""Exact site-review form; metadata syntax never substitutes for root review."""
import copy
import hashlib
import json
import sys
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import identifier_source_roles as roles


def fixture(tmp_path):
    _, public, keys = roles.reference_hashes(ROOT)
    _, allowed = roles.declarations(ROOT, keys)
    value = next(v for v in sorted(allowed) if v.startswith('AS-') and len(v) >= 6)
    raw = ('def test_fixture():\n    subject = ' + repr(value) + '\n').encode()
    start = raw.index(value.encode()); end = start + len(value)
    owner, kind, _ = roles.semantics(raw, start, end)
    record = {'source_sha256': roles.digest(raw), 'start': start, 'end': end,
              'owner': owner, 'purpose': 'invented regression input', 'artifact_export_permission': False}
    payload = (json.dumps(record, indent=2) + '\n').encode()
    (tmp_path / 'actual_invented_review_record.json').write_bytes(payload)
    site = {'start': start, 'end': end, 'token_sha256': roles.digest(raw[start:end]),
            'context_start': 0, 'context_end': len(raw), 'context_sha256': roles.digest(raw),
            'owner': owner, 'lexical_kind': kind, 'role': roles._FIXTURE_ROLE,
            'canonical_declaration_sha256': roles.digest(value.encode()),
            'provenance': {'kind': 'ADOPTED_AUTHORED_FIXTURE_SITE_REVIEW', 'review_record_sha256': roles.digest(payload)}}
    return raw, {'source_sha256': roles.digest(raw), 'sites': [site]}, public, allowed


def test_exact_review_record_and_legacy_patch_forms(tmp_path):
    raw, entry, public, allowed = fixture(tmp_path)
    assert len(roles.bound_sites(raw, entry, public, allowed)) == 1
    assert entry['sites'][0]['provenance']['review_record_sha256'] == hashlib.sha256((tmp_path / 'actual_invented_review_record.json').read_bytes()).hexdigest()
    for basis in (False, True):
        legacy = copy.deepcopy(entry)
        legacy['sites'][0]['provenance'] = {'kind': 'ADOPTED_AUTHORED_FIXTURE_SOURCE', 'reviewed_patch_sha256': '1' * 64}
        if basis: legacy['sites'][0]['provenance']['basis'] = 'Existing descriptive source-patch basis'
        assert len(roles.bound_sites(raw, legacy, public, allowed)) == 1


@pytest.mark.parametrize('bad', [None, True, 'A' * 64, '1' * 63, '', 1])
def test_malformed_review_digest_refuses(tmp_path, bad):
    raw, entry, public, allowed = fixture(tmp_path)
    entry['sites'][0]['provenance']['review_record_sha256'] = bad
    with pytest.raises(ValueError): roles.bound_sites(raw, entry, public, allowed)


@pytest.mark.parametrize('change', ['missing', 'patch_fiction', 'unsupported', 'export', 'legacy_wrong_field'])
def test_unsupported_provenance_form_refuses(tmp_path, change):
    raw, entry, public, allowed = fixture(tmp_path); provenance = entry['sites'][0]['provenance']
    if change == 'missing': provenance.pop('review_record_sha256')
    elif change == 'patch_fiction': provenance['reviewed_patch_sha256'] = '1' * 64
    elif change == 'unsupported': provenance['kind'] = 'ASSERTION_ONLY'
    elif change == 'export': provenance['export_permission'] = True
    else: provenance['kind'] = 'ADOPTED_AUTHORED_FIXTURE_SOURCE'
    with pytest.raises(ValueError): roles.bound_sites(raw, entry, public, allowed)


@pytest.mark.parametrize('field', ['source', 'context', 'owner', 'kind', 'canonical'])
def test_exact_site_constraints_remain_required(tmp_path, field):
    raw, entry, public, allowed = fixture(tmp_path); site = entry['sites'][0]
    if field == 'source': entry['source_sha256'] = '0' * 64
    elif field == 'context': site['context_sha256'] = '0' * 64
    elif field == 'owner': site['owner'] = 'unreviewed_function'
    elif field == 'kind': site['lexical_kind'] = 'comment'
    else: site['canonical_declaration_sha256'] = '0' * 64
    with pytest.raises(ValueError): roles.bound_sites(raw, entry, public, allowed)


@pytest.mark.parametrize('identity', [False, True])
def test_review_form_cannot_promote_public_reference_or_identity(tmp_path, identity):
    raw, entry, public, allowed = fixture(tmp_path)
    catalog = json.loads((ROOT / 'tools/test_public_reference_tokens.json').read_text())
    value = next(x['token'] for x in catalog['tokens'] if roles._PUBLIC_KINDS[x['kind']] == 'public_product_reference')
    raw = (('subject' if identity else 'product') + ' = ' + repr(value) + '\n').encode()
    start = raw.index(value.encode()); end = start + len(value)
    owner, kind, _ = roles.semantics(raw, start, end); site = entry['sites'][0]
    entry['source_sha256'] = roles.digest(raw)
    site.update(start=start, end=end, token_sha256=roles.digest(raw[start:end]), context_end=len(raw),
                context_sha256=roles.digest(raw), owner=owner, lexical_kind=kind, role='public_product_reference')
    with pytest.raises(ValueError): roles.bound_sites(raw, entry, public, allowed)
    site['provenance'] = {'kind': 'ADOPTED_PUBLIC_SOURCE_SITE', 'reviewed_patch_sha256': '1' * 64}
    if identity:
        with pytest.raises(ValueError): roles.bound_sites(raw, entry, public, allowed)
    else:
        assert len(roles.bound_sites(raw, entry, public, allowed)) == 1
