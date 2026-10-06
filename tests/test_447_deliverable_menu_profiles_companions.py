"""Registry/menu controls using synthetic paths and mocked local dependency checks."""
import argparse
import copy
import json
import re
from pathlib import Path
import pytest
from mamey import deliverables_registry as D
from mamey.cli import build_parser, main

ROOT = Path(__file__).resolve().parents[1]

def item(key):
    return D._find_item(D.load_registry(), key)


def test_existing_modeb_identity_and_old_name_alias_are_preserved(capsys):
    for token in ['M01', '#5', 'Mode B 48-Section Deep Dive', 'mode b 48-section deep dive']:
        assert item(token)['id'] == 'M01'
    assert main(['deliverables','explain','Mode B 48-Section Deep Dive','--json']) == 0
    assert json.loads(capsys.readouterr().out)['label'] == '#5'
    assert item('M01')['name'] == 'Mode B 48-Section / Current50 v2 Deep Dive'


def test_profile_routes_and_expanded_work_order_are_explicit():
    m = item('M01')
    text = D.render_menu()
    assert 'full48 is the default' in m['summary']
    assert 'current50_v2 is an explicit opt-in' in m['summary']
    assert 'scaffold, not a finished authored card' in m['summary']
    assert '--contract current50_v2 --require-expanded-locus' in m['summary']
    assert 'Core and selected expanded-CDS counts remain separate' in m['summary']
    assert 'emit-modeb-template --package <package> --bgc <BGC> --contract current50_v2' in m['summary']
    p = build_parser()
    emitted = p.parse_args(['emit-modeb-template','--package','p','--bgc','BGC007','--contract','current50_v2'])
    assert emitted.contract == 'current50_v2'
    legacy = p.parse_args(['verify-modeb','card.md'])
    assert legacy.contract == 'full48' and not legacy.require_expanded_locus
    expanded = p.parse_args(['verify-modeb','card.md','--contract','current50_v2','--require-expanded-locus'])
    assert expanded.contract == 'current50_v2' and expanded.require_expanded_locus
    for name in ['MODEB_PROFILE_MATRIX.md','MODEB_CURRENT50_V2_CONTRACT.md','MODEB_EXPANDED_LOCUS.md']:
        assert name in text and (ROOT/'docs'/name).is_file()
    assert 'scaffolds, not finished authored cards' in D.render_legacy_pointer()


@pytest.mark.parametrize('args,command',[
    (['gecco-crosscheck','--package','p','--zip','source.zip'],'gecco-crosscheck'),
    (['export-metabolomics','--package','p','--source-zip','source.zip'],'export-metabolomics'),
    (['two-proof-rescue','--package','p','--policy','nonks_position_v1','--scorecard','bound.tsv'],'two-proof-rescue'),
])
def test_companion_entries_route_to_real_cli(args,command):
    parsed=build_parser().parse_args(args)
    assert parsed.command == command
    record=next(x for x in D.load_registry()['deliverables'] if command in x['commands'])
    assert record['id'] in ['E06','E07','E08']
    assert callable(parsed.func)
    assert 'post_seal/'+command in record['summary']
    assert (ROOT/'docs/COMPANION_CLASS_EVIDENCE.md').is_file()


def package(tmp_path):
    p=tmp_path/'package';p.mkdir();(p/'manifest.json').write_text('{}')
    return str(p)


def test_gecco_missing_dependencies_are_not_advertised_available(tmp_path,monkeypatch):
    monkeypatch.setattr(D.shutil,'which',lambda name:None)
    monkeypatch.setattr(D.importlib.util,'find_spec',lambda name:None)
    result=D.availability_for(item('E06'),package=package(tmp_path))
    assert result.state == 'INPUT_OR_LOCAL_DEPENDENCY_REQUIRED'
    assert set(result.missing)=={'gecco_local','biopython'}
    assert any('source_archive_binding' in n for n in result.notes)
    assert any('gecco_version_0_11_and_tables' in n for n in result.notes)


