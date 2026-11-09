"""OPEN_ME_FIRST.html shows the same issue count and status as the sealed issue log.

The page was written during the package-addons phase, before late issues were added, so a run
with 2 issues showed "Recorded pipeline issues 1" and "MAMEY_COMPLETE". The pre-seal status
stamp now rebuilds the page.
"""
from __future__ import annotations

import inspect
import json

from mamey import cli
from mamey.cli import _stamp_terminal_status
from mamey.package_addons import write_open_me_first


def _package(tmp_path):
    (tmp_path / "manifest.json").write_text(json.dumps(
        {"strain_id": "EXAMPLE", "package_status": "MAMEY_COMPLETE"}), encoding="utf-8")
    (tmp_path / "issue_log.md").write_text("# Issue Log\n\n- MULTIBATCH: early\n", encoding="utf-8")
    write_open_me_first(tmp_path)
    page = (tmp_path / "OPEN_ME_FIRST.html").read_text(encoding="utf-8")
    assert "<td>Recorded pipeline issues</td><td>1</td>" in page
    return tmp_path


def test_preseal_stamp_rebuilds_the_entry_page(tmp_path):
    pkg = _package(tmp_path)
    _stamp_terminal_status(pkg, validator_status="MAMEY_COMPLETE",
                           issues=["MULTIBATCH: early", "OVER_MERGE_CANDIDATES: late"],
                           refresh_entry_page=True)
    page = (pkg / "OPEN_ME_FIRST.html").read_text(encoding="utf-8")
    assert "<td>Recorded pipeline issues</td><td>2</td>" in page
    assert "<td>Pipeline status</td><td>MAMEY_COMPLETE_WITH_ISSUES</td>" in page


def test_other_stamps_leave_the_checksummed_page_alone(tmp_path):
    pkg = _package(tmp_path)
    before = (pkg / "OPEN_ME_FIRST.html").read_bytes()
    _stamp_terminal_status(pkg, validator_status="MAMEY_COMPLETE",
                           issues=["MULTIBATCH: early", "OVER_MERGE_CANDIDATES: late"])
    assert (pkg / "OPEN_ME_FIRST.html").read_bytes() == before


def test_no_page_is_created_when_none_was_written(tmp_path):
    (tmp_path / "manifest.json").write_text("{}", encoding="utf-8")
    _stamp_terminal_status(tmp_path, validator_status="PASS", issues=["X"], refresh_entry_page=True)
    assert not (tmp_path / "OPEN_ME_FIRST.html").exists()


def test_the_run_refreshes_the_page_at_both_stamps_before_the_zip():
    source = inspect.getsource(cli)
    assert source.count("refresh_entry_page=True") == 2
    preseal = source.index("_preseal_terminal_status = _stamp_terminal_status(")
    assert "refresh_entry_page=True" in source[preseal:preseal + 200]
    late = source.index("including the entry page and its checksum line.")
    assert "refresh_entry_page=True" in source[late:late + 250]
    zip_call = source.index("zip_package(package_dir, zip_path)")
    assert late < zip_call


def test_a_late_issue_after_the_checksums_rebinds_the_page_hash(tmp_path):
    import hashlib
    pkg = _package(tmp_path)
    page = pkg / "OPEN_ME_FIRST.html"
    old = hashlib.sha256(page.read_bytes()).hexdigest()
    (pkg / "checksums_sha256.txt").write_text(f"{'0' * 64}  other.csv\n{old}  OPEN_ME_FIRST.html\n",
                                              encoding="utf-8")
    manifest = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    manifest["files"] = [{"path": "OPEN_ME_FIRST.html", "sha256": old, "bytes": page.stat().st_size}]
    (pkg / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    _stamp_terminal_status(pkg, validator_status="MAMEY_COMPLETE",
                           issues=["MULTIBATCH: early", "OVER_MERGE_CANDIDATES: late",
                                   "[WARN] enrichment files missing before seal: late"],
                           refresh_entry_page=True)
    text = page.read_text(encoding="utf-8")
    assert "<td>Recorded pipeline issues</td><td>3</td>" in text
    new = hashlib.sha256(page.read_bytes()).hexdigest()
    assert new != old
    sums = (pkg / "checksums_sha256.txt").read_text(encoding="utf-8").splitlines()
    assert sums == [f"{'0' * 64}  other.csv", f"{new}  OPEN_ME_FIRST.html"]
    entry = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))["files"][0]
    assert entry == {"path": "OPEN_ME_FIRST.html", "sha256": new, "bytes": page.stat().st_size}


def test_the_page_says_its_count_is_as_sealed(tmp_path):
    text = (_package(tmp_path) / "OPEN_ME_FIRST.html").read_text(encoding="utf-8")
    assert "as sealed" in text and "terminal_status" in text


