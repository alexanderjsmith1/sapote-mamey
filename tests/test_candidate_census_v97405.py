"""v9.7.405 — tools/candidate_census.py: file-count and debris census for a candidate cut tree.

Read-only, stdlib-only: counts total files plus four debris classes (`.pyc`, `__pycache__`,
`.pytest_cache`, `.DS_Store`) that must never ship in a sealed/composed candidate. Every case
builds a throwaway directory tree under tmp_path -- this file never touches the real bundle.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("candidate_census",
                                              ROOT / "tools" / "candidate_census.py")
cc = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(cc)


def _touch(path: Path, content: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_census_counts_total_files_with_no_debris(tmp_path):
    _touch(tmp_path / "a.py")
    _touch(tmp_path / "sub" / "b.py")
    _touch(tmp_path / "sub" / "c.md")
    report = cc.census(str(tmp_path))
    assert report["total_files"] == 3
    assert report["debris"] == {
        "pyc_files": 0, "pycache_dirs": 0, "pytest_cache_dirs": 0, "ds_store_files": 0, "root_run_outputs": 0,
    }
    assert report["debris_total"] == 0
    assert report["status"] == "CLEAN"


def test_census_finds_each_debris_class(tmp_path):
    _touch(tmp_path / "a.py")
    _touch(tmp_path / "__pycache__" / "a.cpython-312.pyc")
    _touch(tmp_path / "sub" / "__pycache__" / "b.cpython-312.pyc")
    _touch(tmp_path / ".pytest_cache" / "CACHEDIR.TAG")
    _touch(tmp_path / ".DS_Store")
    _touch(tmp_path / "sub" / ".DS_Store")
    report = cc.census(str(tmp_path))
    assert report["debris"]["pyc_files"] == 2
    assert report["debris"]["pycache_dirs"] == 2
    assert report["debris"]["pytest_cache_dirs"] == 1
    assert report["debris"]["ds_store_files"] == 2
    assert report["debris_total"] == 7
    assert report["status"] == "DEBRIS_FOUND"


def test_schema_version_and_root_are_present(tmp_path):
    _touch(tmp_path / "a.py")
    report = cc.census(str(tmp_path))
    assert report["schema_version"] == "sapote-candidate-census-1.0"
    assert report["root"] == str(tmp_path.resolve())


def test_census_fails_closed_when_walk_cannot_read_a_subtree(tmp_path, monkeypatch):
    """os.walk calls onerror for scandir failures; the gate must retain and fail that gap."""
    blocked = tmp_path / "blocked"

    def incomplete_walk(root, onerror=None):
        yield str(root), ["blocked"], ["visible.py"]
        assert onerror is not None
        onerror(PermissionError(13, "Permission denied", str(blocked)))

    monkeypatch.setattr(cc.os, "walk", incomplete_walk)
    report = cc.census(str(tmp_path))
    assert report["status"] == "INCOMPLETE"
    assert report["coverage_complete"] is False
    assert report["traversal_errors"] == [{
        "path": str(blocked.resolve()),
        "error_type": "PermissionError",
        "message": f"[Errno 13] Permission denied: '{blocked}'",
    }]
    assert report["debris_total"] == 0, "coverage failure is separate from debris"


# --- CLI ---------------------------------------------------------------------------------------


def test_cli_exits_zero_and_prints_json_receipt_when_clean(tmp_path, capsys):
    _touch(tmp_path / "a.py")
    rc = cc.main([str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0
    receipt = json.loads(out)
    assert receipt["status"] == "CLEAN"
    assert receipt["total_files"] == 1


def test_cli_exits_nonzero_when_debris_present(tmp_path, capsys):
    _touch(tmp_path / "a.py")
    _touch(tmp_path / ".DS_Store")
    rc = cc.main([str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 1
    receipt = json.loads(out)
    assert receipt["status"] == "DEBRIS_FOUND"
    assert receipt["debris"]["ds_store_files"] == 1


def test_cli_exits_nonzero_when_census_is_incomplete(tmp_path, monkeypatch, capsys):
    blocked = tmp_path / "blocked"

    def incomplete_walk(root, onerror=None):
        assert onerror is not None
        onerror(PermissionError(13, "Permission denied", str(blocked)))
        return iter(())

    monkeypatch.setattr(cc.os, "walk", incomplete_walk)
    rc = cc.main([str(tmp_path)])
    receipt = json.loads(capsys.readouterr().out)
    assert rc == 1
    assert receipt["status"] == "INCOMPLETE"
    assert receipt["coverage_complete"] is False


def test_cli_baseline_delta_is_reported_but_does_not_gate_exit(tmp_path, capsys):
    _touch(tmp_path / "a.py")
    _touch(tmp_path / "b.py")
    rc = cc.main([str(tmp_path), "--baseline", "10"])
    out = capsys.readouterr().out
    receipt = json.loads(out)
    assert rc == 0, "baseline mismatch alone must never trigger a non-zero exit"
    assert receipt["baseline"] == 10
    assert receipt["baseline_delta"] == -8


def test_cli_output_flag_writes_the_same_receipt_to_disk(tmp_path, capsys):
    _touch(tmp_path / "a.py")
    out_path = tmp_path / "receipt.json"
    rc = cc.main([str(tmp_path), "--output", str(out_path)])
    stdout_text = capsys.readouterr().out
    assert rc == 0
    assert out_path.is_file()
    assert json.loads(out_path.read_text(encoding="utf-8")) == json.loads(stdout_text)


def test_cli_refuses_a_nonexistent_directory(tmp_path, capsys):
    missing = tmp_path / "does_not_exist"
    rc = cc.main([str(missing)])
    assert rc == 2
    assert missing.name in capsys.readouterr().err


def test_never_mutates_or_deletes_anything(tmp_path):
    debris = tmp_path / "__pycache__" / "a.cpython-312.pyc"
    _touch(debris)
    before = debris.read_text(encoding="utf-8")
    cc.census(str(tmp_path))
    assert debris.is_file(), "census must never delete debris it finds"
    assert debris.read_text(encoding="utf-8") == before


def test_root_run_outputs_counted_at_root_only(tmp_path):
    """v9.7.408: cohort-assemble / cohort-leads default `--out` to a bare filename; two empty CSVs written
    at the bundle root shipped inside both sealed .407 zips. The census must count them at the ROOT and
    nowhere deeper (the same names under runs/ or tests/fixtures are legitimate)."""
    import importlib.util, sys
    spec = importlib.util.spec_from_file_location("candidate_census", ROOT / "tools" / "candidate_census.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    (tmp_path / "COHORT_MASTER.csv").write_text("strain\n", encoding="utf-8")
    deeper = tmp_path / "runs" / "x"; deeper.mkdir(parents=True)
    (deeper / "COHORT_PRIORITY_LEADS.csv").write_text("h\n", encoding="utf-8")
    report = mod.census(tmp_path) if hasattr(mod, "census") else mod.run_census(tmp_path)
    assert report["debris"]["root_run_outputs"] == 1
    assert report["status"] == "DEBRIS_FOUND"
