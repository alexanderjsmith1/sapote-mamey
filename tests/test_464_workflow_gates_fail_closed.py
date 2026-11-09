"""W8 checks the deliverable manifest it found; W9 fails closed on an unreadable package manifest."""
import json
import os

from mamey import sapote_workflow as wf


def _suite_manifest(path, rows_filled):
    rows = "\n".join(f"| {i} | item {i} | {'N/A' if rows_filled else 'COMPLETE/SKIPPED/N/A'} | reason {i} |"
                     for i in range(1, 14))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# manifest\n\ngold_completeness: COMPLETE\nMode B cards written: 3/3\n\n"
                 "| # | item | status | artifact |\n|---|---|---|---|\n" + rows + "\n")


def test_w8_reads_the_deliverable_manifest_not_the_package_manifest(tmp_path):
    pkg, deliv = tmp_path / "package", tmp_path / "deliverables"
    pkg.mkdir(); deliv.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain": "EXAMPLE"}))
    _suite_manifest(deliv / "DELIVERABLE_MANIFEST_EXAMPLE.md", rows_filled=True)
    status, receipt = wf.s8_suite(str(pkg), str(deliv), {})
    # A filled suite manifest passes; reading manifest.json instead found no rows and failed.
    assert status == wf.PASS and "rc=0" in receipt, receipt


def test_w8_unfilled_deliverable_manifest_is_pending(tmp_path):
    pkg, deliv = tmp_path / "package", tmp_path / "deliverables"
    pkg.mkdir(); deliv.mkdir()
    (pkg / "manifest.json").write_text(json.dumps({"strain": "EXAMPLE"}))
    _suite_manifest(deliv / "DELIVERABLE_MANIFEST_EXAMPLE.md", rows_filled=False)
    assert wf.s8_suite(str(pkg), str(deliv), {})[0] == wf.PENDING


def test_w9_missing_manifest_is_not_pass(tmp_path):
    status, receipt = wf.s9_receipt(str(tmp_path), None, {})
    assert status == wf.PENDING and "missing or unreadable" in receipt


def test_w9_unreadable_manifest_is_not_pass(tmp_path):
    (tmp_path / "manifest.json").write_text("{not json")
    assert wf.s9_receipt(str(tmp_path), None, {})[0] == wf.PENDING


def test_w9_cleared_manifest_still_passes(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps({"gold_completeness": "COMPLETE"}))
    assert wf.s9_receipt(str(tmp_path), None, {})[0] == wf.PASS
