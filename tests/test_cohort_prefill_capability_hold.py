"""Minimal capability hold; fabricated facts and existing core interfaces only."""
import csv
import hashlib
import json
from pathlib import Path
import pytest
from mamey import cli, modeb_round, modeb_template_emitter as emitter

HOLD='COHORT_PREFILL_SOURCE_BINDING_UNAVAILABLE'
LOC='SYNTHETIC_NODE_A.1 region001'
WRONG='FABRICATED_WRONG_RAW_SOURCE_FACT'


def fixture_case(root):
    pkg=root/'SYNTHETIC'/'package';pkg.mkdir(parents=True)
    manifest={'strain_id':'SYNTHETIC','taxonomy':'not verified','source':'not supplied',
        'input_zip_sha256':'b'*64,'bgcs':[{'bgc_id':'BGC001','contig':'SYNTHETIC_NODE_A.1',
        'antismash_region':'region001','region_number':1,'start':1,'end':12,'products':['synthetic']}]}
    (pkg/'manifest.json').write_text(json.dumps(manifest))
    with (pkg/'SYNTHETIC_4_triage_board.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['BGC_ID','Strain','Contig','antiSMASH_Region','Products','AB_auto','AF_auto','Corrected_rank'])
        w.writeheader();w.writerow({'BGC_ID':'BGC001','Strain':'SYNTHETIC','Contig':'SYNTHETIC_NODE_A.1','antiSMASH_Region':'region001','Products':'synthetic','AB_auto':'0','AF_auto':'0','Corrected_rank':'1'})
    pc=root/'cohort';pc.mkdir()
    rows=[{'Strain':'SYNTHETIC','BGC_ID':'BGC001','Assembly_Locator':LOC,'Input_Zip_SHA256':'a'*64,
           'Source_Contig_SHA256':'c'*64,'architecture_archetype':WRONG,'archetype_note':'fabricated software control','domain_architecture_string':'FABRICATED_ONLY'}]
    with (pc/'COHORT_domain_architecture_by_bgc.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    return pkg,pc


def core_hashes(pkg,pc):
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [pkg/'manifest.json',pkg/'SYNTHETIC_4_triage_board.csv',pc/'COHORT_domain_architecture_by_bgc.csv']}


def test_direct_prefill_refuses_before_reading_imported_table(tmp_path,monkeypatch):
    pkg,pc=fixture_case(tmp_path)
    original=Path.open
    def guarded(path,*args,**kwargs):
        if path.parent==pc:pytest.fail('held prefill opened an imported table')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'open',guarded)
    with pytest.raises(ValueError,match=HOLD):emitter._precompute_facts(str(pc),LOC,'SYNTHETIC','BGC001')
    with pytest.raises(ValueError,match=HOLD):emitter.emit_card_template(pkg,'BGC001',precompute_dir=str(pc))


@pytest.mark.parametrize('supplied',['existing','missing'])
def test_optional_batch_hold_prevents_output_and_wrong_fact(tmp_path,supplied):
    pkg,pc=fixture_case(tmp_path);before=core_hashes(pkg,pc)
    selected=pc if supplied=='existing' else tmp_path/'missing'
    result=emitter.emit_batch(pkg,scope='top',top_n=1,precompute_dir=str(selected))
    assert result['emitted']==[] and HOLD in result['skipped_reason']
    assert not (pkg/'mode_b_templates').exists()
    result=modeb_round.run_round(pkg,top_n=1,precompute_dir=str(selected))
    assert result['ok'] is False and HOLD in result['error']
    assert not (pkg/'modeb_round_worklist.json').exists()
    assert core_hashes(pkg,pc)==before


def test_actual_cli_optional_hold_is_nonzero_without_artifacts(tmp_path,capsys):
    pkg,pc=fixture_case(tmp_path);before=core_hashes(pkg,pc)
    assert cli.main(['modeb-round','--package',str(pkg),'--top-n','1','--from-precompute',str(pc)])==1
    assert HOLD in capsys.readouterr().err
    assert not (pkg/'mode_b_templates').exists() and not (pkg/'modeb_round_worklist.json').exists()
    assert core_hashes(pkg,pc)==before


def test_default_template_and_round_remain_available(tmp_path):
    pkg,pc=fixture_case(tmp_path);before=core_hashes(pkg,pc)
    card=emitter.emit_card_template(pkg,'BGC001')
    assert WRONG not in card and 'SYNTHETIC_NODE_A.1' in card and 'BGC001' in card
    result=modeb_round.run_round(pkg,top_n=1)
    assert result['ok'] is True and result['emitted_n']==1
    written=Path(result['entries'][0]['template']).read_text()
    assert written==card and WRONG not in written
    assert core_hashes(pkg,pc)==before


def test_core_parser_and_cohort_table_transport_remain_available(tmp_path):
    from .test_captured_actual_run import fixture_archive
    from mamey.parsers import parse_bgcs_from_zip
    source=fixture_archive(tmp_path/'input.zip');digest=hashlib.sha256(source.read_bytes()).hexdigest()
    records=parse_bgcs_from_zip(source,json_mode='off')
    assert len(records)==1 and records[0].contig=='SYNTHETIC_NODE_A.1'
    assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
    pkg,pc=fixture_case(tmp_path/'metadata')
    from tools import build_cohort_precompute as builder
    source_dir=tmp_path/'tables'/'SYNTHETIC';source_dir.mkdir(parents=True)
    input_table=source_dir/'ordered_domain_architectures_by_bgc.csv'
    input_table.write_bytes((pc/'COHORT_domain_architecture_by_bgc.csv').read_bytes())
    before=hashlib.sha256(input_table.read_bytes()).hexdigest();out=tmp_path/'transport.csv'
    assert builder._concat([str(source_dir)],input_table.name,str(out))==1
    assert out.read_bytes()==input_table.read_bytes() and hashlib.sha256(input_table.read_bytes()).hexdigest()==before


def test_actual_cli_without_optional_flag_remains_available(tmp_path):
    pkg,pc=fixture_case(tmp_path);before=core_hashes(pkg,pc)
    assert cli.main(['modeb-round','--package',str(pkg),'--top-n','1'])==0
    worklist=json.loads((pkg/'modeb_round_worklist.json').read_text())
    assert worklist['emitted_n']==1 and worklist['scaffold_invalid_n']==0
    assert WRONG not in Path(worklist['entries'][0]['template']).read_text()
    assert core_hashes(pkg,pc)==before
