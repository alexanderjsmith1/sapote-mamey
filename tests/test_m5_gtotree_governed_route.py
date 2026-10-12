"""Synthetic joins plus genuine stdlib helper children; no native phylogeny job.

The external GToTree/IQ-TREE boundary is fabricated. Mandatory postflight and
advisory signoff run as real child processes with the production safe environment.
These tests do not validate the installed runtime or the biological marker model.
"""
from pathlib import Path
from types import SimpleNamespace
import io
import json
import shutil
import subprocess
import sys

import pytest

from .test_m5_gtotree_runtime_admission import (
    synthetic, make_plan, planner, runner, rt, watch_owner, put, json_put,
)

ROOT = Path(__file__).resolve().parents[1]


def test_shared_original_label_normalization_keeps_literal_and_fallback_contracts():
    for value, fallback, expected in [("SYNTHETIC/QUERY[A]", "UNUSED", "SYNTHETIC_QUERY_A_"),
                                      ("", "SYNTHETIC_FALLBACK", "SYNTHETIC_FALLBACK"),
                                      ("SYNTHETIC_QUERY.1", "UNUSED", "SYNTHETIC_QUERY.1")]:
        assert planner._safe_label(value, fallback) == expected
        assert runner._gtotree_policy.safe_tip_label(value, fallback) == expected
    rows = [{"object_path": "/synthetic/query.fna", "label": "", "strain_id": "SYNTHETIC_QUERY.1", "role": "QUERY"},
            {"object_path": "/synthetic/out.fna", "label": "SYNTHETIC_OUTGROUP", "strain_id": "OUT", "role": "OUTGROUP"}]
    assert runner._gtotree_policy.plan_tip_rows(rows) == [("query.fna", "SYNTHETIC_QUERY.1", "QUERY"),
                                                       ("out.fna", "SYNTHETIC_OUTGROUP", "OUTGROUP")]


def _child_environment(root):
    for rel in ("home", "tmp", "cache"):
        (root / rel).mkdir(parents=True)
    # Use the actual shared sanitizer, without running its software probe.
    env = rt._environment({"environment": Path(sys.executable).parent.parent}, root)
    assert env["PYTHONSAFEPATH"] == "1" and "PYTHONPATH" not in env
    return env


def _real_child(command, *, cwd, log, env, **unused):
    with Path(log).open("x", encoding="utf-8") as stream:
        proc = subprocess.run(command, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                              stdout=stream, stderr=subprocess.STDOUT, timeout=20)
    return {"exit_code": proc.returncode, "stop_reason": None, "cleanup_error": None}


