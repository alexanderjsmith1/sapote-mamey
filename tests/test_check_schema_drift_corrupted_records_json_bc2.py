"""BC2-SD-01 (v9.7.395): check_schema_drift.py's _records() must not silently degrade coverage
when a source's *_records.json exists but fails to parse.

_records() prefers *_records.json (the richer, more-authoritative BGC record source) over the
manifest's own (possibly thinner) "bgcs" list. It used to `except Exception: pass` on a parse
failure and silently fall back to manifest.bgcs with zero signal — so a corrupted/truncated
records.json degraded the primary-key-uniqueness (#4) and KCB-provenance (#5) checks to whatever
subset the thinner manifest happened to carry. This gate's own docstring says it is
"Fail-closed: exits non-zero the moment two sources disagree" — but with the bug, a real
un-provenanced KCB claim visible only in the corrupted records.json went completely unreported,
and the tool printed "no drift — safe to merge" and exited 0.

Reproduced live against the unpatched tools/check_schema_drift.py before this fix.
"""
import json
import os
import subprocess
import sys

TOOL = os.path.join(os.path.dirname(__file__), "..", "tools", "check_schema_drift.py")


def _mk_pkg(tmp_path, name, manifest_bgcs, records_json_text=None):
    d = tmp_path / name / "package"
    d.mkdir(parents=True)
    man = {"strain_id": name, "workflow_version": "9.7.24", "bgc_counts": {}, "bgcs": manifest_bgcs}
    (d / "manifest.json").write_text(json.dumps(man))
    if records_json_text is not None:
        (d / f"{name}_records.json").write_text(records_json_text)
    return str(d)


def _run(*pkgs):
    return subprocess.run([sys.executable, TOOL, "--packages", *pkgs], capture_output=True, text=True)


def test_corrupted_records_json_is_surfaced_and_fails_closed(tmp_path):
    # manifest.bgcs alone is clean (one record, no KCB claim); the corrupted records.json — if it
    # parsed — would reveal a genuine un-provenanced KCB claim on a second BGC.
    corrupted = (
        '{"records": [{"bgc_id": "BGC001", "kcb_top": ""}, '
        '{"bgc_id": "BGC002", "kcb_top": "colibactin-like similarity, no accession"}]}\n'
        "CORRUPTED_TRAILING_GARBAGE{{{"
    )
    pkg = _mk_pkg(tmp_path, "AS-1", [{"bgc_id": "BGC001", "kcb_top": ""}], records_json_text=corrupted)
    r = _run(pkg)
    assert "records.json integrity" in r.stdout, (
        f"a corrupted records.json must be surfaced as a visible finding; got: {r.stdout!r}"
    )
    assert "UNREADABLE" in r.stdout
    assert r.returncode == 1, (
        f"a corrupted records.json must fail this fail-closed gate, not report a clean pass; "
        f"stdout={r.stdout!r}"
    )


def test_valid_records_json_still_passes_cleanly(tmp_path):
    valid = '{"records": [{"bgc_id": "BGC003", "kcb_top": "BGC0002460.3 | loonamycin"}]}'
    pkg = _mk_pkg(tmp_path, "AS-2", [], records_json_text=valid)
    r = _run(pkg)
    assert "records.json integrity" not in r.stdout
    assert r.returncode == 0
    assert "no drift" in r.stdout


def test_no_records_json_still_passes_cleanly(tmp_path):
    # Regression guard: the ordinary case (no records.json at all, manifest.bgcs used directly)
    # must remain completely unaffected.
    pkg = _mk_pkg(tmp_path, "AS-3", [{"bgc_id": "BGC004", "kcb_top": "BGC0002460.3 | loonamycin"}])
    r = _run(pkg)
    assert "records.json integrity" not in r.stdout
    assert r.returncode == 0
