"""Synthetic RID protocol/checkpoint controls: no network calls or real ledgers."""
import hashlib
import json
import time as real_time
from pathlib import Path
import pytest
from tests.test_443_blastp_crawl_runner import stage, load, args, statuses


def empty_xml(title):
    return f'<BlastXML2><BlastOutput2><Search><query-title>{title}</query-title><query-len>60</query-len><hits/></Search></BlastOutput2></BlastXML2>'


@pytest.mark.parametrize('text', ['<html>error</html>', '<Search>', '<Search><query-title>x</query-title></Search>',
 '<BlastXML2/>', '<BlastXML2><Error>failed</Error></BlastXML2>'])
def test_malformed_or_incomplete_response_is_typed(tmp_path, monkeypatch, text):
    mod, _, _ = load(tmp_path, monkeypatch)
    with pytest.raises(mod.RetrievalUnverified):
        mod.parse_xml2(text, 'AS-1', 'BGC1', {}, expected_queries=['wanted'])


def test_roster_admission_distinguishes_completed_no_hits_from_partial(tmp_path, monkeypatch):
    mod, _, _ = load(tmp_path, monkeypatch)
    assert mod.parse_xml2(empty_xml('a'), 'AS-1', 'BGC1', {}, expected_queries=['a']) == []
    for text, roster in ((empty_xml('a'), ['a', 'b']), (empty_xml('wrong'), ['a']),
                          ('<BlastXML2>'+empty_xml('a')+empty_xml('a')+'</BlastXML2>', ['a'])):
        with pytest.raises(mod.RetrievalUnverified):
            mod.parse_xml2(text, 'AS-1', 'BGC1', {}, expected_queries=roster)


def test_repeated_bad_fetch_keeps_same_rid_and_raw_evidence(tmp_path, monkeypatch):
    stage(tmp_path, ['a'])
    mod, _, ncbi = load(tmp_path, monkeypatch)
    monkeypatch.setattr(mod, 'fetch_xml2', lambda rid: '<html>temporarily unavailable</html>')
    assert mod.cmd_run(args(hours=.12)) == 0
    row = next(iter(mod.load_ledger().values()))
    assert row['status'] == 'retrieval_unverified'
    assert ncbi.submits == ['a']
    assert len(list(mod.XMLDIR.glob('RID000-*.xml'))) > 2
    receipt=json.loads((mod.XMLDIR/'RID000-admission.json').read_text())
    assert receipt['status']=='UNVERIFIED' and receipt['query_states'][0]['status']=='UNVERIFIED'
    assert receipt['raw_sha256']==hashlib.sha256((mod.XMLDIR/receipt['raw_file']).read_bytes()).hexdigest()
    assert not list(mod.RESDIR.rglob('*.csv'))
    assert mod.cmd_run(args(hours=.12)) == 0
    assert ncbi.submits == ['a']


def test_valid_no_hits_is_admitted_without_resubmit(tmp_path, monkeypatch):
    stage(tmp_path, ['a'])
    mod, _, ncbi = load(tmp_path, monkeypatch)
    monkeypatch.setattr(mod, 'fetch_xml2', lambda rid: empty_xml(ncbi.titles[rid]))
    assert mod.cmd_run(args(hours=.12)) == 0
    key, row = next(iter(mod.load_ledger().items()))
    assert row['status'] == 'fetched' and mod.retrieval_admitted(key, row)
    assert ncbi.submits == ['a']
    receipt = json.loads((mod.XMLDIR/'RID000-admission.json').read_text())
    assert receipt['status'] == 'COMPLETE_NO_HITS'
    assert json.loads(next(mod.RESDIR.rglob('_result_generation.json')).read_text())['files']


def test_expiry_uses_resumed_row_not_new_submit_row(tmp_path, monkeypatch):
    stage(tmp_path, ['old', 'fresh'])
    mod, clock, ncbi = load(tmp_path, monkeypatch)
    old = next(p for p in mod.all_query_files() if 'old' in p.name)
    key = mod.relkey(old)
    mod.save_ledger({key:dict(file=key, strain='AS-1', bgc=old.parent.name, rid='OLD', status='submitted',
        submit_iso=real_time.strftime('%Y-%m-%d %H:%M:%S', real_time.localtime(clock.now-7200)))})
    assert mod.cmd_run(args(hours=.12, max_wait=3600)) == 0
    led = mod.load_ledger()
    assert led[key]['status'] == 'unsure'
    assert statuses(mod)['AS-1__fresh.faa'] == 'fetched'
    assert 'UNSURE '+key+' RID OLD' in mod.LOG.read_text()


