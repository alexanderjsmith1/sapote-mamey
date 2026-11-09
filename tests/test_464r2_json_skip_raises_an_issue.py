"""A JSON skipped by the evidence parser is raised as a run issue.

`run --json-evidence full` on a JSON over 80,000,000 bytes exited 0 with the skip recorded only
in the parse JSON, the manifest and the gate file. Issues go to issue_log.md and print as one
[ISSUE] line at the end of the run.
"""
from __future__ import annotations

import inspect

from mamey import cli
from mamey.cli import _json_skip_issues


def test_each_skipped_json_becomes_one_issue():
    evidence = {"json_skipped": [
        "a.json: 97,635,604 bytes exceeds full-mode cap (80,000,000); use --json-evidence bounded or off",
        "b.json: 300,000,000 bytes exceeds bounded cap (250,000,000)",
    ]}
    issues = _json_skip_issues(evidence)
    assert len(issues) == 2
    assert issues[0].startswith("JSON_EVIDENCE_SKIPPED: a.json: 97,635,604 bytes exceeds full-mode cap")
    assert "b.json" in issues[1]


def test_no_skip_no_issue():
    assert _json_skip_issues({"json_skipped": []}) == []
    assert _json_skip_issues({}) == []
    assert _json_skip_issues(None) == []


def test_the_run_adds_the_skip_issues_before_the_package_is_written():
    source = inspect.getsource(cli.run_one_strain) if hasattr(cli, "run_one_strain") else inspect.getsource(cli)
    assert "issues.extend(_json_skip_issues(antismash_evidence))" in source


def test_the_full_mode_cap_writes_a_skip_entry(monkeypatch):
    import io
    import zipfile
    from mamey import antismash_evidence as ae
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("x.json", "{}")
    buf.seek(0)
    monkeypatch.setattr(ae, "FULL_MAX_JSON_BYTES", 1)
    evidence = {}
    with zipfile.ZipFile(buf) as zf:
        ae._parse_json_full(zf, "x.json", evidence)
    assert _json_skip_issues(evidence)[0].startswith("JSON_EVIDENCE_SKIPPED: x.json: 2 bytes")


def _evidence(skipped, record_status=None, txt=("knownclusterblast/region1/c1_mibig_hits.txt",)):
    ev = {"json_skipped": skipped, "txt_files": list(txt)}
    if record_status is not None:
        ev["record_extraction"] = {"files": [{"source": "a.json", "status": record_status}]}
    return ev


def test_text_reports_the_record_pass_status_it_actually_had():
    entry = "a.json: 97,635,604 bytes exceeds full-mode cap (80,000,000); use --json-evidence bounded or off"
    read = _json_skip_issues(_evidence([entry], "READ_COMPLETE"))[0]
    assert "the record pass read it" in read and "1 KnownClusterBlast TXT file(s) were still read" in read
    held = _json_skip_issues(_evidence([entry], "HELD_SIZE_CAP"))[0]
    assert "record pass status for it is HELD_SIZE_CAP" in held
    assert "record pass read it" not in held


def test_text_says_when_no_kcb_txt_was_there_to_read():
    entry = "a.json: 2 bytes exceeds full-mode cap (1); use --json-evidence bounded or off"
    text = _json_skip_issues(_evidence([entry], "READ_COMPLETE", txt=("clusterblast/region1/c1.txt",)))[0]
    assert "no KnownClusterBlast TXT file was found to read instead" in text


def test_the_no_ijson_entry_is_worded_on_its_own():
    entry = ("bounded mode requested but ijson is not installed; fell back to off. "
             "Install ijson for streaming JSON evidence.")
    text = _json_skip_issues(_evidence([entry]))[0]
    assert "for this file" not in text and "this file" not in text
    assert "No JSON file was walked by the main walker" in text
