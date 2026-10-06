"""Synthetic source and canonical-context admission controls; no sequence engines."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import zipfile

import pytest

from tests.test_447_modeb_expanded_locus import scope, card
from tests.test_447_modeb_gap_rescue_reader import CORE
from mamey.modeb_locus_scope import build_scope, context_loci, load_inventory
from mamey.modeb_current50_v2 import header_line
from mamey.modeb_gap_rescue import load_gap_rescue


def pinned_package(tmp_path):
    _, rescue, inventory, _ = scope(tmp_path)
    data = json.loads(inventory.read_text())
    package = tmp_path / 'package'; package.mkdir()
    table = package / 'PUBLIC-1_cds_table.csv'
    with table.open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['strain','contig','locus_tag','start','end','strand','length_aa','region','bgc_id'])
        writer.writeheader()
        for gene in data['genes']:
            for identity in gene['identities']:
                strain, contig, region, alias = identity.split(' / ')
                writer.writerow(dict(strain=strain,contig=contig,locus_tag=gene['locus_tag'],start=gene['start_1based'],end=gene['end_1based'],strand=gene['strand'],length_aa=gene['aa_length'],region=region,bgc_id=alias))
    data['package_cds_source'] = dict(path=str(table),sha256=hashlib.sha256(table.read_bytes()).hexdigest())
    inventory.write_text(json.dumps(data))
    return rescue, inventory, data, package


@pytest.mark.parametrize('fault',['membership','geometry','strand','drop'])
def test_rehashed_inventory_cannot_disagree_with_pinned_package(tmp_path, fault):
    rescue, inventory, data, _ = pinned_package(tmp_path)
    assert load_inventory(inventory,'PUBLIC-1')[0]
    if fault == 'membership': data['genes'][0]['identities'] = ['PUBLIC-1 / CONTIG_A_length_1000 / region999 / BGC999']
    elif fault == 'geometry': data['genes'][0]['start_1based'] += 1
    elif fault == 'strand': data['genes'][0]['strand'] = -1
    else: data['genes'].pop(0)
    inventory.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='canonical|geometry|whole-assembly'): load_inventory(inventory,'PUBLIC-1')
    assert build_scope(inventory,load_gap_rescue(rescue,CORE),[dict(locus_tag='a_1')],50)['state']=='HOLD'


def test_context_is_admitted_only_for_full_declared_identity_and_package(tmp_path):
    rescue, inventory, _, package = pinned_package(tmp_path)
    s=build_scope(inventory,load_gap_rescue(rescue,CORE),[dict(locus_tag='a_1')],50)
    md=header_line(*CORE.split(' / '))+'\n# Mode B — PUBLIC-1 / BGC001\n'+card(s)
    assert context_loci(md,package,'BGC001')=={'a_1','b_1','b_2'}
    wrong=md.replace('canonical_identity: '+CORE,'canonical_identity: PUBLIC-1 / OTHER / region001 / BGC001')
    assert context_loci(wrong,package,'BGC001')==set()
    assert context_loci(md+'\n'+header_line(*CORE.split(' / ')),package,'BGC001')==set()
    assert context_loci(md,package.parent/'another','BGC001')==set()


def test_duplicate_zip_member_refused_before_inventory_write(tmp_path):
    tool=Path(__file__).parents[1]/'tools/build_modeb_locus_inventory.py'
    spec=importlib.util.spec_from_file_location('crossreview_inventory_exporter',tool)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    package=tmp_path/'package';package.mkdir()
    (package/'PUBLIC-1_cds_table.csv').write_text('strain,contig,locus_tag,start,end,strand,length_aa,region,bgc_id\n')
    archive=tmp_path/'assembly.zip'
    with zipfile.ZipFile(archive,'w') as z:
        z.writestr('whole.gbk','first synthetic');z.writestr('whole.gbk','second synthetic')
    output=tmp_path/'inventory.json'
    with pytest.raises(ValueError,match='unique regular ZIP member'):
        module.export(archive,'whole.gbk',package,'PUBLIC-1',output)
    assert not output.exists()


@pytest.mark.parametrize('fault',['hash','sequence','length','omit','member','malformed'])
def test_inventory_must_rebuild_from_actual_pinned_assembly(tmp_path,fault):
    rescue, inventory, data, _ = pinned_package(tmp_path)
    if fault=='hash': data['genes'][2]['aa_sha256']='0'*64
    elif fault=='sequence':
        data['genes'][2]['aa_sequence']='RST'; data['genes'][2]['aa_sha256']=hashlib.sha256(b'RST').hexdigest()
    elif fault=='length': data['genes'][2]['contig_length_bp']=1100
    elif fault=='omit': data['genes'].pop(3)
    elif fault=='member': data['assembly_source']['gbk_member']='other.gbk'
    else:
        p=Path(data['assembly_source']['path']);p.write_text('not GenBank')
        data['assembly_source']['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
    inventory.write_text(json.dumps(data))
    assert build_scope(inventory,load_gap_rescue(rescue,CORE),[dict(locus_tag='a_1')],50)['state']=='HOLD'


def test_fenced_scope_rows_do_not_grant_visible_roster(tmp_path):
    from mamey.modeb_locus_scope import findings, marker, render_scope
    rescue, inventory, _, _=pinned_package(tmp_path)
    s=build_scope(inventory,load_gap_rescue(rescue,CORE),[dict(locus_tag='a_1')],50)
    for fence in ('```text','~~~text'):
        md=marker(s)+'\n'+'\n'.join(f'## §{n} Example\n{fence}\n{render_scope(s,n)}\n{fence[:3]}\n' for n in (3,26,50))
        assert any(f['code']=='LOCUS_SCOPE_GENE_DROPPED' for f in findings(md))


@pytest.mark.parametrize('target',['assembly','table'])
def test_export_cannot_overwrite_input_through_hardlink(tmp_path,target):
    import os
    rescue, inventory, data, package=pinned_package(tmp_path)
    spec=importlib.util.spec_from_file_location('hardlink_inventory_exporter',Path(__file__).parents[1]/'tools/build_modeb_locus_inventory.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    victim=Path(data['assembly_source']['path']) if target=='assembly' else package/'PUBLIC-1_cds_table.csv'
    original=victim.read_bytes();out=tmp_path/'aliased.json';os.link(victim,out)
    with pytest.raises(ValueError,match='inode alias'): module.export(data['assembly_source']['path'],None,package,'PUBLIC-1',out)
    assert victim.read_bytes()==out.read_bytes()==original


def test_expanded_options_refuse_legacy_emission_and_allow_explicit_v2(tmp_path,monkeypatch):
    from mamey import modeb_template_emitter as emitter
    from mamey.modeb_current50_v2 import load_contract
    monkeypatch.setattr(emitter,'_bgc_facts',lambda *_:dict(strain_id='PUBLIC-1',contig=CORE.split(' / ')[1],node=CORE.split(' / ')[1],region='region001',bgc_id='BGC001',gene_rows=[]))
    with pytest.raises(ValueError,match='CONTRACT_REQUIRED'):
        emitter.emit_card_template(tmp_path,'BGC001',sources={'rescue_locus_inventory':'missing.json'})
    md=emitter.emit_card_template(tmp_path,'BGC001',contract=load_contract('current50_v2'),sources={'rescue_locus_inventory':'missing.json'})
    assert 'MODEB_EXPANDED_LOCUS_REQUIRED' in md and 'EXPANDED_LOCUS_SOURCE_HOLD' in md


def test_full50_expanded_wrapper_selects_native_contract_without_remapping(tmp_path,monkeypatch):
    import subprocess
    spec=importlib.util.spec_from_file_location('native_full50_wrapper',Path(__file__).parents[1]/'tools/emit_modeb_template_full50.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    seen=[]
    native=header_line(*CORE.split(' / '))+'\n'+''.join(f'## §{n} Native section\nbody-{n}\n' for n in range(1,51))
    def run(argv,**kwargs):
        seen.append(argv);Path(argv[argv.index('--out')+1]).write_text(native)
        return subprocess.CompletedProcess(argv,0,'','')
    monkeypatch.setattr(module.subprocess,'run',run)
    flags=['--rescue-locus-inventory','missing.json']
    text,receipt=module.build(Path(__file__).parents[1],'python',tmp_path,'BGC001',flags)
    assert seen[0][seen[0].index('--contract')+1]=='current50_v2'
    assert text==native and receipt['migration_actions']==[] and receipt['profile']=='CURRENT50_V2_NATIVE'
    assert receipt['contract_sha256']=='8bb29690fbf3bf8cac049561fa800cbc229334a800e113cb797434d20fcfc5ab'
    assert receipt['contract_json'].endswith('modeb_current50_v2_contract.json')
    seen.clear();module.emit_engine_template(tmp_path,'python',tmp_path,'BGC001',[])
    assert '--contract' not in seen[0]


@pytest.mark.parametrize('contract,required,code',[('current50_v2',True,'LOCUS_SCOPE_MISSING'),('current50_v2',False,None),('full48',True,'LOCUS_SCOPE_CONTRACT_REQUIRED')])
def test_actual_verifier_workorder_requirement_survives_removed_metadata(tmp_path,monkeypatch,contract,required,code):
    from types import SimpleNamespace
    from mamey import authored_verify
    from mamey.cli import build_parser
    assert build_parser().parse_args(['verify-modeb','card.md','--require-expanded-locus']).require_expanded_locus is True
    path=tmp_path/'ordinary.md';path.write_text('# Mode B — PUBLIC-1 / BGC001\n')
    receipt=tmp_path/'verify.json'
    monkeypatch.setattr(authored_verify,'_bgc_context_from_package',lambda *_:None)
    # Isolate the source/workorder gate from unrelated unfinished-card depth checks.
    monkeypatch.setattr(authored_verify,'lint_card',lambda *args,**kwargs:[])
    authored_verify.verify_modeb_command(SimpleNamespace(file=str(path),contract=contract,require_expanded_locus=required,report_json=str(receipt),summary_only=True))
    codes={f['code'] for f in json.loads(receipt.read_text())['findings']}
    assert ('LOCUS_SCOPE_MISSING' in codes)==(code=='LOCUS_SCOPE_MISSING')
    assert ('LOCUS_SCOPE_CONTRACT_REQUIRED' in codes)==(code=='LOCUS_SCOPE_CONTRACT_REQUIRED')


@pytest.mark.parametrize('drift',[False,True])
def test_actual_verifier_keeps_raw_scope_metadata_and_selected_matrix_context(tmp_path,monkeypatch,drift):
    from types import SimpleNamespace
    from mamey import authored_verify
    rescue,inventory,_,package=pinned_package(tmp_path)
    s=build_scope(inventory,load_gap_rescue(rescue,CORE),[dict(locus_tag='a_1')],50)
    md=header_line(*CORE.split(' / '))+'\n# Mode B — PUBLIC-1 / BGC001\n'+card(s)
    path=tmp_path/'expanded.md';path.write_text(md)
    if drift: inventory.write_text(inventory.read_text()+'\n')
    ctx=dict(known_loci={'a_1'},known_locus_tags=['a_1'],n_core_genes=1)
    monkeypatch.setattr(authored_verify,'_bgc_context_from_package',lambda *_:ctx)
    seen=[]
    monkeypatch.setattr(authored_verify,'lint_card',lambda md,**kwargs:seen.append((md,kwargs['bgc_context'])) or [])
    receipt=tmp_path/'verify.json'
    authored_verify.verify_modeb_command(SimpleNamespace(file=str(path),contract='current50_v2',package=str(package),bgc='BGC001',require_expanded_locus=True,report_json=str(receipt),summary_only=True))
    result=json.loads(receipt.read_text());codes={f['code'] for f in result['findings']}
    assert seen and 'MODEB_LOCUS_SCOPE_V1' not in seen[0][0]  # active scientific prose view
    if drift:
        assert 'LOCUS_SCOPE_SOURCE_INVALID' in codes and 'modeb_matrix_locus_tags' not in ctx
    else:
        assert not any(code.startswith('LOCUS_SCOPE_') for code in codes)
        assert set(ctx['modeb_matrix_locus_tags'])=={'a_1','b_1','b_2'}
        assert ctx['known_locus_tags']==['a_1'] and ctx['n_core_genes']==1
        assert 'existence only' in result['profile']