def test_a_late_issue_rebinds_the_commit_receipt_hash_too(tmp_path):
    import hashlib
    pkg = _package(tmp_path)
    receipt = pkg / "commit_receipt.json"
    receipt.write_text(json.dumps({"status": "PASS", "issues": []}), encoding="utf-8")
    old = hashlib.sha256(receipt.read_bytes()).hexdigest()
    (pkg / "checksums_sha256.txt").write_text(f"{old}  commit_receipt.json\n", encoding="utf-8")
    _stamp_terminal_status(pkg, validator_status="MAMEY_COMPLETE", issues=["LATE: x"],
                           refresh_entry_page=True)
    new = hashlib.sha256(receipt.read_bytes()).hexdigest()
    assert new != old
    assert (pkg / "checksums_sha256.txt").read_text(encoding="utf-8") == f"{new}  commit_receipt.json\n"


def test_stamps_without_the_flag_do_not_touch_the_checksums(tmp_path):
    pkg = _package(tmp_path)
    (pkg / "checksums_sha256.txt").write_text(f"{'0' * 64}  OPEN_ME_FIRST.html\n", encoding="utf-8")
    _stamp_terminal_status(pkg, validator_status="MAMEY_COMPLETE", issues=["LATE: x"])
    assert (pkg / "checksums_sha256.txt").read_text(encoding="utf-8") == f"{'0' * 64}  OPEN_ME_FIRST.html\n"


def _report(pkg, issues):
    from mamey.compile_report import render_run_level_issues
    text = ("# 3. Earlier\n\nx\n\n# 4. Assembly and strain summary\n\n| Field | Value |\n|---|---|\n"
            "| Taxonomy | t |\n" + render_run_level_issues(issues) + "\n# 5. Next section\n\ny\n")
    (pkg / "EXAMPLE_compiled_report.md").write_text(text, encoding="utf-8")


def test_the_compiled_report_issue_list_is_refreshed_and_rebound(tmp_path):
    import hashlib
    pkg = _package(tmp_path)
    _report(pkg, ["MULTIBATCH: early"])
    report = pkg / "EXAMPLE_compiled_report.md"
    old = hashlib.sha256(report.read_bytes()).hexdigest()
    (pkg / "checksums_sha256.txt").write_text(f"{old}  EXAMPLE_compiled_report.md\n", encoding="utf-8")
    _stamp_terminal_status(pkg, validator_status="MAMEY_COMPLETE",
                           issues=["MULTIBATCH: early", "OVER_MERGE_CANDIDATES: late"],
                           refresh_entry_page=True)
    text = report.read_text(encoding="utf-8")
    assert "- OVER_MERGE_CANDIDATES: late" in text and text.count("**Run-level issues**") == 1
    assert "# 5. Next section" in text and "# 3. Earlier" in text
    new = hashlib.sha256(report.read_bytes()).hexdigest()
    assert (pkg / "checksums_sha256.txt").read_text(encoding="utf-8") == f"{new}  EXAMPLE_compiled_report.md\n"


def test_a_report_built_with_no_issues_gets_the_block_added(tmp_path):
    pkg = _package(tmp_path)
    _report(pkg, [])
    _stamp_terminal_status(pkg, validator_status="MAMEY_COMPLETE", issues=["LATE: x"],
                           refresh_entry_page=True)
    text = (pkg / "EXAMPLE_compiled_report.md").read_text(encoding="utf-8")
    assert "- LATE: x" in text
    assert text.index("- LATE: x") < text.index("# 5. Next section")


def test_the_stamp_after_the_zip_leaves_the_checksummed_receipt_alone(tmp_path):
    pkg = _package(tmp_path)
    receipt = pkg / "commit_receipt.json"
    receipt.write_text(json.dumps({"status": "PASS", "issues": ["MULTIBATCH: early"]}), encoding="utf-8")
    before = receipt.read_bytes()
    _stamp_terminal_status(pkg, validator_status="MAMEY_COMPLETE",
                           issues=["MULTIBATCH: early", "POST_ZIP: late"], after_zip=True)
    assert receipt.read_bytes() == before
    manifest = json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["issue_count"] == 2
    assert "- POST_ZIP: late" in (pkg / "issue_log.md").read_text(encoding="utf-8")


def test_a_refresh_failure_is_raised_as_an_issue(tmp_path, monkeypatch):
    import mamey.package_addons as addons
    pkg = _package(tmp_path)
    def boom(_pkg):
        raise RuntimeError("page writer failed")
    monkeypatch.setattr(addons, "write_open_me_first", boom)
    issues = ["MULTIBATCH: early"]
    status = _stamp_terminal_status(pkg, validator_status="MAMEY_COMPLETE", issues=issues,
                                    refresh_entry_page=True)
    assert any(i.startswith("[WARN] STATUS_SURFACE_REFRESH_FAILED") for i in issues)
    assert status == "MAMEY_COMPLETE_WITH_ISSUES"
    assert "STATUS_SURFACE_REFRESH_FAILED" in (pkg / "issue_log.md").read_text(encoding="utf-8")
    assert json.loads((pkg / "manifest.json").read_text(encoding="utf-8"))["issue_count"] == 2


def test_the_final_stamp_in_the_run_is_the_after_zip_one():
    source = inspect.getsource(cli)
    assert "_stamp_terminal_status(package_dir, validator_status=status, issues=issues, after_zip=True)" in source
