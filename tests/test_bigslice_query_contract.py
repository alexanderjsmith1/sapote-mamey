"""Actual handler/fake-child contracts. No installed BiG-SLiCE or real model used."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import pytest

spec=importlib.util.spec_from_file_location('bigslice_independent_fixture',Path(__file__).with_name('_bigslice_contract_fixture.py'))
F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)

@pytest.fixture
def adapter(monkeypatch):
    m=F.adapter_module();monkeypatch.setattr(m,'run_watched',F.fake_watch);return m

@pytest.fixture
def case(tmp_path):return F.panel(tmp_path)


def test_query_actual_child_exports_exact_selected_run_and_four_components(adapter,case):
    before=F.sha(case.model)
    assert adapter.main(case.query)==0
    assert F.state(case)['status']=='COMPLETE'
    rows=F.exported(case)
    assert len(rows)==1
    assert rows[0]['exact_locus']=='Streptomyces_example_Type / CP000001.1 / region001 / BGC001'
    assert (rows[0]['model_run_id'],rows[0]['clustering_id'],rows[0]['gcf_id'],rows[0]['gcf_id_in_run'],rows[0]['rank'],rows[0]['membership_value'])==('3','11','101','1','0','0.25')
    assert rows[0]['model_sha256']==before==F.sha(case.model)
    actual=json.loads((case.runtime/'last_argv.json').read_text())
    assert actual[actual.index('--query')+2]==str(case.work)
    assert actual[actual.index('--run_id')+1]=='3'
    assert actual[actual.index('-t')+1]=='1'
    assert actual[actual.index('--program_db_folder')+1]==str(case.hmm)
    assert str(case.out) not in actual
    assert not (case.work/'.mamey-bigslice-lease').exists()


def test_two_fresh_queries_use_distinct_names_and_report_ids(adapter,case):
    assert adapter.main(case.query)==0
    first=F.exported(case)[0]
    out2=case.root/'export2';argv=[str(out2) if a==str(case.out) else a for a in case.query]
    assert adapter.main(argv)==0
    with sqlite3.connect(case.work/'reports/reports.db') as db:
        reports=db.execute('SELECT id,name FROM reports ORDER BY id').fetchall()
    assert len(reports)==2 and reports[0][1]!=reports[1][1]
    assert reports[0][0]==int(first['report_id']) and reports[1][0]!=reports[0][0]


def test_occupied_output_preserves_prior_success_and_never_launches(adapter,case,monkeypatch):
    case.out.mkdir();p=case.out/'RUN_STATE.json';p.write_text('{"status":"COMPLETE","attempt_id":"historical"}')
    before=p.read_bytes()
    monkeypatch.setattr(adapter,'run_watched',lambda *a,**k:pytest.fail('child must not launch'))
    assert adapter.main(case.query)==2 and p.read_bytes()==before
    assert not (case.work/'.mamey-bigslice-lease').exists()

@pytest.mark.parametrize('mode,code',[('nonzero','CHILD_FAILED'),('row_only','FileNotFoundError'),('wrong_run','REPORT_RUN_MISMATCH'),('duplicate_rank','MEMBERSHIP_CONFLICT'),('wrong_gcf','MEMBERSHIP_CONFLICT'),('mutate_model','SOURCE_CHANGED')])
def test_later_failure_never_consumes_prior_success_and_preserves_diagnostics(adapter,case,mode,code):
    assert adapter.main(case.query)==0
    prior=(case.out/'RUN_STATE.json').read_bytes();prior_tsv=(case.out/'bigslice_assignment.tsv').read_bytes()
    F.control(case,mode)
    new=case.root/'failed';argv=[str(new) if a==str(case.out) else a for a in case.query]
    assert adapter.main(argv)==2
    failure=json.loads((new/'RUN_STATE.json').read_text())
    assert failure['status']=='FAILED' and failure['error_code']==code
    assert not (new/'bigslice_assignment.tsv').exists()
    assert (case.out/'RUN_STATE.json').read_bytes()==prior and (case.out/'bigslice_assignment.tsv').read_bytes()==prior_tsv
    assert (new/'native.log').exists()
    assert not (case.work/'.mamey-bigslice-lease').exists()


def test_timeout_stop_receipt_prevents_success_even_if_child_exit_zero(adapter,case,monkeypatch):
    def stopped(command,**kw):
        result=F.fake_watch(command,**kw)
        if '--query' in command:result['stop_reason']='TIME_LIMIT'
        return result
    monkeypatch.setattr(adapter,'run_watched',stopped)
    assert adapter.main(case.query)==2 and F.state(case)['error_code']=='CHILD_FAILED'
    assert json.loads((case.out/'native_process.json').read_text())['stop_reason']=='TIME_LIMIT'


def test_keyboard_interrupt_records_failed_attempt_and_releases_owned_lease(adapter,case,monkeypatch):
    monkeypatch.setattr(adapter,'run_watched',lambda *a,**k:(_ for _ in ()).throw(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):adapter.main(case.query)
    assert F.state(case)['status']=='FAILED' and F.state(case)['error_code']=='KeyboardInterrupt'
    assert not (case.work/'.mamey-bigslice-lease').exists()


def test_existing_model_lease_is_not_deleted(adapter,case):
    lease=case.work/'.mamey-bigslice-lease';lease.write_text('other-attempt\n')
    assert adapter.main(case.query)==2 and lease.read_text()=='other-attempt\n'
    assert F.state(case)['status']=='FAILED'

@pytest.mark.parametrize('flag,value',[('--threads','0'),('--threads','5'),('--n-ranks','0'),('--timeout','0'),('--timeout','nan')])
def test_invalid_resource_controls_refuse_without_writes(adapter,case,flag,value):
    argv=case.query[:]
    if flag in argv:argv[argv.index(flag)+1]=value
    else:argv.extend([flag,value])
    assert adapter.main(argv)==2 and not case.out.exists()


def test_read_only_model_root_refuses_without_any_model_or_export_mutation(adapter,case):
    before=F.sha(case.model)
    assert adapter.main([*case.query,'--read-only-root',str(case.work)])==2
    assert not case.out.exists() and F.sha(case.model)==before and not (case.work/'.mamey-bigslice-lease').exists()


def test_output_input_symlink_alias_refuses(adapter,case):
    alias=case.root/'alias';alias.symlink_to(case.inp,target_is_directory=True)
    argv=[str(alias/'export') if a==str(case.out) else a for a in case.query]
    assert adapter.main(argv)==2 and not (case.inp/'export').exists()


def test_legacy_three_option_command_has_no_write_authority(adapter,case):
    with pytest.raises(SystemExit) as error:
        adapter.main(['query','--input',str(case.inp),'--bigfam-model',str(case.work),'--out',str(case.out)])
    assert error.value.code==2 and not case.out.exists()


def test_missing_runtime_admission_is_terminal_before_native_launch(adapter,case,monkeypatch):
    data=json.loads(case.admission.read_text());data['review_status']='UNKNOWN';F.write_json(case.admission,data)
    monkeypatch.setattr(adapter,'run_watched',lambda *a,**k:pytest.fail('unknown runtime must not execute'))
    assert adapter.main(case.query)==2 and F.state(case)['error_code']=='RUNTIME_NOT_ADMITTED'


def test_model_profile_does_not_allow_guessed_normalization(adapter,case):
    data=json.loads(case.model_profile.read_text());data['normalization']='legacy-unnormalized';F.write_json(case.model_profile,data)
    assert adapter.main(case.query)==2 and F.state(case)['error_code']=='MODEL_PROFILE_NOT_ADMITTED'


def test_cluster_creates_fresh_native_subdir_and_exact_export(adapter,case):
    assert adapter.main(case.cluster)==0
    assert F.state(case)['status']=='COMPLETE'
    assert (case.out/'native_result/result/data.db').is_file()
    assert F.exported(case)[0]['gcf_id']=='101'
    metadata=(case.out/'input_view/datasets.tsv').read_text()
    assert 'taxonomy unspecified' in metadata and 'symbiont' not in metadata
    assert adapter.main(case.cluster)==2  # no stale staging reuse or overwrite


def test_cluster_duplicate_basename_refuses_before_child(adapter,tmp_path,monkeypatch):
    c=F.panel(tmp_path,('CP000001.1','CP000002.1'))
    for i,row in enumerate(c.rows):
        old=c.inp/row['relative_path'];dest=c.inp/f'folder{i}'/'same.region001.gbk';dest.parent.mkdir();old.rename(dest);row['relative_path']=dest.relative_to(c.inp).as_posix()
    c.save_rows()
    monkeypatch.setattr(adapter,'run_watched',lambda *a,**k:pytest.fail('colliding staging must refuse'))
    assert adapter.main(c.cluster)==2 and F.state(c)['error_code']=='STAGING_COLLISION'


def test_handler_keeps_all_requested_ranks_not_only_rank_zero(adapter,case):
    argv=case.query[:];argv[argv.index('--n-ranks')+1]='2'
    assert adapter.main(argv)==0
    assert [(r['rank'],r['gcf_id'],r['membership_value']) for r in F.exported(case)]==[('0','101','0.25'),('1','102','0.75')]


def test_actual_cli_fake_child_with_existing_resource_watcher(case,tmp_path):
    # Root-only execution after admission: real handler + real watcher, synthetic child only.
    import os,subprocess,sys
    tool=Path(__file__).resolve().parents[1]/'tools/bigslice_query.py'
    result=subprocess.run([sys.executable,str(tool),*case.query],capture_output=True,text=True,timeout=20,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    assert result.returncode==0,(result.stdout,result.stderr)
    process=json.loads((case.out/'native_process.json').read_text())
    assert process['exit_code']==0 and process['stop_reason'] is None and process['peak_process_tree_rss']>0
    assert process['argv'][-len(json.loads((case.runtime/'last_argv.json').read_text())):]==json.loads((case.runtime/'last_argv.json').read_text())
    assert F.exported(case)[0]['exact_locus'].endswith('CP000001.1 / region001 / BGC001')


def test_symlinked_native_report_destination_refused_before_any_child(adapter,case,monkeypatch):
    elsewhere=case.root/'protected';elsewhere.mkdir()
    reports=case.work/'reports';reports.mkdir();(reports/'1').symlink_to(elsewhere,target_is_directory=True)
    monkeypatch.setattr(adapter,'run_watched',lambda *a,**k:pytest.fail('escaping native write must refuse'))
    assert adapter.main(case.query)==2 and F.state(case)['error_code']=='MODEL_PATH_ALIAS'
    assert list(elsewhere.iterdir())==[]


def test_wrong_hmm_library_is_not_silently_replaced(adapter,case,monkeypatch):
    (case.hmm/'biosynthetic_pfams/biopfam.md5sum').write_text('3'*32+'\n')
    monkeypatch.setattr(adapter,'run_watched',lambda *a,**k:pytest.fail('wrong HMM must not execute'))
    assert adapter.main(case.query)==2 and F.state(case)['error_code']=='HMM_MODEL_MISMATCH'


def test_missing_runtime_source_file_binding_holds_unknown_distribution(adapter,case,monkeypatch):
    data=json.loads(case.admission.read_text());data['source_files']=data['source_files'][:-1];F.write_json(case.admission,data)
    monkeypatch.setattr(adapter,'run_watched',lambda *a,**k:pytest.fail('unbound source must not execute'))
    assert adapter.main(case.query)==2 and F.state(case)['error_code']=='RUNTIME_SOURCE_BINDING'



def test_help_probe_works_with_custom_hmm_and_no_default_adjacent_models(adapter,case):
    assert not (case.binary.parent/'bigslice-models').exists()
    assert adapter.main(case.query)==0 and F.state(case)['status']=='COMPLETE'
    probe=json.loads((case.out/'RUNTIME_PROBE.json').read_text())
    assert probe['kind']=='UPSTREAM_HELP_BANNER' and probe['cli_observed_versions']==['2.0.0'] and probe['admitted'] is True
    assert probe['command']==[__import__('sys').executable,str(case.binary),'--help']
    assert probe['actual_distribution_version'] is None  # this fixture is an uninstalled synthetic source tree
    assert '--version' not in json.loads((case.out/'runtime_probe_process.json').read_text())['argv']


def test_independent_fake_reproduces_upstream_version_default_hmm_trap(case):
    import subprocess,sys
    version=subprocess.run([sys.executable,str(case.binary),'--version','--program_db_folder',str(case.hmm)],capture_output=True,text=True,timeout=5)
    assert version.returncode==0 and "Can't find HMM model libraries!" in version.stdout and '[ Version 2.0.0 ]' not in version.stdout
    help_result=subprocess.run([sys.executable,str(case.binary),'--help'],capture_output=True,text=True,timeout=5)
    assert help_result.returncode==0 and '[ Version 2.0.0 ]' in help_result.stdout
    assert not (case.binary.parent/'bigslice-models').exists() and not case.out.exists()


@pytest.mark.parametrize('help_text',['[ Version 1.0.0 ]','[ Version 2.0.00 ]','[ Version 2.0.0rc1 ]','[ Version 2.0.0 ] [ Version 2.0.0 ]','BiG-SLiCE version 2.0.0'])
def test_help_requires_one_exact_cli_banner_and_never_starts_query(adapter,case,help_text):
    data=json.loads((case.runtime/'control.json').read_text());data['help_text']=help_text;F.write_json(case.runtime/'control.json',data)
    assert adapter.main(case.query)==2 and F.state(case)['error_code']=='RUNTIME_VERSION'
    assert json.loads((case.out/'RUNTIME_PROBE.json').read_text())['admitted'] is False
    assert not (case.out/'native.log').exists() and not (case.runtime/'last_argv.json').exists()


def test_orphan_valid_database_is_not_promoted_by_row_only_zero_exit(adapter,case,monkeypatch):
    # Exact ROOT_BINDING_REPRODUCTION_01 shape: valid query DB moved to unindexed1,
    # reports index removed, misleading child would create only a new row.
    _,old,index=F.seed_query(case)
    dest=case.work/'reports/1';dest.mkdir();old.rename(dest/'data.db');index.unlink()
    before=F.sha(dest/'data.db');F.control(case,'row_only')
    monkeypatch.setattr(adapter,'run_watched',lambda *a,**k:pytest.fail('orphan must be refused before native can overwrite it'))
    assert adapter.main(case.query)==2 and F.state(case)['error_code']=='ORPHAN_REPORT_DESTINATION'
    assert F.sha(dest/'data.db')==before and not index.exists()
    assert not (case.out/'bigslice_assignment.tsv').exists() and not (case.work/'.mamey-bigslice-lease').exists()


@pytest.mark.parametrize('mode',['cluster_wrong_threshold','cluster_wrong_method'])
def test_cluster_success_exit_cannot_hide_configuration_mismatch(adapter,case,mode):
    F.control(case,mode)
    assert adapter.main(case.cluster)==2 and F.state(case)['error_code']=='CLUSTER_CONFIG_MISMATCH'
    assert (case.out/'CLUSTER_MODEL_BINDING.json').is_file() and not (case.out/'bigslice_assignment.tsv').exists()


def test_cluster_nondefault_requested_threshold_is_retained(adapter,case):
    assert adapter.main([*case.cluster,'--threshold','0.65'])==0
    selected=json.loads((case.out/'SELECTED_RESULT.json').read_text())
    assert selected['model_scope']['threshold']==0.65 and selected['model_scope']['clustering_method']=='birch'


def test_cluster_model_mutation_after_scope_is_detected_before_export(adapter,case,monkeypatch):
    original=adapter.read_selected
    def mutate_after_read(*args,**kwargs):
        result=original(*args,**kwargs)
        with sqlite3.connect(case.out/'native_result/result/data.db') as db:
            db.execute("UPDATE run SET prog_params='mutation after model_scope' WHERE id=3")
        return result
    monkeypatch.setattr(adapter,'read_selected',mutate_after_read)
    assert adapter.main(case.cluster)==2 and F.state(case)['error_code']=='SOURCE_CHANGED'
    assert not (case.out/'bigslice_assignment.tsv').exists()
    recorded=json.loads((case.out/'CLUSTER_MODEL_BINDING.json').read_text())
    assert recorded['model']['sha256']!=F.sha(case.out/'native_result/result/data.db')


def test_executed_entry_cannot_be_unrelated_to_declared_source_entry(adapter,case,monkeypatch):
    foreign=case.root/'other.py';foreign.write_text("print('[ Version 2.0.0 ]')\n")
    data=json.loads(case.admission.read_text());data['executable_sha256']=F.sha(foreign);F.write_json(case.admission,data)
    argv=[str(foreign) if a==str(case.binary) else a for a in case.query]
    monkeypatch.setattr(adapter,'run_watched',lambda *a,**k:pytest.fail('unrelated entry must never execute'))
    assert adapter.main(argv)==2 and F.state(case)['error_code']=='RUNTIME_ENTRY_SOURCE'



def test_cli_banner_cannot_substitute_for_separate_distribution_admission(adapter,case):
    data=json.loads(case.admission.read_text());data['distribution']={'name':'bigslice','mode':'installed-distribution','version':'0.0.0-uninstalled-fixture'};F.write_json(case.admission,data)
    assert adapter.main(case.query)==2 and F.state(case)['error_code']=='RUNTIME_DISTRIBUTION'
    assert (case.out/'RUNTIME_IDENTITY.json').is_file() and not (case.out/'runtime_probe.log').exists() and not (case.out/'native.log').exists()


def test_unknown_distribution_provenance_refused_before_entry_execution(adapter,case,monkeypatch):
    data=json.loads(case.admission.read_text());data.pop('distribution');F.write_json(case.admission,data)
    monkeypatch.setattr(adapter,'run_watched',lambda *a,**k:pytest.fail('unknown distribution must not execute'))
    assert adapter.main(case.query)==2 and F.state(case)['error_code']=='RUNTIME_DISTRIBUTION'



def test_actual_query_producer_receipt_round_trips_through_read_handler(adapter,case):
    assert adapter.main(case.query)==0
    original=F.exported(case)[0]
    result=json.loads((case.out/'SELECTED_RESULT.json').read_text())
    fresh=case.root/'read-export';argv=[str(fresh) if a==str(case.out) else a for a in case.read]
    argv += ['--query-db',result['query_db']['path'],'--reports-db',str(case.work/'reports/reports.db'),
             '--report-id',str(result['report_id']),'--query-name',result['query_provenance']['query_name'],
             '--query-receipt',str(case.out/'SELECTED_RESULT.json')]
    assert adapter.main(argv)==0 and json.loads((fresh/'RUN_STATE.json').read_text())['status']=='COMPLETE'
    import csv
    with (fresh/'bigslice_assignment.tsv').open() as handle:reread=list(csv.DictReader(handle,delimiter='\t'))[0]
    assert reread['attempt_id']!=original['attempt_id']
    assert {k:v for k,v in reread.items() if k!='attempt_id'}=={k:v for k,v in original.items() if k!='attempt_id'}