def test_gecco_local_presence_does_not_certify_version_or_binding(tmp_path,monkeypatch):
    monkeypatch.setattr(D.shutil,'which',lambda name:'/synthetic/gecco' if name=='gecco' else None)
    monkeypatch.setattr(D.importlib.util,'find_spec',lambda name:object())
    result=D.availability_for(item('E06'),package=package(tmp_path))
    assert result.state == 'DECLARED_INPUT_REVIEW_REQUIRED'
    assert not result.missing
    assert len(result.notes)==2
    assert 'does not install GECCO' in item('E06')['summary']


def test_metabolomics_missing_parser_and_unbound_source_are_truthful(tmp_path,monkeypatch):
    monkeypatch.setattr(D.importlib.util,'find_spec',lambda name:None)
    result=D.availability_for(item('E07'),package=package(tmp_path))
    assert result.missing == ('biopython',)
    assert any('source_archive_binding' in n for n in result.notes)
    monkeypatch.setattr(D.importlib.util,'find_spec',lambda name:object())
    ready=D.availability_for(item('E07'),package=str(tmp_path/'package'))
    assert ready.state == 'DECLARED_INPUT_REVIEW_REQUIRED'
    assert 'Unsupported class mappings remain unmapped' in item('E07')['summary']
    assert 'does not analyze MS data' in item('E07')['summary']


def test_nonks_route_preserves_default_and_explicit_vetoes(tmp_path):
    parsed=build_parser().parse_args(['two-proof-rescue','--package','p'])
    assert parsed.policy == 'ks_clade_v2'
    text=item('E08')['summary']
    for needed in ['nonks_position_v1','CONSISTENT','APART_CLOSE','CONFLICT','typed uncertainty','supporting evidence only']:
        assert needed in text
    state=D.availability_for(item('E08'),package=package(tmp_path))
    assert state.state == 'JUDGMENT_REQUIRED'
    assert any('admitted_pair_evidence' in n for n in state.notes)


@pytest.mark.parametrize('aliases',[None,'old name',[''] ,[42]])
def test_alias_schema_rejects_malformed_values(aliases):
    registry=copy.deepcopy(D.load_registry());D._find_item(registry,'M01')['aliases']=aliases
    assert any('aliases must be' in x for x in D.validate_registry(registry))


def test_schema_rejects_cross_item_alias_ambiguity():
    registry=copy.deepcopy(D.load_registry());D._find_item(registry,'E06')['aliases']=['#5']
    assert any('ambiguous lookup token #5' in x for x in D.validate_registry(registry))


def test_generated_menus_have_no_drift_and_local_doc_links_resolve():
    assert D.validate_registry(D.load_registry()) == []
    assert D.CANONICAL_MENU_PATH.read_text() == D.render_menu()
    assert D.LEGACY_MENU_PATH.read_text() == D.render_legacy_pointer()
    for dest in re.findall(r'\]\(([^)]+)\)',D.render_menu()):
        if not dest.startswith(('http:', 'https:')):
            assert (ROOT/'docs'/dest.split('#')[0]).is_file(),dest


def test_all_legacy_ids_labels_and_outputs_remain_compatible():
    expected={**{f'C{i:02}':f'#{i}' for i in range(1,5)},
              **{f'M{i:02}':f'#{i+4}' for i in range(1,5)},
              **{f'E{i:02}':f'E{i}' for i in range(1,6)},
              **{f'S{i:02}':f'S{i}' for i in range(1,6)},
              **{f'G{i:02}':f'G{i}' for i in range(1,6)}}
    for key,label in expected.items():
        assert item(key)['label']==label
        assert item(label)['id']==key
    assert {'modeb_48_card','source_loss_audit','future_map_payload'} <= set(item('M01')['outputs'])


def test_unknown_resource_is_review_required_not_ready():
    record=copy.deepcopy(item('E07'));record['requirements']=['fixture_unknown_resource']
    state=D.availability_for(record)
    assert state.state=='DECLARED_INPUT_REVIEW_REQUIRED'
    assert state.notes==('not inferred automatically: fixture_unknown_resource',)
