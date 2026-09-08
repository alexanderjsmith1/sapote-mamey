"""F10: tools/seal_sweep.py — seal-time sweep for stale prose and stale START_HERE version
citations. All fixtures below are synthetic (tmp_path); no real bundle rows are embedded here.
One live smoke test runs the sweep against this actual tree's own root without asserting on
specific findings (the tree's doc surface changes over time) -- it only proves the sweep runs
clean-of-crashes against real files, mirroring how tests/test_gate_wiring_invariant.py exercises
itself against ROOT directly.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import seal_sweep  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _write_bundle(tmp_path, *, changelog, start_here_files, build_stamp_version="9.7.406",
                   extra_docs=None):
    (tmp_path / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
    (tmp_path / "BUILD_STAMP.txt").write_text(f"version={build_stamp_version}\nbuild=x\n",
                                                encoding="utf-8")
    for name, text in start_here_files.items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    for name, text in (extra_docs or {}).items():
        (tmp_path / name).write_text(text, encoding="utf-8")
    return tmp_path


def test_newest_changelog_entry_bounding_matches_f6():
    """F6's own bounding contract, reused: historical entries are never scanned."""
    text = "# v9.7.406 · current\ncurrent prose\n\n# v9.7.405 · history\nhistorical prose\n"
    entry = seal_sweep.newest_changelog_entry(text)
    assert "current prose" in entry
    assert "historical prose" not in entry


def test_malformed_changelog_fails_closed_as_a_finding(tmp_path):
    bundle = _write_bundle(tmp_path, changelog="preface with no header\n", start_here_files={})
    findings = seal_sweep.sweep_changelog(bundle)
    assert findings == [{
        "path": "CHANGELOG.md", "code": "MALFORMED_CHANGELOG",
        "detail": "CHANGELOG must start with a versioned '# vX.Y.Z' entry",
    }]


def test_sweep_changelog_detects_banned_phrase_in_newest_entry_only(tmp_path):
    bundle = _write_bundle(
        tmp_path,
        changelog=("# v9.7.406 · current\nTO BE FILLED\n\n"
                    "# v9.7.405 · history\nCANDIDATE — not a seal\n"),
        start_here_files={},
    )
    findings = seal_sweep.sweep_changelog(bundle)
    assert findings == [{
        "path": "CHANGELOG.md", "code": "BANNED_PHRASE",
        "detail": "newest entry contains 'TO BE FILLED'",
    }]


def test_sweep_changelog_clean_when_newest_entry_has_no_banned_phrase(tmp_path):
    bundle = _write_bundle(
        tmp_path,
        changelog="# v9.7.406 · current\nseal-ready prose\n\n# v9.7.405 · history\nTO BE FILLED\n",
        start_here_files={},
    )
    assert seal_sweep.sweep_changelog(bundle) == []


def test_sweep_doc_surface_detects_banned_phrase_in_readme_and_start_here(tmp_path):
    bundle = _write_bundle(
        tmp_path,
        changelog="# v9.7.406 · current\nclean\n",
        start_here_files={"CLAUDE_START_HERE.md": "read this — absent by defined-symbol\n"},
        extra_docs={"README.md": "PENDING, not yet in this tree\n"},
    )
    findings = sorted(seal_sweep.sweep_doc_surface(bundle), key=lambda f: f["path"])
    assert findings == [
        {"path": "CLAUDE_START_HERE.md", "code": "BANNED_PHRASE",
         "detail": "contains 'absent by defined-symbol'"},
        {"path": "README.md", "code": "BANNED_PHRASE",
         "detail": "contains 'PENDING, not yet in this tree'"},
    ]


def test_sweep_doc_surface_clean_tree_has_no_findings(tmp_path):
    bundle = _write_bundle(
        tmp_path,
        changelog="# v9.7.406 · current\nclean\n",
        start_here_files={"CLAUDE_START_HERE.md": "current bundle: v9.7.406, all clear\n"},
        extra_docs={"README.md": "nothing banned here\n",
                    "CURRENT_DOCS_INDEX.md": "index, nothing banned\n"},
    )
    assert seal_sweep.sweep_doc_surface(bundle) == []


def test_sweep_start_here_version_citation_flags_missing_citation(tmp_path):
    bundle = _write_bundle(
        tmp_path,
        changelog="# v9.7.406 · current\nclean\n",
        start_here_files={
            "CLAUDE_START_HERE.md": "current bundle: v9.7.406\n",
            "FIGURES_START_HERE.md": "no version line in here at all\n",
        },
        build_stamp_version="9.7.406",
    )
    findings = seal_sweep.sweep_start_here_version_citation(bundle)
    assert findings == [{
        "path": "FIGURES_START_HERE.md", "code": "VERSION_STALE",
        "detail": "does not cite current version '9.7.406' (from BUILD_STAMP.txt)",
    }]


