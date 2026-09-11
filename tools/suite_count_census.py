#!/usr/bin/env python3
"""Measure pytest collection separately from JUnit execution outcomes.

Collection uses configured testpaths unless --tests is supplied. This command never runs
an execution suite implicitly. An optional JUnit report supplies observed outcomes; skipped
cases remain skips, not deselections. Outputs are additive and do not alter a baseline.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
_WORKER = r'''
import json, sys, pytest
from pathlib import Path
_original_importorskip = pytest.importorskip
_collection_gating_deps = {}
def _recording_importorskip(modname, *args, **kwargs):
    try:
        module = _original_importorskip(modname, *args, **kwargs)
    except pytest.skip.Exception:
        _collection_gating_deps[modname] = False
        raise
    _collection_gating_deps[modname] = _collection_gating_deps.get(modname, True) and True
    return module
pytest.importorskip = _recording_importorskip
class Census:
    def __init__(self):
        self.deselected = []; self.errors = []; self.collection_skips = []
    def pytest_deselected(self, items):
        self.deselected.extend(x.nodeid for x in items)
    def pytest_collectreport(self, report):
        if report.failed: self.errors.append(report.nodeid)
        if report.skipped: self.collection_skips.append(report.nodeid)
    def pytest_collection_finish(self, session):
        self.selected = [x.nodeid for x in session.items]
        self.marked_skip = [x.nodeid for x in session.items if x.get_closest_marker('skip')]
c = Census()
rc = pytest.main([*sys.argv[2:], '--collect-only', '-q', '-p', 'no:cacheprovider'], plugins=[c])
Path(sys.argv[1]).write_text(json.dumps(dict(exit_code=int(rc), selected=getattr(c,'selected',[]),
    deselected=c.deselected, marked_skip=getattr(c,'marked_skip',[]),
    collection_errors=c.errors, collection_skips=c.collection_skips,
    collection_gating_deps=_collection_gating_deps)))
raise SystemExit(rc)
'''


def environment_fingerprint(collection_gating_deps=None):
    """Record collection-process provisioning; this does not describe an imported JUnit run."""
    cwd = Path.cwd().resolve()
    here = Path(__file__).resolve().parent
    env = {"official_data_reachable": False, "official_data_root": None}
    for root in [cwd, *cwd.parents, here, *here.parents]:
        marker = root / "OFFICIAL_DATA"
        if marker.is_dir():
            env = {"official_data_reachable": True, "official_data_root": str(root)}
            break
    env["collection_gating_deps"] = dict(sorted((collection_gating_deps or {}).items()))
    return env


def census(scopes=None):
    with tempfile.TemporaryDirectory(prefix="suite-census-") as td:
        path = Path(td) / "collection.json"
        result = subprocess.run([sys.executable, "-B", "-c", _WORKER, str(path), *(scopes or [])],
                                cwd=ROOT, capture_output=True, text=True)
        # Pytest exit 5 is a valid census result when every requested module is
        # collection-skipped; the worker still writes the measured empty set.
        if result.returncode not in (0, 5) or not path.is_file():
            raise ValueError("CENSUS_COLLECTION_FAILED: " + (result.stdout + result.stderr)[-2000:])
        raw = json.loads(path.read_text())
    selected = sorted(raw["selected"]); deselected = sorted(raw["deselected"])
    return {"schema": "suite-count-census-v2", "scopes": scopes or "configured_testpaths",
            "collected": len(selected) + len(deselected), "selected": len(selected),
            "deselected": len(deselected), "marked_skip": len(raw["marked_skip"]),
            "collection_skips": raw["collection_skips"], "collection_errors": raw["collection_errors"],
            "selected_nodeids": selected, "deselected_nodeids": deselected,
            "environment": environment_fingerprint(raw.get("collection_gating_deps")),
            "environment_scope": "collection_process_only",
            "execution": None}


def read_junit(path):
    path = Path(path); data = path.read_bytes(); root = ET.fromstring(data)
    counts = collections.Counter()
    cases = []
    for case in root.iter("testcase"):
        status = next((kind for kind in ("error", "failure", "skipped") if case.find(kind) is not None), "passed")
        counts[status] += 1
        cases.append([case.get("classname", ""), case.get("name", ""), status])
    if not counts:
        raise ValueError("CENSUS_JUNIT_EMPTY")
    return {"sha256": hashlib.sha256(data).hexdigest(), "testcase_outcomes": dict(counts), "testcases": sorted(cases),
            "execution_environment": "UNBOUND_IMPORTED_JUNIT",
            "note": "JUnit testcase counts; subtests follow the producer's JUnit representation"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tests", action="append", help="Explicit scope; repeatable; default configured testpaths")
    ap.add_argument("--junit", help="Existing execution JUnit XML; does not run tests")
    ap.add_argument("--against", help="Previous census JSON with the same schema and scope")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--out", help="New output file; existing outputs are refused")
    a = ap.parse_args(argv)
    if a.write and not a.out:
        ap.error("--write requires --out")
    try:
        now = census(a.tests)
        if a.junit:
            now["execution"] = read_junit(a.junit)
        removed = []
        concerns = []
        if a.against:
            prev = json.loads(Path(a.against).read_text())
            if prev.get("schema") != now["schema"] or prev.get("scopes") != now["scopes"]:
                raise ValueError("CENSUS_BASELINE_SCOPE_OR_SCHEMA_MISMATCH")
            # Counts-only inputs support count comparisons, not identity parity.
            for key in ("collected", "selected"):
                if type(prev.get(key)) is not int or prev[key] < 0:
                    raise ValueError("CENSUS_BASELINE_COUNT_INVALID: " + key)
                if now[key] < prev[key]:
                    concerns.append(f"{key.upper()}_DROPPED: {prev[key]} -> {now[key]} "
                                    f"(-{prev[key] - now[key]})")
            if "selected_nodeids" in prev:
                removed = sorted(set(prev["selected_nodeids"]) - set(now["selected_nodeids"]))
                now["nodeid_diff"] = "available"
            else:
                now["nodeid_diff"] = "unavailable_baseline_has_no_nodeids"
            prev_skips = ((prev.get("execution") or {}).get("testcase_outcomes", {}) or {}).get("skipped", 0)
            now_skips = ((now.get("execution") or {}).get("testcase_outcomes", {}) or {}).get("skipped", 0)
            if now.get("execution") and prev.get("execution") and now_skips > prev_skips:
                concerns.append(f"SKIPS_ROSE: {prev_skips} -> {now_skips} "
                                f"(+{now_skips - prev_skips} case(s) stopped executing)")
            # A collection-provisioning difference needs review; equal markers do
            # not prove equal execution environments for imported reports.
            prev_env, now_env = prev.get("environment"), now.get("environment")
            if prev_env is not None and prev_env != now_env:
                old_deps = prev_env.get("collection_gating_deps", "UNRECORDED")
                new_deps = now_env.get("collection_gating_deps", "UNRECORDED")
                concerns.append(
                    "ENVIRONMENT_DIFFERS: collection provisioning differs; "
                    "official_data_reachable baseline="
                    f"{prev_env.get('official_data_reachable')} vs now="
                    f"{now_env.get('official_data_reachable')}; "
                    f"collection_gating_deps baseline={old_deps} vs now={new_deps}; "
                    "imported execution environment is unbound")
            old_exec, new_exec = prev.get("execution"), now.get("execution")
            if old_exec and not new_exec:
                concerns.append("EXECUTION_MISSING: baseline had execution evidence")
            if old_exec and new_exec:
                old_passed = old_exec.get("testcase_outcomes", {}).get("passed", 0)
                new_passed = new_exec.get("testcase_outcomes", {}).get("passed", 0)
                if new_passed < old_passed:
                    concerns.append(f"PASSED_DROPPED: {old_passed} -> {new_passed}")
                if "testcases" in old_exec and "testcases" in new_exec:
                    old_ids = collections.Counter((c, n) for c, n, outcome in old_exec["testcases"] if outcome == "passed")
                    new_ids = collections.Counter((c, n) for c, n, outcome in new_exec["testcases"] if outcome == "passed")
                    lost = old_ids - new_ids
                    if lost:
                        concerns.append(f"PREVIOUSLY_PASSING_CASES_NOT_PASSING: {sum(lost.values())}")
                    now["execution_comparison"] = "testcase_identity_and_counts"
                else:
                    now["execution_comparison"] = "counts_only_identity_unavailable"
        now["removed_selected_nodeids"] = removed
        now["concerns"] = concerns
        failures = (now["execution"] or {}).get("testcase_outcomes", {})
        now["status"] = ("REVIEW_REQUIRED"
                         if removed or concerns or failures.get("failure") or failures.get("error")
                         else "PASS")
        if a.write:
            with Path(a.out).open("x", encoding="utf-8") as handle:
                json.dump(now, handle, indent=2); handle.write("\n")
        print(json.dumps({k: v for k, v in now.items() if not k.endswith("nodeids")}, indent=2))
        return 0 if now["status"] == "PASS" else 1
    except (OSError, ValueError, KeyError, ET.ParseError) as exc:
        print("SUITE_COUNT_CENSUS_FAILED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
