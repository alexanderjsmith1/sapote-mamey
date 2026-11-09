"""check_deliverable_suite --artifact-root: a COMPLETE artifact must be a regular file inside the root.

Before: `os.path.exists` admitted a directory, and a path that resolved outside the root.
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("cds_464r3", ROOT / "tools" / "check_deliverable_suite.py")
cds = importlib.util.module_from_spec(_spec)
sys.path.insert(0, str(ROOT / "tools"))
_spec.loader.exec_module(cds)


def _manifest(paths):
    rows = "\n".join(f"| {i} | item {i} | COMPLETE | {paths[i - 1]} |" for i in range(1, 14))
    return "| # | Deliverable | Status | Artifact (path) or Reason |\n|---|---|---|---|\n" + rows + "\n"


def test_directory_and_outside_paths_are_findings(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    for i in range(1, 12):
        (root / f"a{i}.md").write_text("x")
    (root / "a_folder").mkdir()
    (tmp_path / "outside.md").write_text("x")
    text = _manifest([f"a{i}.md" for i in range(1, 12)] + ["a_folder", "../outside.md"])
    findings, _ = cds.check(text, "standard", artifact_root=str(root))
    assert len(findings) == 2
    assert "a_folder" in findings[0] and "../outside.md" in findings[1]
    assert all("not a regular file inside" in f for f in findings)
