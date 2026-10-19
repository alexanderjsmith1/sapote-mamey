"""New synthetic material stays declared,hash-bound and discoverable on failure."""
import copy
import hashlib
import json
import os
from pathlib import Path
from tools import determinism_fingerprint as owner
ROOT=Path(os.environ.get('LANE08_SOURCE_ROOT',Path(__file__).resolve().parents[1]))
TARGET='tests/fixtures/ripper_semantic/synthetic_single_record.gbk'
def spec():return json.loads((ROOT/'mamey/data/determinism_inventory.json').read_text())

def test_synthetic_material_has_one_bound_local_probe():
    listing=spec();rows=[r for group in ('package_runs','probes') for r in listing[group] if r['input']==TARGET]
    assert len(rows)==1;row=rows[0]
    assert row['kind']=='pytest' and row['expected_exit_code']==0
    assert row['input_sha256']==hashlib.sha256((ROOT/TARGET).read_bytes()).hexdigest()
    assert row['command']==['-B','-m','pytest','tests/test_ripper_local_semantics.py','-q','--no-header','--no-summary','-p','no:cacheprovider']
    assert row['expected_outcome']=='SYNTHETIC_INPUT_SEMANTICS_ONLY_NO_UPSTREAM_EXECUTION'


def test_removed_material_declaration_still_fails_closed():
    listing=spec();listing['probes']=[r for r in listing['probes'] if r['input']!=TARGET]
    result=owner.validate_inventory(listing)
    assert result['complete'] is False and TARGET in result['unlisted']


def test_stale_material_digest_still_fails_closed():
    listing=spec();next(r for r in listing['probes'] if r['input']==TARGET)['input_sha256']='0'*64
    result=owner.validate_inventory(listing)
    assert result['complete'] is False
    assert any(r['input']==TARGET and r['expected']=='0'*64 for r in result['hash_mismatches'])
