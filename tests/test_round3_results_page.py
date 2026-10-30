"""The entry page must not hide incomplete evidence behind a success badge."""
import json
import pytest
from mamey.package_addons import write_open_me_first

@pytest.mark.parametrize('status,gate_status,findings,label',[
    ('MAMEY_COMPLETE_WITH_ISSUES','MAMEY_COMPLETE',[],'EXTRACTION HAS ISSUES'),
    ('MAMEY_COMPLETE','MAMEY_COMPLETE',['MAIN_JSON_WALKER_TRUNCATED'],'EXTRACTION HAS ISSUES'),
    ('MAMEY_COMPLETE','FAIL',[],'VALIDATION OR PIPELINE FAILURE'),
    ('INCOMPLETE','UNKNOWN',[],'STATUS UNRESOLVED'),
])
def test_distinct_statuses(tmp_path,status,gate_status,findings,label):
    (tmp_path/'manifest.json').write_text(json.dumps({'strain_id':'DEMO','terminal_status':status}))
    (tmp_path/'manifest_short.json').write_text(json.dumps({'status':'MAMEY_COMPLETE'}))
    (tmp_path/'gate_validation.json').write_text(json.dumps({'status':gate_status,'gold_completeness':'JUDGMENT_PENDING','json_evidence_visibility':{'status':'ADVISORY_FINDINGS','findings':findings}}))
    text=write_open_me_first(tmp_path).read_text()
    assert label in text
    assert 'JUDGMENT_PENDING' in text
    assert gate_status in text and status in text
    assert 'your Claude session' not in text
    assert 'top chemistry' not in text
    for finding in findings: assert finding in text

@pytest.mark.parametrize('duplicate',[False,True])
def test_lead_identity_is_bound_to_one_full_source_record(tmp_path,duplicate):
    record={'bgc_id':'BGC001','contig':'NODE_FULL.1','antismash_region':'region003'}
    (tmp_path/'manifest.json').write_text(json.dumps({'strain_id':'DEMO','bgcs':[record]*(2 if duplicate else 1)}))
    (tmp_path/'manifest_short.json').write_text(json.dumps({'top_3_ab':[{'bgc_id':'BGC001','contig':'NODE_FULL.1','ab_score':40}]}))
    text=write_open_me_first(tmp_path).read_text()
    assert ('IDENTITY HOLD' if duplicate else 'DEMO / NODE_FULL.1 / region003 / BGC001') in text

def test_present_malformed_gate_is_not_hidden(tmp_path):
    (tmp_path/'gate_validation.json').write_text('{broken')
    with pytest.raises(ValueError,match='gate_validation.json'):
        write_open_me_first(tmp_path)


@pytest.mark.parametrize("recorded,log,count", [
    ([], "# Issue Log\n\n- A recorded warning.\n", 1),
    (["stale"], "# Issue Log\n\n- First warning.\n- Second warning.\n", 2),
    (["stale"], "# Issue Log\n\n- No blocking issues recorded.\n", 0),
    ([], "# Issue Log\n\n- No blocking issues recorded.\n- No blocking flag was available for this warning.\n", 1),
])
def test_entry_issue_count_uses_recorded_log(tmp_path, recorded, log, count):
    (tmp_path / "manifest.json").write_text(json.dumps({
        "strain_id": "PUBLIC-TEST", "terminal_status": "MAMEY_COMPLETE", "issues": recorded,
    }))
    (tmp_path / "issue_log.md").write_text(log)
    text = write_open_me_first(tmp_path).read_text()
    assert f"<td>Recorded pipeline issues</td><td>{count}</td>" in text
    assert ("EXTRACTION HAS ISSUES" in text) == bool(count)


@pytest.mark.parametrize("content", [b"\xff", b"# Issue Log\n", b""])
def test_present_unreadable_or_empty_issue_log_is_not_zero(tmp_path, content):
    (tmp_path / "issue_log.md").write_bytes(content)
    previous = tmp_path / "OPEN_ME_FIRST.html"
    previous.write_text("earlier entry")
    with pytest.raises(ValueError, match="issue_log.md"):
        write_open_me_first(tmp_path)
    assert previous.read_text() == "earlier entry"


def test_missing_issue_log_preserves_manifest_fallback(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"issues": ["recorded warning"]}))
    text = write_open_me_first(tmp_path).read_text()
    assert "<td>Recorded pipeline issues</td><td>1</td>" in text
