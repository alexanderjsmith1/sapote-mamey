"""Independent selected-query SQLite and exact source identity controls."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import pytest

spec=importlib.util.spec_from_file_location('bigslice_reader_fixture',Path(__file__).with_name('_bigslice_contract_fixture.py'))
F=importlib.util.module_from_spec(spec);spec.loader.exec_module(F)

@pytest.fixture
def adapter(monkeypatch):
    m=F.adapter_module();monkeypatch.setattr(m,'run_watched',F.fake_watch);return m


def test_read_exact_report_ignores_unrelated_newer_query_and_preserves_databases(adapter,tmp_path):
    c=F.panel(tmp_path);argv,qdb,index=F.seed_query(c)
    before={p:F.sha(p) for p in (c.model,qdb,index)}
    assert adapter.main(argv)==0
    assert all(F.sha(p)==sha for p,sha in before.items())
    row=F.exported(c)[0]
    assert (row['report_id'],row['model_run_id'],row['gcf_id'])==('4','3','101')
    assert F.state(c)['denominator']=={'selected_inputs':1,'parsed_bgcs':1,'membership_rows':1,'excluded':0}

@pytest.mark.parametrize('sql,expected',[
    ("UPDATE reports_run SET run_id=8 WHERE report_id=4",'READ_QUERY_SELECTION'),
    ("INSERT INTO reports_run VALUES(4,3)",'READ_QUERY_SELECTION'),
    ("UPDATE reports SET name='different' WHERE id=4",'READ_QUERY_SELECTION')])
def test_report_selection_conflicts_fail_not_latest_fallback(adapter,tmp_path,sql,expected):
    c=F.panel(tmp_path);argv,qdb,index=F.seed_query(c)
    with sqlite3.connect(index) as db:db.execute(sql)
    assert adapter.main(argv)==2 and F.state(c)['error_code']==expected
    assert not (c.out/'bigslice_assignment.tsv').exists()

@pytest.mark.parametrize('sql,code',[
    ("UPDATE gcf_membership SET gcf_id=202",'MEMBERSHIP_CONFLICT'),
    ("INSERT INTO gcf_membership VALUES(1,102,0,0.5)",'MEMBERSHIP_CONFLICT'),
    ("INSERT INTO gcf_membership VALUES(99,101,0,0.5)",'MEMBERSHIP_CONFLICT'),
    ("UPDATE gcf_membership SET rank=2",'MEMBERSHIP_VALUE'),
    ("UPDATE gcf_membership SET membership_value=-1",'MEMBERSHIP_VALUE'),
    ("DELETE FROM gcf_membership",'MEMBERSHIP_DENOMINATOR'),
    ("UPDATE schema SET parent_schema_ver='0.0.0'",'QUERY_SCHEMA_UNSUPPORTED')])
def test_query_membership_or_schema_damage_keeps_terminal_failure(adapter,tmp_path,sql,code):
    c=F.panel(tmp_path);argv,qdb,index=F.seed_query(c)
    with sqlite3.connect(qdb) as db:db.execute(sql)
    F.close_seed_receipt(c,qdb,index)  # independent malformed-but-bound input reaches the specific reader gate
    assert adapter.main(argv)==2 and F.state(c)['error_code']==code


def test_missing_db_never_created_and_no_recursive_first_db_fallback(adapter,tmp_path):
    c=F.panel(tmp_path);missing=c.root/'absent.db'
    argv=[str(missing) if a==str(c.model) else a for a in c.read]
    assert adapter.main(argv)==2 and not missing.exists() and not c.out.exists()


def test_nonempty_wal_is_explicitly_held(adapter,tmp_path):
    c=F.panel(tmp_path);argv,qdb,index=F.seed_query(c)
    sidecar=Path(str(qdb)+'-wal');sidecar.write_bytes(b'not-a-checkpointed-snapshot')
    before=sidecar.read_bytes()
    assert adapter.main(argv)==2 and F.state(c)['error_code']=='DATABASE_NOT_QUIESCENT'
    assert sidecar.read_bytes()==before


def test_readonly_connection_rejects_write_and_preserves_source(adapter,tmp_path):
    c=F.panel(tmp_path);before=F.sha(c.model)
    with adapter.readonly_db(c.model,adapter.MODEL_COLUMNS) as db:
        with pytest.raises(sqlite3.OperationalError):db.execute('DELETE FROM run')
    assert F.sha(c.model)==before

@pytest.mark.parametrize('contigs',[
    ('CP000001.1','CP000001.2'),
    ('NODE_1_length_1000_cov_3.25','NODE_1_length_1000_cov_3.75'),
    ('completeChromosomeA','completeChromosomeB')])
def test_full_contigs_versions_and_repeated_region_numbers_remain_distinct(adapter,tmp_path,contigs):
    c=F.panel(tmp_path,contigs,strain='Mixed_Case_Strain_Ref');argv,qdb,index=F.seed_query(c)
    assert adapter.main(argv)==0
    observed=F.exported(c)
    assert {r['full_contig'] for r in observed}==set(contigs)
    assert {r['region'] for r in observed}=={'region001'}
    assert {r['strain'] for r in observed}=={'Mixed_Case_Strain_Ref'}
    assert {r['exact_locus'] for r in observed}=={f'Mixed_Case_Strain_Ref / {contigs[0]} / region001 / BGC001',f'Mixed_Case_Strain_Ref / {contigs[1]} / region001 / BGC002'}

@pytest.mark.parametrize('field,value,code',[
    ('full_contig','NODE_1','ExactLocusIdentityError'),
    ('full_contig','CP000001.2','INVENTORY_BINDING'),
    ('strain','Mixed_case_wrong','INVENTORY_STRAIN'),
    ('bgc_alias','BGC099','INVENTORY_BINDING'),
    ('sha256','0'*64,'SOURCE_CHANGED'),
    ('inventory_row_sha256','0'*64,'INVENTORY_ROW'),
    ('source_member','not-present.region001.gbk','INVENTORY_BINDING')])
def test_crosswalk_conflicts_cannot_be_repaired_by_names(adapter,tmp_path,field,value,code):
    c=F.panel(tmp_path);c.rows[0][field]=value;c.save_rows()
    assert adapter.main(c.query)==2 and F.state(c)['error_code']==code
    assert not (c.out/'bigslice_assignment.tsv').exists()


def test_duplicate_db_source_records_cannot_share_one_alias(adapter,tmp_path):
    c=F.panel(tmp_path);argv,qdb,index=F.seed_query(c)
    with sqlite3.connect(qdb) as db:
        db.execute('INSERT INTO bgc SELECT 2,orig_folder,orig_filename,length_nt FROM bgc WHERE id=1')
        db.execute('INSERT INTO gcf_membership VALUES(2,101,0,0.25)')
    F.close_seed_receipt(c,qdb,index)  # independently admit this malformed source for denominator-gate coverage
    assert adapter.main(argv)==2 and F.state(c)['error_code']=='PARSED_DENOMINATOR'


def test_extra_unbound_input_is_retained_as_denominator_refusal(adapter,tmp_path):
    c=F.panel(tmp_path);(c.inp/'unbound.region002.gbk').write_text('not admitted')
    assert adapter.main(c.query)==2 and F.state(c)['error_code']=='INPUT_DENOMINATOR'


def test_missing_supplied_bigscape_tsv_fails_instead_of_silently_ignoring(adapter,tmp_path):
    c=F.panel(tmp_path);argv,qdb,index=F.seed_query(c)
    assert adapter.main([*argv,'--bigscape-tsv',str(c.root/'missing.tsv')])==2
    assert F.state(c)['status']=='FAILED' and not (c.out/'bigslice_assignment.tsv').exists()


def test_model_unfinished_or_wrong_hmm_refused_before_child(adapter,tmp_path,monkeypatch):
    c=F.panel(tmp_path)
    with sqlite3.connect(c.model) as db:db.execute('UPDATE run SET status=5 WHERE id=3')
    monkeypatch.setattr(adapter,'run_watched',lambda *a,**k:pytest.fail('unfinished model must not execute'))
    assert adapter.main(c.query)==2 and F.state(c)['error_code']=='MODEL_RUN_NOT_FINISHED'


def test_cluster_database_reader_selects_run_not_all_rank_zero_memberships(adapter,tmp_path):
    c=F.panel(tmp_path)
    name=c.rows[0]['relative_path']
    with sqlite3.connect(c.model) as db:
        db.execute('INSERT INTO bgc VALUES(1,?,?,100)',(str(c.inp),name))
        db.execute('INSERT INTO run_bgc_status VALUES(1,3,7)')
        db.execute('INSERT INTO gcf_membership VALUES(1,101,0,0.25)')
        db.execute('INSERT INTO gcf_membership VALUES(1,202,0,0.05)')
    profile=json.loads(c.model_profile.read_text());profile['model_sha256']=F.sha(c.model);F.write_json(c.model_profile,profile)
    assert adapter.main(c.read)==0
    assert [(r['model_run_id'],r['gcf_id'],r['membership_value']) for r in F.exported(c)]==[('3','101','0.25')]


def test_source_region_header_version_must_match_physical_inventory(adapter,tmp_path):
    c=F.panel(tmp_path)
    data=(c.inp/c.rows[0]['relative_path']).read_bytes().replace(b'VERSION     CP000001.1',b'VERSION     CP000001.2')
    (c.inp/c.rows[0]['relative_path']).write_bytes(data)
    import zipfile
    with zipfile.ZipFile(c.source,'w',compression=zipfile.ZIP_STORED) as archive:archive.writestr(c.rows[0]['source_member'],data)
    manifest=json.loads(c.manifest.read_text());manifest['input_zip_sha256']=F.sha(c.source);F.write_json(c.manifest,manifest)
    c.rows[0].update(sha256=F.sha(c.inp/c.rows[0]['relative_path']),source_zip_sha256=F.sha(c.source),manifest_sha256=F.sha(c.manifest));c.save_rows()
    assert adapter.main(c.query)==2 and F.state(c)['error_code']=='GBK_REGION_UNSUPPORTED'


@pytest.mark.parametrize('bridge_state',['absent','exact','wrong_member'])
def test_bigscape_family_ids_remain_method_specific_and_need_explicit_member_bridge(adapter,tmp_path,bridge_state):
    c=F.panel(tmp_path);argv,qdb,index=F.seed_query(c)
    import csv
    table=c.root/'bigscape.tsv';family='bigscape-gcf:v1/run/1/cutoff/0.5/family/101'
    with table.open('w',newline='') as h:
        w=csv.DictWriter(h,fieldnames=['family_id','run_id','normalized_cutoff','qualified_family_id','members_locators'],delimiter='\t');w.writeheader()
        w.writerow(dict(family_id='101',run_id='1',normalized_cutoff='0.5',qualified_family_id=family,members_locators='explicit-source-member'))
    argv += ['--bigscape-tsv',str(table)]
    if bridge_state!='absent':
        bridge=c.root/'bridge.tsv'
        with bridge.open('w',newline='') as h:
            w=csv.DictWriter(h,fieldnames=['strain','full_contig','region','bgc_alias','qualified_family_id','member_locator'],delimiter='\t');w.writeheader()
            w.writerow(dict(strain=c.strain,full_contig='CP000001.1',region='region001',bgc_alias='BGC001',qualified_family_id=family,member_locator='explicit-source-member' if bridge_state=='exact' else 'other-member'))
        argv += ['--bigscape-bridge',str(bridge)]
    result=adapter.main(argv)
    if bridge_state=='wrong_member':
        assert result==2 and F.state(c)['error_code']=='COMPARISON_BRIDGE'
    else:
        assert result==0
        comparison=json.loads((c.out/'SELECTED_RESULT.json').read_text())['comparison']
        assert comparison['status']==('HOLD_EXACT_LOCUS_BRIDGE_REQUIRED' if bridge_state=='absent' else 'BOUND_OPERATOR_BRIDGE_NO_AGREEMENT_STATISTIC')
        own=F.exported(c)[0]['qualified_family_id']
        assert own!=family and json.loads(own)[0]=='bigslice-gcf:v1'



def test_foreign_same_id_model_cannot_label_existing_query_distances(adapter,tmp_path):
    c=F.panel(tmp_path);argv,qdb,index=F.seed_query(c)
    foreign=c.root/'foreign_model.db';foreign.write_bytes(c.model.read_bytes())
    with sqlite3.connect(foreign) as db:db.execute("UPDATE run SET prog_params='independently different model with same IDs' WHERE id=3")
    profile=c.root/'foreign_profile.json';data=json.loads(c.model_profile.read_text());data['model_sha256']=F.sha(foreign);F.write_json(profile,data)
    argv=[str(foreign) if a==str(c.model) else str(profile) if a==str(c.model_profile) else a for a in argv]
    before=F.sha(qdb)
    assert adapter.main(argv)==2 and F.state(c)['error_code']=='QUERY_MODEL_PROVENANCE'
    assert F.sha(qdb)==before and not (c.out/'bigslice_assignment.tsv').exists()


def test_replaced_original_model_same_path_and_ids_refused(adapter,tmp_path):
    c=F.panel(tmp_path);argv,qdb,index=F.seed_query(c)
    with sqlite3.connect(c.model) as db:db.execute("UPDATE run SET prog_params='replacement at original path' WHERE id=3")
    data=json.loads(c.model_profile.read_text());data['model_sha256']=F.sha(c.model);F.write_json(c.model_profile,data)
    assert adapter.main(argv)==2 and F.state(c)['error_code']=='QUERY_MODEL_PROVENANCE'
    assert not (c.out/'bigslice_assignment.tsv').exists()


def test_external_query_without_producer_receipt_is_explicitly_held(adapter,tmp_path):
    c=F.panel(tmp_path);argv,qdb,index=F.seed_query(c);i=argv.index('--query-receipt');del argv[i:i+2]
    assert adapter.main(argv)==2 and not c.out.exists()
    assert qdb.is_file() and index.is_file()


@pytest.mark.parametrize('artifact',['SELECTED_RESULT.json','RUN_MANIFEST.json','RUN_STATE.json'])
def test_broken_producer_receipt_closure_refuses(adapter,tmp_path,artifact):
    c=F.panel(tmp_path);argv,qdb,index=F.seed_query(c)
    p=c.root/'producer'/artifact;data=json.loads(p.read_text())
    if artifact=='RUN_STATE.json':data['status']='FAILED'
    else:data['unbound_edit']=True
    F.write_json(p,data)
    assert adapter.main(argv)==2 and F.state(c)['error_code']=='QUERY_PROVENANCE'
    assert not (c.out/'bigslice_assignment.tsv').exists()


def test_modified_query_db_without_new_producer_binding_is_refused(adapter,tmp_path):
    c=F.panel(tmp_path);argv,qdb,index=F.seed_query(c)
    with sqlite3.connect(qdb) as db:db.execute('UPDATE gcf_membership SET membership_value=0.99')
    assert adapter.main(argv)==2 and F.state(c)['error_code']=='QUERY_INPUT_PROVENANCE'


def test_later_unrelated_report_addition_does_not_break_exact_query_closure(adapter,tmp_path):
    c=F.panel(tmp_path);argv,qdb,index=F.seed_query(c)
    with sqlite3.connect(index) as db:
        db.execute("INSERT INTO reports VALUES(99,'query','later unrelated','2000-01-03')")
        db.execute('INSERT INTO reports_run VALUES(99,8)')
    assert adapter.main(argv)==0 and F.exported(c)[0]['report_id']=='4'


def test_selected_report_metadata_change_refused_even_if_ids_and_name_match(adapter,tmp_path):
    c=F.panel(tmp_path);argv,qdb,index=F.seed_query(c)
    with sqlite3.connect(index) as db:db.execute("UPDATE reports SET creation_date='changed' WHERE id=4")
    assert adapter.main(argv)==2 and F.state(c)['error_code']=='QUERY_REPORT_PROVENANCE'



def test_crosswalk_row_limit_is_enforced_during_bounded_read(adapter,tmp_path,monkeypatch):
    c=F.panel(tmp_path,('CP000001.1','CP000002.1'));monkeypatch.setattr(adapter,'MAX_ROWS',1)
    monkeypatch.setattr(adapter,'run_watched',lambda *a,**k:pytest.fail('oversized metadata cannot launch native'))
    assert adapter.main(c.query)==2 and F.state(c)['error_code']=='CSV_ROW_LIMIT'


def test_bridge_tsv_byte_and_row_limits_apply_before_materializing_all_rows(adapter,tmp_path,monkeypatch):
    p=tmp_path/'bridge.tsv';p.write_text('strain\tfull_contig\nA\tCP000001.1\nB\tCP000002.1\n')
    monkeypatch.setattr(adapter,'MAX_ROWS',1)
    with pytest.raises(adapter.AdapterError,match='CSV_ROW_LIMIT'):adapter.bounded_tsv(p,('strain','full_contig'),'COMPARISON_BRIDGE')
    monkeypatch.setattr(adapter,'MAX_FILE',1)
    with pytest.raises(adapter.AdapterError,match='METADATA_LIMIT'):adapter.bounded_tsv(p,('strain','full_contig'),'COMPARISON_BRIDGE')
