"""Synthetic tabular fixtures; no sequence analysis or figures."""
import csv
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import pytest
TARGET=Path(__file__).resolve().parents[1]/'tools/ks_burden_table.py'
spec=importlib.util.spec_from_file_location('ks_under_test',TARGET)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)


def package(root,strain='SYN-001'):
    p=root/strain;p.mkdir()
    files=[p/f'{strain}_1_intake.json',p/f'{strain}_2_inventory.csv',p/f'{strain}_3_antismash_modules.csv',p/f'{strain}_4B_pks_ks_fragment_scan.csv']
    for f,text in zip(files,[json.dumps({'strain_id':strain}),'BGC_ID,Boundary\nSOFTWARE_ONLY,Interior\n','row_id,domain\nM1,PKS_KS\n','clade_id,n_ks\nC1,2\n']):
        f.write_text(text)
    return p,files


def alias(source,dest,kind):
    if kind=='direct':return source
    if kind=='symlink':dest.symlink_to(source)
    else:os.link(source,dest)
    return dest


@pytest.mark.parametrize('index',range(4))
@pytest.mark.parametrize('kind',['direct','symlink','hardlink'])
@pytest.mark.parametrize('which',['output','receipt'])
def test_bound_input_alias_refuses_preserves_all_bytes(tmp_path,index,kind,which):
    p,files=package(tmp_path);before={f:f.read_bytes() for f in files}
    target=alias(files[index],tmp_path/'alias',kind)
    other=tmp_path/'new_parent/other'
    output,receipt=(target,other) if which=='output' else (other,target)
    with pytest.raises(mod.KSBurdenHold) as raised:
        mod.build([p],output,receipt)
    assert raised.value.code=='KS_OUTPUT_ALIAS_HOLD'
    assert {f:f.read_bytes() for f in files}==before
    assert not other.parent.exists()


@pytest.mark.parametrize('kind',['direct','symlink','hardlink','absent'])
def test_output_receipt_alias_refuses_without_truncation(tmp_path,kind):
    p,files=package(tmp_path)
    output=tmp_path/'shared'
    if kind!='absent':output.write_text('retained destination')
    receipt=output if kind=='absent' else alias(output,tmp_path/'receipt_alias',kind)
    with pytest.raises(mod.KSBurdenHold) as raised:
        mod.build([p],output,receipt)
    assert raised.value.code=='KS_OUTPUT_ALIAS_HOLD'
    if kind=='absent':assert not output.exists()
    else:assert output.read_text()=='retained destination'


def test_all_packages_protected(tmp_path):
    p,files=package(tmp_path);q,second=package(tmp_path,'SYN-002')
    before=second[2].read_bytes()
    with pytest.raises(mod.KSBurdenHold,match='KS_OUTPUT_ALIAS_HOLD'):
        mod.build([p,q],second[2],tmp_path/'receipt')
    assert second[2].read_bytes()==before


def test_distinct_outputs_preserve_counts_and_source_hashes(tmp_path):
    p,files=package(tmp_path);before={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in files}
    out=tmp_path/'out/counts.tsv';receipt=tmp_path/'out/receipt.json'
    result=mod.build([p],out,receipt)
    assert result['status']=='PASS'
    with out.open() as handle:row=next(csv.DictReader(handle,delimiter='\t'))
    assert row['total_pks_ks_burden']=='3'
    assert {r['logical_locator']:r['sha256'] for r in result['packages'][0]['sources']}==before
    assert {f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in files}==before
    assert result['output']['sha256']==hashlib.sha256(out.read_bytes()).hexdigest()


def test_symlink_parent_alias_preserves_input(tmp_path):
    p,files=package(tmp_path);before=files[1].read_bytes()
    parent=tmp_path/'package_alias';parent.symlink_to(p,target_is_directory=True)
    with pytest.raises(mod.KSBurdenHold,match='KS_OUTPUT_ALIAS_HOLD'):
        mod.build([p],parent/files[1].name,tmp_path/'receipt')
    assert files[1].read_bytes()==before