def test_second_resumed_expired_row_does_not_mutate_first(tmp_path, monkeypatch):
    stage(tmp_path, ['live', 'old'])
    mod, clock, ncbi = load(tmp_path, monkeypatch)
    led = {}
    for p in mod.all_query_files():
        key = mod.relkey(p); old = 'old' in p.name; rid='OLD' if old else 'LIVE'
        ncbi.rids[rid] = ('live', clock.now); ncbi.never.add('live')
        led[key] = dict(file=key, strain='AS-1', bgc=p.parent.name, rid=rid, status='submitted',
          submit_iso=real_time.strftime('%Y-%m-%d %H:%M:%S', real_time.localtime(clock.now-(7200 if old else 0))))
    mod.save_ledger(led)
    assert mod.cmd_run(args(hours=.04, max_wait=3600)) == 0
    assert statuses(mod) == {'AS-1__live.faa':'submitted','AS-1__old.faa':'unsure'}


def test_changed_or_legacy_fetched_query_is_operator_hold(tmp_path, monkeypatch):
    stage(tmp_path, ['a'])
    mod, _, ncbi = load(tmp_path, monkeypatch)
    assert mod.cmd_run(args(hours=.12)) == 0
    p = mod.all_query_files()[0]; p.write_text(p.read_text()+'A\n')
    assert mod.cmd_run(args(hours=.12)) == 0
    assert statuses(mod)['AS-1__a.faa'] == 'query_unbound'
    assert ncbi.submits == ['a']


def test_lane_exclusion_precedes_submit(tmp_path, monkeypatch):
    stage(tmp_path, ['a'])
    mod, _, ncbi = load(tmp_path, monkeypatch)
    with mod.lane_owner():
        assert mod.cmd_run(args(hours=.12)) == 3
        assert mod.cmd_rebuild() == 3
    assert ncbi.submits == []


def result_row(gene, acc):
    return ['AS-1','BGC1',gene,60,'','',1,acc,'x','t',90,10,'','1e-5',50,90]


@pytest.mark.parametrize('boundary',[1,2,3])
def test_result_generation_failure_restores_previous_pair(tmp_path, monkeypatch, boundary):
    mod, _, _ = load(tmp_path, monkeypatch)
    mod.BASE.mkdir(parents=True)
    mod.write_results('AS-1','BGC1',[result_row('a','old')])
    old = {p:p.read_bytes() for p in mod.RESDIR.rglob('*') if p.is_file()}
    original = mod._atomic_bytes; calls = 0
    def fail_once(path, data):
        nonlocal calls
        if path.name != '_result_transaction.json':
            calls += 1
            if calls == boundary: raise OSError('synthetic commit boundary')
        return original(path,data)
    monkeypatch.setattr(mod,'_atomic_bytes',fail_once)
    with pytest.raises(OSError): mod.write_results('AS-1','BGC1',[result_row('a','new')])
    assert {p:p.read_bytes() for p in old} == old
    assert not (mod.BASE/'_result_transaction.json').exists()


def test_interrupted_pending_generation_recovers_before_next_lane(tmp_path, monkeypatch):
    mod, _, _ = load(tmp_path, monkeypatch)
    mod.BASE.mkdir(parents=True)
    mod.write_results('AS-1','BGC1',[result_row('a','old')])
    old={p:p.read_bytes() for p in mod.RESDIR.rglob('*') if p.is_file()}
    atomic=mod._atomic_bytes
    monkeypatch.setattr(mod,'_recover_results',lambda: None)
    def die(path,data):
        if path.name.endswith('_top_hit_per_gene.csv'): raise KeyboardInterrupt()
        atomic(path,data)
    monkeypatch.setattr(mod,'_atomic_bytes',die)
    with pytest.raises(KeyboardInterrupt): mod.write_results('AS-1','BGC1',[result_row('a','new')])
    assert (mod.BASE/'_result_transaction.json').exists()
    monkeypatch.undo()
    # load() paths remain on module; restore the actual helper removed by monkeypatch.
    with mod.lane_owner(): pass
    assert {p:p.read_bytes() for p in old} == old


def test_ledger_replace_failure_keeps_previous_complete_bytes(tmp_path, monkeypatch):
    mod, _, _ = load(tmp_path, monkeypatch)
    mod.save_ledger({'a':dict(file='a',status='submitted')}); original=mod.LEDGER.read_bytes()
    replace=mod.os.replace
    def fail(src,dst):
        if Path(dst)==mod.LEDGER: raise OSError('synthetic ledger publish failure')
        return replace(src,dst)
    monkeypatch.setattr(mod.os,'replace',fail)
    with pytest.raises(OSError): mod.save_ledger({'b':dict(file='b',status='fetched')})
    assert mod.LEDGER.read_bytes()==original
    assert not list(mod.BASE.glob('.*.tmp'))