@pytest.mark.parametrize("mixed_family", [False, True])
def test_actual_safe_path_postflight_child_keeps_sibling_taxonomy_and_json_owner(tmp_path, mixed_family):
    repo = tmp_path / "repo"
    tools, package = repo / "tools", repo / "mamey"
    tools.mkdir(parents=True); package.mkdir()
    for name in ("phylo_postflight.py", "phylo_preflight.py", "_wbio.py",
                 "tree_sanity_check.py", "_console.py", "signoff_check.py"):
        shutil.copy2(ROOT / "tools" / name, tools / name)
    for name in ("__init__.py", "outgroup_registry_path.py", "phylo_evidence.py"):
        shutil.copy2(ROOT / "mamey" / name, package / name)
    # CWD must never supply sibling modules, even if they have the expected names.
    work = tmp_path / "untrusted_cwd"; work.mkdir()
    marker = work / "POISON_IMPORTED"
    poison = "from pathlib import Path\nPath(" + repr(str(marker)) + ").write_text('BAD')\nraise RuntimeError('CWD_IMPORT')\n"
    for name in ("_wbio.py", "phylo_preflight.py"):
        put(work / name, poison)
    env = _child_environment(tmp_path / "context")
    third = "Micromonospora_SYNTHETIC_REFERENCE" if mixed_family else "Streptomyces_SYNTHETIC_REFERENCE"
    tree = put(work / "known.treefile",
        "((Streptomyces_SYNTHETIC_QUERY:0.05," + third + ":0.05)99/100:0.05,"
        "Micromonospora_SYNTHETIC_OUTGROUP:0.1);\n")
    report = work / "postflight.json"
    command = [sys.executable, "-B", "-s", "-P", str(tools / "phylo_postflight.py"),
               str(tree), "--outgroup", "Micromonospora_SYNTHETIC_OUTGROUP", "--json", str(report)]
    result = _real_child(command, cwd=work, log=work / "direct.log", env=env)
    rows = {row["check"]: row for row in json.loads(report.read_text())}
    assert result["exit_code"] == (1 if mixed_family else 0)
    assert rows["P1"]["status"] == rows["P2"]["status"] == rows["P3"]["status"] == "PASS"
    assert rows["P4"]["status"] == ("FAIL" if mixed_family else "PASS")
    assert "Streptomycetaceae" in rows["P4"]["message"] or mixed_family
    assert not marker.exists()

    class ChildLaunch:
        root = work
        count = 0
        commands = []
        def __call__(self, argv, log, selected_env):
            self.count += 1; self.commands.append(argv)
            return _real_child(argv, cwd=self.root,
                log=self.root / ("watch_%03d.log" % self.count), env=selected_env)["exit_code"]

    launch = ChildLaunch()
    okay, details = runner.hard_tree_qc(str(tree), "Micromonospora_SYNTHETIC_OUTGROUP",
        tools_dir=str(tools), mamey_dir=str(package), launch=launch, log=io.StringIO(), env=env)
    assert okay is (not mixed_family), "\n".join(details)
    assert launch.commands == [[sys.executable, str(tools / "phylo_postflight.py"),
                               str(tree), "--outgroup", "Micromonospora_SYNTHETIC_OUTGROUP"]]
    assert any("[P4]" in line for line in details)
    signoff = _real_child([sys.executable, str(tools / "signoff_check.py"), str(tree)],
                         cwd=work, log=work / "signoff.log", env=env)
    assert signoff["exit_code"] == 0
    assert "QC gate (advisory)" in (work / "signoff.log").read_text()
    assert not marker.exists()


def _runner_args(root, source, iq, *, fresh_probe):
    manifest = json.loads((root / "RUN_MANIFEST.json").read_text())
    return ["--approved", "--genome-list", str(root / "input_view/genomes_absolute.txt"),
        "--mapping-file", str(root / "input_view/labels.tsv"), "--plan-dir", str(root),
        "--workdir", str(root / "outputs/governed_run"), "--outgroup", "SYNTHETIC_OUTGROUP",
        "--query-tips", "SYNTHETIC_QUERY", "--hmm", str(root / manifest["hmm"]["object_relpath"]),
        "--threads", "1", "--parallel", "1", "--gtotree-bin", str(source.e / "bin/gtotree"),
        "--iqtree-bin", str(iq), "--gtotree-runtime-manifest", str(source.manifest),
        "--gtotree-runtime-environment", str(source.e), "--gtotree-runtime-source", str(source.s),
        "--gtotree-runtime-probe-dir", str(fresh_probe)]


def _approve(root):
    state = json.loads((root / "RUN_STATE.json").read_text())
    state["approved"] = True
    json_put(root / "RUN_STATE.json", state)


@pytest.mark.parametrize("mutation", ["relabel", "swap_role_labels", "row_order", "output_root"])
def test_mutable_mapping_and_matching_cli_cannot_rebind_manifest_identity(synthetic, monkeypatch, mutation):
    root, proof, iq = make_plan(synthetic, monkeypatch)
    _approve(root)
    args = _runner_args(root, synthetic, iq, fresh_probe=synthetic.root / "next_probe")
    path = root / "input_view/labels.tsv"
    lines = path.read_text().splitlines()
    manifest_before = (root / "RUN_MANIFEST.json").read_bytes()
    if mutation == "relabel":
        path.write_text(path.read_text().replace("SYNTHETIC_QUERY", "CHANGED_QUERY"))
        args[args.index("--query-tips") + 1] = "CHANGED_QUERY"
    elif mutation == "swap_role_labels":
        path.write_text(path.read_text().replace("SYNTHETIC_QUERY", "TEMP_QUERY").replace(
            "SYNTHETIC_OUTGROUP", "SYNTHETIC_QUERY").replace("TEMP_QUERY", "SYNTHETIC_OUTGROUP"))
        args[args.index("--query-tips") + 1] = "SYNTHETIC_OUTGROUP"
        args[args.index("--outgroup") + 1] = "SYNTHETIC_QUERY"
    elif mutation == "row_order":
        path.write_text("\n".join(reversed(lines)) + "\n")
    else:
        args[args.index("--workdir") + 1] = str(root / "outputs/alternate")
    observed_before = path.read_bytes()
    monkeypatch.setattr(watch_owner, "run_watched", lambda *a, **kw: pytest.fail("native child before identity refusal"))
    assert runner.main(args) == 3
    assert not (root / "outputs/governed_run").exists()
    assert not (root / "outputs/alternate").exists()
    assert path.read_bytes() == observed_before
    assert (root / "RUN_MANIFEST.json").read_bytes() == manifest_before