def test_sweep_start_here_version_citation_missing_build_stamp(tmp_path):
    tmp_path.joinpath("SOMETHING_START_HERE.md").write_text("x", encoding="utf-8")
    findings = seal_sweep.sweep_start_here_version_citation(tmp_path)
    assert findings == [{
        "path": "BUILD_STAMP.txt", "code": "MISSING_BUILD_STAMP",
        "detail": "no BUILD_STAMP.txt / no version= line at bundle root; cannot check citation",
    }]


def test_run_sweep_clean_bundle_has_no_findings(tmp_path):
    bundle = _write_bundle(
        tmp_path,
        changelog="# v9.7.406 · current\nseal-ready\n",
        start_here_files={"CLAUDE_START_HERE.md": "current bundle: v9.7.406\n"},
        extra_docs={"README.md": "clean\n"},
        build_stamp_version="9.7.406",
    )
    assert seal_sweep.run_sweep(bundle) == []


def test_run_sweep_dirty_bundle_reports_every_check_family(tmp_path):
    bundle = _write_bundle(
        tmp_path,
        changelog="# v9.7.406 · current\nTO BE FILLED\n",
        start_here_files={"CLAUDE_START_HERE.md": "no citation here\n"},
        extra_docs={"README.md": "PENDING, not yet in this tree\n"},
        build_stamp_version="9.7.406",
    )
    findings = seal_sweep.run_sweep(bundle)
    codes = {f["code"] for f in findings}
    assert codes == {"BANNED_PHRASE", "VERSION_STALE"}
    assert len(findings) == 3  # changelog phrase + readme phrase + stale start-here citation


def test_check_flag_flips_exit_code_only(tmp_path):
    """--check changes only the exit code; findings are printed identically either way."""
    bundle = _write_bundle(
        tmp_path,
        changelog="# v9.7.406 · current\nTO BE FILLED\n",
        start_here_files={"CLAUDE_START_HERE.md": "current bundle: v9.7.406\n"},
        build_stamp_version="9.7.406",
    )
    tool = ROOT / "tools" / "seal_sweep.py"

    report = subprocess.run([sys.executable, str(tool), "--root", str(bundle)],
                             capture_output=True, text=True)
    checked = subprocess.run([sys.executable, str(tool), "--root", str(bundle), "--check"],
                              capture_output=True, text=True)

    assert report.returncode == 0
    assert checked.returncode == 1
    assert report.stdout == checked.stdout
    assert "BANNED_PHRASE" in report.stdout


def test_json_output_round_trips_findings(tmp_path):
    bundle = _write_bundle(
        tmp_path,
        changelog="# v9.7.406 · current\nTO BE FILLED\n",
        start_here_files={},
        build_stamp_version="9.7.406",
    )
    tool = ROOT / "tools" / "seal_sweep.py"
    result = subprocess.run([sys.executable, str(tool), "--root", str(bundle), "--json"],
                             capture_output=True, text=True)
    findings = json.loads(result.stdout)
    assert findings == [{"path": "CHANGELOG.md", "code": "BANNED_PHRASE",
                          "detail": "newest entry contains 'TO BE FILLED'"}]


def test_clean_report_says_clean(tmp_path):
    bundle = _write_bundle(
        tmp_path,
        changelog="# v9.7.406 · current\nseal-ready\n",
        start_here_files={"CLAUDE_START_HERE.md": "current bundle: v9.7.406\n"},
        build_stamp_version="9.7.406",
    )
    tool = ROOT / "tools" / "seal_sweep.py"
    result = subprocess.run([sys.executable, str(tool), "--root", str(bundle), "--check"],
                             capture_output=True, text=True)
    assert result.returncode == 0
    assert "clean" in result.stdout


def test_live_tree_sweep_runs_without_crashing():
    """Smoke coverage against this tree's own real root (mirrors how
    tests/test_gate_wiring_invariant.py exercises ROOT directly). Deliberately does not assert on
    specific findings -- the doc surface changes over time and a stale hardcoded expectation would
    itself be the kind of drift this sweep exists to catch."""
    findings = seal_sweep.run_sweep(ROOT)
    assert isinstance(findings, list)
    for f in findings:
        assert set(f) == {"path", "code", "detail"}
