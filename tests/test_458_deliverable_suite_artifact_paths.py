"""check_deliverable_suite can check that COMPLETE artifact paths exist, and says when it did not.

A COMPLETE row needed only a non-empty artifact cell; the path was never looked for, so a
manifest naming files that were never written passed the release gate.
"""
import importlib.util
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "check_deliverable_suite.py"
_spec = importlib.util.spec_from_file_location("check_deliverable_suite_458", TOOL)
cds = importlib.util.module_from_spec(_spec)
sys.path.insert(0, str(ROOT / "tools"))
_spec.loader.exec_module(cds)


def _manifest(paths):
    rows = "\n".join(f"| {i} | item {i} | COMPLETE | {paths[i - 1]} |" for i in range(1, 14))
    return "| # | Deliverable | Status | Artifact (path) or Reason |\n|---|---|---|---|\n" + rows + "\n"


def test_missing_artifact_is_a_finding_when_root_given(tmp_path):
    for i in range(1, 13):
        (tmp_path / f"a{i}.md").write_text("x")
    text = _manifest([f"a{i}.md" for i in range(1, 13)] + ["never_written.md"])
    findings, _ = cds.check(text, "standard", artifact_root=str(tmp_path))
    assert len(findings) == 1 and "never_written.md" in findings[0] and "item 13" in findings[0]


def test_all_present_passes(tmp_path):
    for i in range(1, 14):
        (tmp_path / f"a{i}.md").write_text("x")
    findings, _ = cds.check(_manifest([f"a{i}.md" for i in range(1, 14)]), "standard", artifact_root=str(tmp_path))
    assert findings == []


def test_without_root_the_printout_says_paths_were_not_checked(tmp_path):
    m = tmp_path / "DELIVERABLE_MANIFEST_X.md"
    m.write_text(_manifest([f"a{i}.md" for i in range(1, 14)]))
    out = subprocess.run([sys.executable, str(TOOL), "--manifest", str(m)], capture_output=True, text=True).stdout
    assert "PASS" in out and "not checked on disk" in out