def _completed_native_route(synthetic, monkeypatch):
    actual_runtime_from_arguments = rt.runtime_from_arguments
    root, prior_proof, iq = make_plan(synthetic, monkeypatch)
    _approve(root)
    monkeypatch.setattr(rt, "runtime_from_arguments", actual_runtime_from_arguments)
    commands = []
    def boundary(command, **kw):
        commands.append(command)
        if command[0] == str(synthetic.e / "bin/python"):
            return synthetic.watched(command, **kw)
        if command[0] == sys.executable:
            # Exercise the actual production mandatory/advisory helper process.
            assert Path(command[1]).name in ("phylo_postflight.py", "signoff_check.py")
            return _real_child(command, **kw)
        put(Path(kw["log"]), "SYNTHETIC_NATIVE_DIAGNOSTIC\n")
        if command[0] == str(synthetic.e / "bin/gtotree"):
            mapping = [line.split("\t") for line in Path(command[command.index("-m") + 1]).read_text().splitlines()]
            provided = Path(command[command.index("-f") + 1]).read_text().splitlines()
            # Independent reviewed v2 key semantics for this .fna-only fixture:
            # provided_path or extension-free genome ID; basename.fna is invalid.
            accepted_keys = set(provided) | {Path(path).stem for path in provided}
            assert all(key in accepted_keys for key, label in mapping)
            assert [key for key, label in mapping] == provided
            out = Path(command[command.index("-o") + 1])
            put(out / "aligned-SCGs.faa", "".join(">" + label + "\nACDE\n" for name, label in mapping))
            put(out / "genomes-summary-info.tsv", "genome_id\tlabel\tin_final_tree\n" + "".join(
                Path(name).stem + "\t" + label + "\tYes\n" for name, label in mapping))
        elif command[0] == str(iq) and "-s" in command:
            prefix = Path(command[command.index("--prefix") + 1])
            tree = "((SYNTHETIC_QUERY:0.05,SYNTHETIC_REFERENCE:0.05)99/100:0.05,SYNTHETIC_OUTGROUP:0.1);\n"
            put(Path(str(prefix) + ".treefile"), tree)
            put(Path(str(prefix) + ".contree"), tree)
            put(Path(str(prefix) + ".log"), "Total wall-clock time: synthetic boundary\n")
        else:
            assert command == [str(iq), "--version"]
        return {"exit_code": 0, "stop_reason": None, "cleanup_error": None}
    monkeypatch.setattr(watch_owner, "run_watched", boundary)
    probe = synthetic.root / "execution_probe"
    args = _runner_args(root, synthetic, iq, fresh_probe=probe)
    args += ["--signoff", str(ROOT / "tools/signoff_check.py")]
    assert runner.main(args) == 0
    work = root / "outputs/governed_run"
    status = json.loads((work / "run_status.json").read_text())
    assert status["status"] == "DONE" and status["tip_retention"] == "TIPS_RETAINED"
    assert json.loads((probe / "RECEIPT.json").read_text())["status"] == "PASS_SOFTWARE_PROBE_ONLY"
    assert probe != prior_proof._receipt.parent
    assert any(Path(c[1]).name == "phylo_postflight.py" for c in commands if c[0] == sys.executable)
    assert any(Path(c[1]).name == "signoff_check.py" for c in commands if c[0] == sys.executable)
    assert len(status["execution_phases"]) == len(commands) - 1
    return root, work, status