def test_valid_no_hits_clears_previous_rows_and_rebuild_is_coherent(tmp_path, monkeypatch):
    stage(tmp_path,['a'])
    mod, _, ncbi = load(tmp_path,monkeypatch)
    mod.BASE.mkdir(parents=True)
    mod.write_results('AS-1','BGC1',[result_row('a','stale')])
    monkeypatch.setattr(mod,'fetch_xml2',lambda rid:empty_xml(ncbi.titles[rid]))
    assert mod.cmd_run(args(hours=.12))==0
    csvf=mod.RESDIR/'AS-1/BGC1'/f'BGC1{mod.TOP10_SUFFIX}'
    assert len(csvf.read_text().splitlines())==1
    assert mod.cmd_rebuild()==0
    assert len(csvf.read_text().splitlines())==1
    key,row=next(iter(mod.load_ledger().items()))
    assert mod.retrieval_admitted(key,row)
    csvf.write_text('corrupted generation')
    assert not mod.retrieval_admitted(key,row)
    assert mod.cmd_rebuild()==3


@pytest.mark.parametrize('fields', [ '<bit-score>NaN</bit-score><evalue>1e-5</evalue><identity>2</identity><align-len>10</align-len>',
 '<bit-score>5</bit-score><evalue>1e-5</evalue><identity>12</identity><align-len>10</align-len>' ])
def test_invalid_hsp_is_unverified_not_empty(tmp_path,monkeypatch,fields):
    mod, _, _=load(tmp_path,monkeypatch)
    text=empty_xml('a').replace('<hits/>','<hits><Hit><accession>SYNTHETIC</accession><hsps><Hsp>'+fields+'</Hsp></hsps></Hit></hits>')
    with pytest.raises(mod.RetrievalUnverified):mod.parse_xml2(text,'AS-1','BGC1',{},expected_queries=['a'])


def test_unsupported_hits_cannot_certify_empty(tmp_path,monkeypatch):
    mod, _, _=load(tmp_path,monkeypatch)
    text=empty_xml('a').replace('<hits/>','<hits><unknown-result/></hits>')
    with pytest.raises(mod.RetrievalUnverified):mod.parse_xml2(text,'AS-1','BGC1',{},expected_queries=['a'])


def test_http_error_body_remains_typed_and_digest_bound(tmp_path,monkeypatch):
    stage(tmp_path,['a'])
    mod, _, ncbi=load(tmp_path,monkeypatch)
    def failed_fetch(rid):raise mod.TransportUnverified('curl rc=22: synthetic HTTP error','<html>synthetic HTTP failure</html>')
    monkeypatch.setattr(mod,'fetch_xml2',failed_fetch)
    assert mod.cmd_run(args(hours=.12))==0
    row=next(iter(mod.load_ledger().values()))
    receipt=json.loads((mod.XMLDIR/'RID000-admission.json').read_text())
    assert row['status']=='retrieval_unverified' and ncbi.submits==['a']
    assert receipt['status']=='UNVERIFIED' and 'rc=22' in receipt['error']
    assert hashlib.sha256((mod.XMLDIR/receipt['raw_file']).read_bytes()).hexdigest()==receipt['raw_sha256']


def test_curl_checks_http_status_and_preserves_returned_body(tmp_path,monkeypatch):
    mod, _, _=load(tmp_path,monkeypatch)
    def fake(command,**kw):
        assert '--fail-with-body' in command
        return type('Response',(),dict(returncode=22,stdout='synthetic error body',stderr='HTTP failure'))()
    monkeypatch.setattr(mod.subprocess,'run',fake)
    with pytest.raises(mod.TransportUnverified) as error:mod._curl(['https://invalid.example.test'],1)
    assert error.value.response=='synthetic error body'


def test_supported_xml_numeric_whitespace_still_admits_hit(tmp_path,monkeypatch):
    mod, _, _=load(tmp_path,monkeypatch)
    hit='<Hit><accession> SYNTHETIC </accession><hsps><Hsp><bit-score> 50 </bit-score><evalue> 1e-5 </evalue><identity> 9 </identity><align-len> 10 </align-len></Hsp></hsps></Hit>'
    text=empty_xml('a').replace('<query-len>60</query-len>','<query-len> 60 </query-len>').replace('<hits/>','<hits>'+hit+'</hits>')
    rows=mod.parse_xml2(text,'AS-1','BGC1',{},expected_queries=['a'])
    assert len(rows)==1 and rows[0][7]=='SYNTHETIC' and rows[0][10]==90
