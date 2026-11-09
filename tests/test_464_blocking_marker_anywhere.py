"""The run exit gate and the issue registry share one rule: [BLOCKING] anywhere in an issue fails the run."""
from argparse import Namespace

import pytest

from mamey import cli
from mamey.issue_registry import issue_severity


def _args(tmp_path):
    return Namespace(chatgpt_safe=True, chatgpt_followup=True, mode="gold", brief="standard",
                     json_evidence="bounded", require_workbook=False, locus_maps="auto", heartbeat_seconds=20,
                     strains=None, strain="TEST", input_zip="missing.zip", outdir=str(tmp_path), master=None,
                     taxonomy=None, source=None, bioactivity=None, bioactivity_json=None,
                     antismash_profile="unknown", release=None, metadata_csv=None, token_budget="standard",
                     display_name=None)


@pytest.mark.parametrize("issue", [
    "[BLOCKING] sealed receipt mismatch",
    "phase: [BLOCKING] synthetic refused evidence",
    "  [blocking] lower-case marker after whitespace",
    "BLOCKING: bare marker at the start",
])
def test_blocking_marker_fails_the_run(monkeypatch, tmp_path, issue):
    assert issue_severity(issue) == "BLOCKING"
    monkeypatch.setattr(cli, "run_one_strain", lambda **kw: {
        "strain_id": "TEST", "status": "MAMEY_COMPLETE_WITH_ISSUES", "validator_status": "PASS", "issues": [issue]})
    assert cli.run_command(_args(tmp_path)) == 1


@pytest.mark.parametrize("issue", ["[WARN] enrichment files missing", "note: a non-blocking remark"])
def test_non_blocking_issue_keeps_exit_zero(monkeypatch, tmp_path, issue):
    assert issue_severity(issue) != "BLOCKING"
    monkeypatch.setattr(cli, "run_one_strain", lambda **kw: {
        "strain_id": "TEST", "status": "MAMEY_COMPLETE_WITH_ISSUES", "validator_status": "PASS", "issues": [issue]})
    assert cli.run_command(_args(tmp_path)) == 0