def test_actual_planner_fresh_probe_runner_real_helpers_and_bound_discovery(synthetic, monkeypatch):
    root, work, status = _completed_native_route(synthetic, monkeypatch)
    receipt = synthetic.root / "DISCOVERY.json"
    assert planner.discover_outputs(SimpleNamespace(run_dir=str(root), receipt=str(receipt))) == 0
    result = json.loads(receipt.read_text())
    assert result["discovery_mode"] == "BOUND_GOVERNED_CURRENT_ATTEMPT"
    assert result["status"] == "PASS_UNIQUE_ALIGNMENT"
    assert result["admitted_taxa"] == result["retained_taxa_from_summary"] == 3
    assert result["alignment_candidates"][0]["path"] == status["alignment"]
    assert result["alignment_candidates"][0]["sha256"] == status["completed_artifacts"]["alignment"]["sha256"]
    assert result["genome_summary_paths"] == [str(work / "gtotree/genomes-summary-info.tsv")]
    assert "runner already executes IQ-TREE and hard QC" in (root / "HANDOFF.md").read_text()


@pytest.mark.parametrize("mutation", ["alignment", "summary", "missing_summary", "failed_status", "stale_manifest",
                                    "mapping", "input", "execution_bindings", "copied_status", "ambiguous",
                                    "summary_rehashed", "summary_duplicate_rehashed", "query_removed_rehashed",
                                    "alignment_rehashed", "phase_receipt", "phase_log", "tool_versions"])
def test_discovery_refuses_changed_stale_partial_and_ambiguous_outputs_without_legacy_fallback(synthetic, monkeypatch, mutation):
    root, work, status = _completed_native_route(synthetic, monkeypatch)
    # Unrelated historical-looking output must not satisfy governed admission.
    put(root / "outputs/gtotree_alignment/Aligned_SCGs.faa", ">OLD_A\nAA\n>OLD_B\nAA\n")
    path = work / "run_status.json"
    if mutation == "alignment":
        put(work / "gtotree/aligned-SCGs.faa", ">CHANGED\nAAAA\n")
    elif mutation == "summary":
        summary = work / "gtotree/genomes-summary-info.tsv"
        summary.write_text(summary.read_text().replace("SYNTHETIC_QUERY", "CHANGED_QUERY"))
    elif mutation == "missing_summary":
        (work / "gtotree/genomes-summary-info.tsv").unlink()
    elif mutation == "failed_status":
        status["status"] = "TREE_QC_FAILED"; json_put(path, status)
    elif mutation == "stale_manifest":
        with (root / "RUN_MANIFEST.json").open("a") as stream: stream.write("\n")
    elif mutation == "mapping":
        with (root / "input_view/labels.tsv").open("a") as stream: stream.write("\n")
    elif mutation == "input":
        target = Path(json.loads((root / "RUN_MANIFEST.json").read_text())["assemblies"][0]["object_path"])
        target.write_text(">CHANGED_SYNTHETIC_INPUT\nACAC\n")
    elif mutation == "execution_bindings":
        put(work / "EXECUTION_BINDINGS.json", "{}")
    elif mutation == "copied_status":
        status["plan_binding"]["workdir"] = str(root / "outputs/old_run")
        json_put(path, status)
    elif mutation == "phase_receipt":
        put(work / "watch_001.json", "{}")
    elif mutation == "phase_log":
        put(work / "watch_001.log", "CHANGED_SYNTHETIC_DIAGNOSTIC\n")
    elif mutation == "tool_versions":
        put(work / "TOOL_VERSIONS.json", "[]")
    elif mutation == "ambiguous":
        shutil.copy2(work / "gtotree/aligned-SCGs.faa", work / "gtotree/second-concatenation.faa")
    else:
        key = "alignment" if mutation == "alignment_rehashed" else "genome_summary"
        target = Path(status["completed_artifacts"][key]["path"])
        text = target.read_text()
        if mutation in ("summary_rehashed", "alignment_rehashed"):
            text = text.replace("SYNTHETIC_QUERY", "CHANGED_QUERY")
        elif mutation == "query_removed_rehashed":
            text = text.replace("SYNTHETIC_QUERY\tYes", "SYNTHETIC_QUERY\tNo")
        else:
            lines = text.splitlines(); lines[-1] = lines[1]; text = "\n".join(lines) + "\n"
        target.write_text(text)
        status["completed_artifacts"][key].update(sha256=rt.sha256(target), bytes=target.stat().st_size)
        json_put(path, status)
    snapshot = {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}
    receipt = synthetic.root / "HELD_DISCOVERY.json"
    assert planner.discover_outputs(SimpleNamespace(run_dir=str(root), receipt=str(receipt))) == 2
    result = json.loads(receipt.read_text())
    assert result["status"] == ("HOLD_AMBIGUOUS_ALIGNMENT" if mutation == "ambiguous" else "HOLD_GOVERNED_OUTPUT_BINDING")
    assert result["discovery_mode"] == "BOUND_GOVERNED_CURRENT_ATTEMPT"
    assert {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()} == snapshot


