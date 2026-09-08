"""BLAST-P02/P03/P06 (v9.7.325): the last unguarded doors in the BLASTp family degrade to empty
instead of crashing ingest on an NCBI HTML/QBlastInfo error stub (the two-writer clobber class) or
a harvest-before-submit state.
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))
from mamey.blastp_followup import parse_xml2, parse_hit_table_csv
from mamey.blastp_ebi import harvest_ebi

_HTML_STUB = "<!DOCTYPE html><html><body>QBlastInfo error: CPU usage limit exceeded</body></html>"
_QBLAST_STUB = "\n<p><!--\nQBlastInfoBegin\n\tStatus=FAILED\nQBlastInfoEnd\n--></p>\n"


def test_parse_xml2_returns_empty_on_html_stub(tmp_path):
    p = tmp_path / "r.xml"; p.write_text(_HTML_STUB, encoding="utf-8")
    assert parse_xml2(p) == {}


def test_parse_xml2_returns_empty_on_qblast_stub(tmp_path):
    p = tmp_path / "r.xml"; p.write_text(_QBLAST_STUB, encoding="utf-8")
    assert parse_xml2(p) == {}


def test_parse_xml2_returns_empty_on_truncated_xml(tmp_path):
    p = tmp_path / "r.xml"; p.write_text('<?xml version="1.0"?><BlastOutput2><Repo', encoding="utf-8")
    assert parse_xml2(p) == {}


def test_parse_hit_table_csv_returns_empty_on_stub(tmp_path):
    p = tmp_path / "ht.csv"; p.write_text(_HTML_STUB, encoding="utf-8")
    assert parse_hit_table_csv(p) == []


def test_harvest_ebi_no_crash_on_missing_state(tmp_path):
    # harvest before submit: state file absent -> _load returns {} -> must not KeyError
    state = str(tmp_path / "nope.json")
    out = harvest_ebi(state, poll_budget=0)
    assert isinstance(out, dict)


def test_harvest_ebi_no_crash_on_empty_jobs(tmp_path):
    state = tmp_path / "s.json"; state.write_text(json.dumps({"jobs": {}, "results": {}}), encoding="utf-8")
    out = harvest_ebi(str(state), poll_budget=0)
    assert isinstance(out, dict)
