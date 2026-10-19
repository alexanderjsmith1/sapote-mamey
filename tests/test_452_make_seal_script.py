"""Small offline exact-identity seal-plan fixtures; no seal, subprocess or pytest child."""
from collections import Counter
from datetime import datetime, timedelta, timezone
import copy
import importlib.util
import json
from pathlib import Path
import stat
import zipfile

import pytest


TOOLS = Path(__file__).resolve().parents[1] / "tools"
NODES = ["tests/test_synthetic.py::test_parameter[a::b]",
         "tests/test_synthetic.py::TestNamed::test_two"]


@pytest.fixture
def tool(monkeypatch):
    path = TOOLS / "make_seal_script.py"
    # Let the own-before control fail in its call phase, not during fixture setup.
    if not path.is_file():
        return None
    monkeypatch.syspath_prepend(str(TOOLS))
    spec = importlib.util.spec_from_file_location("c2_make_seal_script", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def dump(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def capture(root, skipped=False):
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    rows = []; results = []
    for i, node in enumerate(NODES):
        skip = skipped and i == 1
        phases = ["setup", "teardown"] if skip else ["setup", "call", "teardown"]
        for phase in phases:
            rows.append({"nodeid": node, "when": phase,
                         "outcome": "skipped" if skip and phase == "setup" else "passed",
                         "duration": 0.001, "reason": "optional tool unavailable" if skip and phase == "setup" else None,
                         "wasxfail": None})
        results.append({"nodeid": node, "outcome": "skipped" if skip else "passed",
                        "reasons": ["optional tool unavailable"] if skip else [], "wasxfail": []})
    return {"schema": "sapote-mamey.pytest-execution.v1", "started_utc": now, "completed_utc": now,
            "rootpath": str(root), "pytest_version": "synthetic-1", "inifile": None,
            "invocation_args": ["-q", "--rootdir", str(root), "--release-evidence", str(root.parent / "capture.json")],
            "collected": list(NODES), "testscollected": len(NODES), "collection_finished": True,
            "deselected": [], "collection_errors": [], "collection_skips": [], "duplicate_collected": [],
            "unexpected_report_nodes": [], "phase_reports": rows, "outcomes": results,
            "counts": dict(Counter(r["outcome"] for r in results)), "subtests": [], "subtest_counts": {}, "exit_code": 0}


@pytest.fixture
def case(tool, tmp_path):
    if tool is None:
        return None
    cut = tmp_path / "cut"; cut.mkdir()
    source = cut / "source"; source.mkdir()
    extracted = cut / "extracted"; extracted.mkdir()
    for root in (source, extracted):
        (root / "marker.txt").write_text("synthetic source\n"); (root / "marker.txt").chmod(0o644)
    archive = cut / "synthetic.zip"
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.write(extracted / "marker.txt", "marker.txt")
    owner = cut / "owner consumer.sh"; owner.write_text("#!/bin/bash\nexit 99 # never executed by fixtures\n")
    manifests = []
    for name, root, skip in (("source", source, False), ("archive", extracted, True)):
        log = cut / (name + ".log"); log.write_text("synthetic log: ..\n" if not skip else "synthetic log: .s\n")
        cap = cut / (name + "-capture.json")
        data = capture(root, skip); data["invocation_args"][-1] = str(cap); dump(cap, data)
        manifest = cut / (name + "-input.json")
        dump(manifest, {"schema": "sapote-mamey.seal-suite-input.v1", "log": tool.pin(log),
                       "capture": tool.pin(cap), "tree": {"path": str(root), "sha256": tool.source_tree_sha256(root)}})
        manifests.append(manifest)
    differences = cut / "differences.json"
    a = capture(source)["outcomes"][1]; b = capture(extracted, True)["outcomes"][1]
    dump(differences, [{"nodeid": NODES[1], "source": tool.outcome(a), "archive": tool.outcome(b),
                        "explanation": "Synthetic fixture tool differs; no real environment claim"}])
    args = dict(cut_folder=cut, source_log=cut / "source.log", archive_log=cut / "archive.log",
                source_evidence=manifests[0], archive_evidence=manifests[1], differences=differences,
                archive=archive, archive_sha256=tool.pin(archive)["sha256"], owner_script=owner)
    return args


def update_capture(tool, case, role, mutate):
    manifest_path = case[role + "_evidence"]
    manifest = tool.read_json(manifest_path)
    path = Path(manifest["capture"]["path"])
    data = tool.read_json(path); mutate(data); dump(path, data)
    manifest["capture"] = tool.pin(path); dump(manifest_path, manifest)


def test_exact_named_difference_generates_without_executing(tool, case, tmp_path, monkeypatch):
    assert tool is not None, "exact-identity seal generator is absent; dot/count checks cannot replace it"
    import subprocess
    def forbidden(*args, **kwargs): raise AssertionError("generator attempted execution")
    monkeypatch.setattr(subprocess, "run", forbidden); monkeypatch.setattr(subprocess, "Popen", forbidden)
    plan = tool.build_plan(**case)
    assert plan["named_differences"][0]["nodeid"] == NODES[1]
    result = tool.emit_candidate(plan, tmp_path / "candidate")
    wrapper = Path(result["script"]["path"])
    assert "SAPOTE_OWNER_SEAL_APPROVED" in wrapper.read_text()
    assert not (stat.S_IMODE(wrapper.stat().st_mode) & 0o111)
    assert tool.recheck_plan(Path(result["plan"]["path"]), result["plan"]["sha256"]) == plan


def test_reordered_progress_is_compared_by_exact_id(tool, case):
    def reverse(data):
        data["collected"].reverse(); data["outcomes"].reverse()
    update_capture(tool, case, "archive", reverse)
    plan = tool.build_plan(**case)
    assert [r["nodeid"] for r in plan["named_differences"]] == [NODES[1]]


def test_matching_runs_need_no_dispositions(tool, case):
    original = tool.read_json(Path(tool.read_json(case["source_evidence"])["capture"]["path"]))
    def match(data):
        for key in ("outcomes", "phase_reports", "counts"):
            data[key] = copy.deepcopy(original[key])
    update_capture(tool, case, "archive", match)
    dump(case["differences"], [])
    assert tool.build_plan(**case)["named_differences"] == []


@pytest.mark.parametrize("mode", ["duplicate", "changed_context", "missing_context"])
def test_subtest_identity_cannot_be_inferred_from_equal_main_counts(tool, case, mode):
    def base(data):
        data["subtests"] = [{"nodeid": NODES[0], "when": "call", "outcome": "passed",
                            "reason": None, "wasxfail": None, "duration": 0.01, "context": "value=1"}]
        data["subtest_counts"] = {"passed": 1}
    for role in ("source", "archive"): update_capture(tool, case, role, base)
    def mutate(data):
        if mode == "duplicate":
            data["subtests"].append(copy.deepcopy(data["subtests"][0])); data["subtest_counts"] = {"passed": 2}
        if mode == "changed_context": data["subtests"][0]["context"] = "value=2"
        if mode == "missing_context": data["subtests"][0].pop("context")
    update_capture(tool, case, "archive", mutate)
    with pytest.raises(ValueError, match="subtest"):
        tool.build_plan(**case)


def test_progress_dot_only_log_cannot_supply_identity(tool, case):
    case["archive_evidence"].write_text('{"schema":"progress-dot-order","dots":".s"}')
    with pytest.raises(ValueError, match="exact execution manifest required"):
        tool.build_plan(**case)


@pytest.mark.parametrize("mutation,reason", [
    (lambda d: d["collected"].__setitem__(1, "tests/test_other.py::test_two"), "outcome identities"),
    (lambda d: d["collected"].append(d["collected"][0]), "duplicate node"),
    (lambda d: d.__setitem__("collection_finished", False), "collection did not finish"),
    (lambda d: d.__setitem__("exit_code", 1), "did not exit green"),
    (lambda d: d.__setitem__("deselected", [NODES[0]]), "deselected"),
    (lambda d: d["phase_reports"].pop(), "missing, duplicated"),
    (lambda d: d["invocation_args"].append("--collect-only"), "collect-only"),
    (lambda d: d["invocation_args"].extend(["-k", "easy"]), "incompatible suite selection"),
    (lambda d: d["outcomes"][1].__setitem__("reasons", ["invented cause"]), "phase evidence"),
    (lambda d: d.__setitem__("collection_skips", [{"nodeid": "tests/test_unknown.py", "reason": "skip"}]), "ambiguous test identity"),
])
def test_incomplete_ambiguous_and_incompatible_evidence_refuses(tool, case, mutation, reason):
    update_capture(tool, case, "archive", mutation)
    with pytest.raises(ValueError, match=reason):
        tool.build_plan(**case)


def test_same_counts_different_nodes_refuses(tool, case):
    def replace(data):
        for key in ("collected",): data[key] = [n.replace("test_two", "test_unseen") for n in data[key]]
        for key in ("outcomes", "phase_reports"):
            for row in data[key]: row["nodeid"] = row["nodeid"].replace("test_two", "test_unseen")
    update_capture(tool, case, "archive", replace)
    with pytest.raises(ValueError, match="incompatible collection identities"):
        tool.build_plan(**case)


@pytest.mark.parametrize("mode", ["missing", "extra", "duplicate", "wrong", "blank"])
def test_unexplained_stale_or_ambiguous_dispositions_refuse(tool, case, mode):
    rows = tool.read_json(case["differences"])
    if mode == "missing": rows = []
    if mode == "extra": rows.append(dict(rows[0], nodeid=NODES[0]))
    if mode == "duplicate": rows.append(copy.deepcopy(rows[0]))
    if mode == "wrong": rows[0]["archive"]["outcome"] = "passed"
    if mode == "blank": rows[0]["explanation"] = " "
    dump(case["differences"], rows)
    with pytest.raises(ValueError): tool.build_plan(**case)


@pytest.mark.parametrize("which", ["source_log", "archive_log", "owner_script", "differences"])
def test_changed_bound_inputs_refuse_on_owner_recheck(tool, case, tmp_path, which):
    result = tool.emit_candidate(tool.build_plan(**case), tmp_path / "candidate")
    case[which].write_text(case[which].read_text() + "\nchanged\n")
    with pytest.raises(ValueError):
        tool.recheck_plan(Path(result["plan"]["path"]), result["plan"]["sha256"])


def test_archive_tree_and_zip_must_match(tool, case):
    extracted = Path(tool.read_json(case["archive_evidence"])["tree"]["path"])
    (extracted / "marker.txt").write_text("changed\n")
    # Even a freshly declared tree digest cannot hide divergence from pinned ZIP bytes.
    manifest = tool.read_json(case["archive_evidence"])
    manifest["tree"]["sha256"] = tool.source_tree_sha256(extracted); dump(case["archive_evidence"], manifest)
    with pytest.raises(ValueError, match="archive/extracted content differs"):
        tool.build_plan(**case)


def test_stale_evidence_refuses(tool, case):
    def stale(data):
        timestamp = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat().replace("+00:00", "Z")
        data["started_utc"] = data["completed_utc"] = timestamp
    update_capture(tool, case, "archive", stale)
    with pytest.raises(ValueError, match="expired"): tool.build_plan(**case)


def test_output_is_fresh_and_outside_bound_evidence(tool, case, tmp_path):
    plan = tool.build_plan(**case)
    output = tmp_path / "candidate"; output.mkdir(); marker = output / "prior"; marker.write_text("preserve")
    with pytest.raises(ValueError, match="occupied"): tool.emit_candidate(plan, output)
    assert marker.read_text() == "preserve"
    with pytest.raises(ValueError, match="overlaps"): tool.emit_candidate(plan, case["cut_folder"] / "candidate")
    alias = tmp_path / "dangling"; alias.symlink_to(tmp_path / "missing")
    with pytest.raises(ValueError, match="occupied"): tool.emit_candidate(plan, alias)


def test_duplicate_json_fields_refuse(tool, case):
    case["archive_evidence"].write_text('{"schema":"a","schema":"b"}')
    with pytest.raises(ValueError, match="duplicate JSON key"): tool.build_plan(**case)
