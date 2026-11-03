"""Structural cohort admission only; synthetic identities, no scientific inference."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import pytest

TARGET = Path(__file__).resolve().parents[1] / 'mamey/mode_b/gene_first_layers.py'
spec = importlib.util.spec_from_file_location('layer_candidate', TARGET)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
B = {'locus_context_receipt_id': 'synthetic-receipt', 'identity': {'synthetic': 'software-only'}}


def manifest(**updates):
    result = {'logical_locator': 'synthetic/members.json', 'sha256': 'a'*64,
              'members': ['SYN-001', 'SYN-002'], 'denominator': 2,
              'schema_version_policy': 'explicit', 'database_snapshot_policy': 'explicit',
              'missingness_policy': 'explicit'}
    result.update(updates)
    return result


@pytest.mark.parametrize('members', [['SYN-001','SYN-001'], [''], [' '], [None], [True], [1], [{}], [[]], ['SYN-001', None]])
def test_invalid_members_held_without_mutation(members):
    m = manifest(members=members, denominator=len(members))
    before = copy.deepcopy(m)
    result = mod.build_layer_c(B, m)
    assert result['readiness'] == 'C_HELD'
    assert 'LAYER_C_MEMBERSHIP_HOLD' in result['holds']
    assert result['outputs_emitted'] == []
    assert m == before


@pytest.mark.parametrize('denominator', [True, False])
def test_boolean_denominator_is_not_count(denominator):
    result=mod.build_layer_c(B, manifest(members=['SYN-001'], denominator=denominator))
    assert result['readiness']=='C_HELD'
    assert 'LAYER_C_DENOMINATOR_HOLD' in result['holds']


@pytest.mark.parametrize('over', [{}, {'members':['SYN-001'],'denominator':1}, {'members':['custom identifier','custom identifier 2']}])
def test_valid_exact_members_still_ready(over):
    result=mod.build_layer_c(B, manifest(**over))
    assert result['readiness']=='C_READY'
    assert result['holds']==[]
    assert result['cites']=={'locus_context_receipt_id':B['locus_context_receipt_id']}
    assert result['outputs_emitted']==[]
    assert result==mod.build_layer_c(B,manifest(**over))


@pytest.mark.parametrize('over,hold', [({'members':['AS-*'],'denominator':1},'LAYER_C_MEMBERSHIP_HOLD'), ({'denominator':3},'LAYER_C_DENOMINATOR_HOLD'), ({'members':[],'denominator':0},'LAYER_C_MEMBERSHIP_HOLD'), ({'sha256':'missing'},'LAYER_C_MANIFEST_HOLD')])
def test_existing_holds_preserved(over,hold):
    result=mod.build_layer_c(B,manifest(**over))
    assert result['readiness']=='C_HELD'
    assert hold in result['holds']
