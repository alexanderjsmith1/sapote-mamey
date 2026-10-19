"""Synthetic filesystem/dispatch contracts; no package archive or real study input."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest
import mamey.strain_data_home as homes

ROOT = Path(__file__).resolve().parents[1]

def load(relative, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

@pytest.fixture
def estate(tmp_path, monkeypatch):
    root = tmp_path / 'Synthetic Workspace'; root.mkdir()
    official = root / 'Fixture Controls'; official.mkdir()
    (official/'exclusions.json').write_text(json.dumps({'hard_excluded': [], 'raw_assembly_void': [], 'strain_of_record': {}, 'qc_hold_audit_only': [], 'governed': {}}))
    monkeypatch.setenv('SAPOTE_WORKSPACE_ROOT', str(root))
    monkeypatch.setenv('MAMEY_OFFICIAL_DATA', str(official))
    monkeypatch.setenv('SAPOTE_ASSEMBLY_AUTHORITY', str(root/'missing_authority.tsv'))
    monkeypatch.delenv('MAMEY_PACKAGE_HOMES', raising=False)
    homes.clear_strain_data_cache()
    return root

def file(path, text='Products,KCB_top\nother,0\n'):
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(text); return path

def test_declared_pattern_order_and_no_implicit_legacy_probe(estate, monkeypatch):
    monkeypatch.setenv('MAMEY_PACKAGE_HOMES', os.pathsep.join(['Custom Home*', '/invented/not-accessed', 'Custom Home*']))
    assert homes.package_home_patterns() == ('mamey_packages', 'Package Outputs*', 'Custom Home*', '/invented/not-accessed', 'Custom Home*')
    monkeypatch.delenv('MAMEY_PACKAGE_HOMES')
    (estate/'Unrelated Deployment Home').mkdir()
    assert homes.package_home_directories(str(estate)) == ()

def test_existing_homes_case_alias_dedup_and_env_order(estate, monkeypatch):
    builtin = estate/'package outputs Current'; builtin.mkdir()
    (estate/'Package Outputs Archive').mkdir(); (estate/'Package Outputs Excluded').mkdir()
    first=estate/'Custom One'; first.mkdir(); second=estate/'Custom Two'; second.mkdir()
    alias=estate/'Alias Home'; alias.symlink_to(builtin)
    monkeypatch.setenv('MAMEY_PACKAGE_HOMES', os.pathsep.join([str(alias),str(second),str(first)]))
    assert tuple(map(Path,homes.package_home_directories(str(estate)))) == (builtin,second,first)
    assert homes._package_zip_index(str(estate)) == []  # empty directories only, no archive files

def test_version_and_flavor_parsing_keeps_existing_contract():
    name='AS-9904_Mamey_v9.7.452_engine1.9.176_strict_Complete_Package.zip'
    assert homes._package_version_key(name)==(9,7,452)
    assert homes._package_flavor(name)=='strict'
    assert homes._package_flavor('unknown_Complete_Package.zip') is None

def test_explicit_missing_authority_fails_closed_without_archive(estate):
    assert homes._assembly_authority('AS-9904',str(estate))[1]['status']=='AUTHORITY_INVALID'
    assert homes.resolve_antismash_zip('AS-9904',str(estate),'strict') is None

def test_inventory_first_home_custom_order_and_empty_refusal(estate, monkeypatch):
    module=load('deliverable_tools/inventory_audit.py','migration_inventory')
    assert module.main(['--out',str(estate/'No Report')]) == 2
    assert not (estate/'No Report').exists()
    b=file(estate/'Package Outputs Current'/'AS-9904'/'package'/'AS-9904_4_triage_board.csv','Lead_tier_auto,Products\nInventory,other\n')
    custom=file(estate/'Custom Home'/'AS-9904'/'package'/'AS-9904_4_triage_board.csv','Lead_tier_auto,Products\nInventory,other\n')
    monkeypatch.setenv('MAMEY_PACKAGE_HOMES',str(custom.parents[2]))
    pattern,found=module._default_boards_glob(); assert found and str(b) in __import__('glob').glob(pattern)
    b.unlink();pattern,found=module._default_boards_glob();assert found and str(custom) in __import__('glob').glob(pattern)
    out=estate/'Explicit Report'; module.main(['--boards-glob',str(custom),'--out',str(out)])
    assert (out/'INVENTORY_AUDIT.md').is_file()

def test_roster_custom_home_preference_version_and_outside_ancestor(estate, monkeypatch, tmp_path):
    external=tmp_path/'ancestor-v99.0.0'/'Custom Package Home';external.mkdir(parents=True)
    monkeypatch.setenv('MAMEY_PACKAGE_HOMES', str(external))
    module=load('deliverable_tools/roster_v2.py','migration_roster')
    fallback=file(estate/'Other Home'/'v1.0.0'/'AS-9904'/'package'/'AS-9904_2_inventory.csv')
    selected=file(external/'v1.0.0'/'AS-9904'/'package'/'AS-9904_2_inventory.csv')
    os.utime(fallback,(2000000000,2000000000));os.utime(selected,(1000000000,1000000000))
    assert module.resolve_inventory('AS-9904')==str(selected)
    assert module._inventory_freshness_key(str(selected),str(external))==(1,0,0)
    newer=file(estate/'Other Home'/'v2.0.0'/'AS-9904'/'package'/'AS-9904_2_inventory.csv')
    assert module.resolve_inventory('AS-9904')==str(newer)
    newer.unlink();file(external/'old'/'v3.0.0'/'AS-9904'/'package'/'AS-9904_2_inventory.csv')
    assert module.resolve_inventory('AS-9904')==str(selected)

@pytest.mark.parametrize('relative,allowed',[
 ('strain_data/AS-320_NRPS.md',True), ('strain_data/Sea Green.txt',True),
 ('strain_data/private/report.md',False), ('strain_data/OFFICIAL_DATA/report.md',False),
 ('strain_data/cohort/report.md',False), ('strain_data/merged_cohort/report.md',False),
 ('strain_data/roster.csv',False), ('strain_data/roster.tsv',False),
 ('strain_data/STRAIN_GENUS.csv',False), ('strain_data/exclusions.json',False),
 ('strain_data/ASSEMBLY_AUTHORITY.tsv',False), ('strain_data/_PROVENANCE/report.md',False),
 ('strain_data/scratchpad/report.md',False), ('strain_data/claims.py',False),
 ('Other Home/report.md',False), ('my_strain_data/report.md',False),
])
def test_scope_generic_positive_and_payload_controls(estate,relative,allowed):
    module=load('hooks/claim_safety_scope.py','migration_scope')
    target=file(estate/relative)
    assert module.in_scope(str(target),str(estate)) is allowed
    assert module.in_scope(relative,str(estate)) is allowed

def test_scope_traversal_outside_absolute_symlink_and_explicit_home(estate,tmp_path):
    module=load('hooks/claim_safety_scope.py','migration_scope')
    inside=file(estate/'strain_data'/'report.md'); outside=file(tmp_path/'outside.md')
    assert not module.in_scope('strain_data/../strain_data/report.md',str(estate))
    assert not module.in_scope(str(outside),str(estate))
    assert not module.in_scope(r'C:\invented\report.md',str(estate))
    assert not module.in_scope(r'\\invented\report.md',str(estate))
    alias=estate/'strain_data'/'escape.md'; alias.symlink_to(outside)
    assert not module.in_scope(str(alias),str(estate))
    explicit=file(estate/'Explicit Report Home'/'AS-320_NRPS.md')
    assert module.in_scope(str(explicit),str(estate),str(explicit.parent))
    assert module.in_scope('Explicit Report Home/AS-320_NRPS.md',str(estate),'Explicit Report Home')
    assert not module.in_scope(str(inside.with_name('missing.md')),str(estate))

def test_hook_dispatch_handles_space_root_and_remains_advisory(estate):
    (estate/'Tools'/'bin').mkdir(parents=True)
    (estate/'Tools'/'bin'/'python3').symlink_to(sys.executable)
    log=estate/'dispatch.tsv'
    # Record calls only: these stand in for the downstream tools, not their verdicts.
    for name in ('claim_safety_check.py','guardrail_named_compound.py'):
        (estate/'Tools'/name).write_text('import sys\nfrom pathlib import Path\nwith Path('+repr(str(log))+').open("a") as f: f.write(Path(__file__).name+"\\t"+sys.argv[-1]+"\\n")\nraise SystemExit(7)\n')
    selected=file(estate/'Explicit Report Home'/'AS-320_NRPS.md')
    env=dict(os.environ,SAPOTE_WORKSPACE_ROOT=str(estate),SAPOTE_DELIVERABLE_ROOT=str(selected.parent),PYTHONDONTWRITEBYTECODE='1')
    def run(p):return subprocess.run(['/bin/bash',str(ROOT/'hooks/claim_safety_posttool.sh')],input=json.dumps({'tool_input':{'file_path':str(p)}}),env=env,text=True,capture_output=True,timeout=15)
    assert run(selected).returncode==0
    assert len(log.read_text().splitlines())==2
    private=file(selected.parent/'private'/'roster.csv'); assert run(private).returncode==0
    assert len(log.read_text().splitlines())==2

def test_policy_migration_preserves_science_and_new_id():
    from mamey.rules import load_inventory_tier_policy
    policy=load_inventory_tier_policy(ROOT/'mamey/data/rules_registry.json')
    assert policy['id']=='inventory-bottom-tier-v1'
    assert 'historical' in policy['identifier_note']

def test_fair_analysis_explicit_custom_home_and_builtin_first(estate, monkeypatch):
    fixture=load('tests/test_fair_cohort_analysis_no_dated_glob_v97397.py','migration_fair_fixture')
    root,report=fixture._fixture_root(estate)
    fixture._write_inventory(root)
    custom=file(estate/'Custom Inventories'/'AS-9904'/'package'/'AS-9904_2_inventory.csv','BGC_ID,Boundary\nBGC001,Edge\n')
    env=dict(os.environ,SAPOTE_WORKSPACE_ROOT=root,MAMEY_PACKAGE_HOMES=str(custom.parents[2]))
    def run():
        p=subprocess.run([sys.executable,str(ROOT/'deliverable_tools/fair_cohort_analysis.py')],env=env,text=True,capture_output=True,timeout=15)
        assert p.returncode==0,p.stderr
        return Path(report).read_text()
    assert '(1/2)' in run()
    (estate/'Package Outputs'/'AS-9904'/'package'/'AS-9904_2_inventory.csv').unlink()
    assert '(1/1)' in run()


def test_structural_report_home_wins_over_empty_conventional_directory(estate):
    (estate/'strain_data').mkdir()
    selected=estate/'Unrelated Report Home';selected.mkdir()
    (selected/'WHERE_THINGS_LIVE.md').write_text('# invented index\n')
    module=load('hooks/link_check.py','migration_link_check')
    assert module.DELIVERABLE_HUB_ROOT == str(selected)


def test_scope_os_private_prefix_is_outside_workspace_policy(estate):
    module=load('hooks/claim_safety_scope.py','migration_scope')
    workspace=estate/'private'/'Synthetic Workspace';workspace.mkdir(parents=True)
    report=file(workspace/'strain_data'/'report.md')
    assert module.in_scope(str(report),str(workspace))

@pytest.mark.parametrize('spelling', ['relative', 'absolute'])
def test_scope_whole_home_symlink_cannot_implicitly_admit_external_root(estate, tmp_path, spelling):
    module=load('hooks/claim_safety_scope.py','migration_scope')
    external=file(tmp_path/'External Report Home'/'AS-320_NRPS.md')
    (estate/'strain_data').symlink_to(external.parent)
    value='strain_data/AS-320_NRPS.md' if spelling=='relative' else str(external)
    assert not module.in_scope(value,str(estate))


def test_scope_explicit_external_root_allows_selected_home_only(estate,tmp_path):
    module=load('hooks/claim_safety_scope.py','migration_scope')
    external=file(tmp_path/'External Report Home'/'AS-320_NRPS.md')
    (estate/'strain_data').symlink_to(external.parent)
    for selected in (external.parent,estate/'strain_data'):
        assert module.in_scope(str(external),str(estate),str(selected))
        assert module.in_scope('strain_data/AS-320_NRPS.md',str(estate),str(selected))
        private=file(external.parent/'private'/'report.md')
        assert not module.in_scope(str(private),str(estate),str(selected))
        roster=file(external.parent/'roster.tsv')
        assert not module.in_scope(str(roster),str(estate),str(selected))
    outside=file(tmp_path/'Unselected Home'/'report.md')
    assert not module.in_scope(str(outside),str(estate),str(external.parent))
    alias=external.parent/'escape.md';alias.symlink_to(outside)
    assert not module.in_scope(str(alias),str(estate),str(external.parent))


@pytest.mark.parametrize('selected', ['private','OFFICIAL_DATA','cohort','merged_cohort','.git',
                                      'private/Report Home','OFFICIAL_DATA/Report Home'])
def test_scope_explicit_external_private_home_or_ancestor_refuses(estate,tmp_path,selected):
    module=load('hooks/claim_safety_scope.py','migration_scope')
    report=file(tmp_path/'External Selection'/selected/'report.md')
    assert not module.in_scope(str(report),str(estate),str(report.parent))
    alias=tmp_path/'Neutral Alias';alias.symlink_to(report.parent)
    assert not module.in_scope(str(report),str(estate),str(alias))


def test_scope_explicit_workspace_private_ancestor_refuses(estate):
    module=load('hooks/claim_safety_scope.py','migration_scope')
    report=file(estate/'private'/'Report Home'/'report.md')
    assert not module.in_scope(str(report),str(estate),str(report.parent))