@pytest.mark.parametrize("mutation,allow_drop,expected", [("drop_query", False, "QUERY_TIP_DROPPED"),
    ("drop_query", True, "QUERY_TIP_DROPPED"), ("extra", True, "UNEXPECTED_ALIGNMENT_TIP"),
    ("duplicate", True, "DUPLICATE_ALIGNMENT_TIP")])
def test_direct_mapped_versioned_query_and_unique_tip_roster_refuse_before_iqtree(synthetic, monkeypatch,
                                                                               mutation, allow_drop, expected):
    proof = synthetic.prove()
    monkeypatch.setattr(rt, "runtime_from_arguments", lambda *a: proof)
    iq = put(synthetic.root / "iqtree", "SYNTHETIC_IQTREE")
    query = put(synthetic.root / "query.fna", ">SYNTHETIC_QUERY\nACGT\n")
    out = put(synthetic.root / "out.fna", ">SYNTHETIC_OUTGROUP\nCCGT\n")
    genomes = put(synthetic.root / "genomes.txt", str(query) + "\n" + str(out) + "\n")
    mapping = put(synthetic.root / "labels.tsv", str(query) + "\tSYNTHETIC_QUERY.1\n" +
                  str(out) + "\tSYNTHETIC_OUTGROUP.1\n")
    hmm = put(synthetic.root / "model.hmm", "NAME SYNTHETIC_MODEL\n")
    calls = []
    def boundary(command, **kw):
        calls.append(command); put(Path(kw["log"]), "SYNTHETIC_NATIVE_DIAGNOSTIC\n")
        if command[0] == str(synthetic.e / "bin/gtotree"):
            tips = ["SYNTHETIC_QUERY.1", "SYNTHETIC_OUTGROUP.1"]
            if mutation == "drop_query": tips.remove("SYNTHETIC_QUERY.1")
            elif mutation == "extra": tips.append("UNDECLARED_SYNTHETIC_TIP")
            else: tips.append("SYNTHETIC_QUERY.1")
            put(Path(command[command.index("-o") + 1]) / "aligned-SCGs.faa",
                "".join(">" + tip + "\nACDE\n" for tip in tips))
        else:
            assert command == [str(iq), "--version"]
        return {"exit_code": 0, "stop_reason": None, "cleanup_error": None}
    monkeypatch.setattr(watch_owner, "run_watched", boundary)
    work = synthetic.root / "fresh_versioned_output"
    args = ["--approved", "--genome-list", str(genomes), "--mapping-file", str(mapping),
        "--workdir", str(work), "--outgroup", "SYNTHETIC_OUTGROUP.1", "--query-tips", "SYNTHETIC_QUERY.1",
        "--hmm", str(hmm), "--threads", "1", "--parallel", "1", "--gtotree-bin", str(synthetic.e / "bin/gtotree"),
        "--iqtree-bin", str(iq)] + (["--allow-reference-drop"] if allow_drop else [])
    assert runner.main(args) == 7
    status = json.loads((work / "run_status.json").read_text())
    assert status["status"] == expected
    assert not any("-s" in command for command in calls)
    if mutation == "drop_query":
        assert status["dropped"][0]["tip"] == "SYNTHETIC_QUERY.1"
        assert status["dropped"][0]["role"] == "query"
    elif mutation == "extra":
        assert status["unexpected"] == ["UNDECLARED_SYNTHETIC_TIP"]
    else:
        assert status["duplicates"] == ["SYNTHETIC_QUERY.1"]
    # The distinct pre-existing filename ingress still stems actual filenames.
    assert runner._load_module(str(ROOT / "tools/gtotree_execution_gate.py"), "legacy_filename_query_control").declared_query_tips(
        ["SYNTHETIC_QUERY"], query_tips=["SYNTHETIC_QUERY.fna"]) == {"SYNTHETIC_QUERY"}
