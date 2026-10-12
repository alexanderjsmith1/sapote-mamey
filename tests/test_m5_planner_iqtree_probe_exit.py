"""Planner IQ interface admission: independent text, exit codes and actual hold route."""
import csv
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
# Independently transcribed IQ interface declaration spellings, not copied from
# the implementation's REQUIRED_IQTREE_HELP at fixture construction time.
IQ_HELP = "\n".join(["-s FILE alignment", "-m MODEL substitution model",
                       "-B, --ufboot ultrafast bootstrap", "--alrt approximate support",
                       "-T NUM|AUTO threads", "--prefix output prefix", "--seed random seed"])
IQ_VERSION = "IQ-TREE multicore version 3.1.4"


def load_planner():
    name = "m5_iq_exit_planner"
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools/plan_gtotree_iqtree.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def planner():
    return load_planner()


def child_response(planner, monkeypatch, version_exit=0, help_exit=0, stream="stdout",
                   version=IQ_VERSION, help_text=IQ_HELP):
    calls = []
    def child(argv, **kwargs):
        calls.append((argv, kwargs))
        assert argv[0] == "/selected/iqtree3"
        assert argv[1] in ("--version", "-h")
        text = version if argv[1] == "--version" else help_text
        return SimpleNamespace(stdout=text if stream == "stdout" else "",
                               stderr=text if stream == "stderr" else "",
                               returncode=version_exit if argv[1] == "--version" else help_exit)
    monkeypatch.setattr(planner.subprocess, "run", child)
    return calls


@pytest.mark.parametrize("version_exit,help_exit", [(7, 0), (0, 9), (7, 9), (-9, 0)])
@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_nonzero_exit_cannot_be_repaired_by_complete_version_and_help_text(planner, monkeypatch, version_exit, help_exit, stream):
    calls = child_response(planner, monkeypatch, version_exit, help_exit, stream)
    result = planner._probe("/selected/iqtree3", "--version", "-h", planner.REQUIRED_IQTREE_HELP)
    assert result["status"] == "PROBE_FAILED"
    assert result["help_contract"] == "PROBE_FAILED"
    assert result["version_exit"] == version_exit and result["help_exit"] == help_exit
    assert result["version"] == IQ_VERSION and result["missing_help_tokens"] == []
    assert [argv for argv, kwargs in calls] == [["/selected/iqtree3", "--version"], ["/selected/iqtree3", "-h"]]
    assert all(kwargs["timeout"] == 10 and kwargs["check"] is False for argv, kwargs in calls)


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_zero_exit_valid_interface_is_present_from_either_output_stream(planner, monkeypatch, stream):
    child_response(planner, monkeypatch, stream=stream)
    result = planner._probe("/selected/iqtree3", "--version", "-h", planner.REQUIRED_IQTREE_HELP)
    assert result["status"] == "PRESENT" and result["help_contract"] == "PASS"
    assert result["version_exit"] == result["help_exit"] == 0
    assert result["version"] == IQ_VERSION and result["missing_help_tokens"] == []


def test_zero_exit_missing_interface_option_remains_interface_hold(planner, monkeypatch):
    child_response(planner, monkeypatch, help_text=IQ_HELP.replace("--seed random seed", ""))
    result = planner._probe("/selected/iqtree3", "--version", "-h", planner.REQUIRED_IQTREE_HELP)
    assert result["status"] == "PRESENT"
    assert result["help_contract"] == "HOLD_HELP_DRIFT"
    assert result["missing_help_tokens"] == ["--seed"]


def test_zero_exit_without_any_version_evidence_is_not_present(planner, monkeypatch):
    child_response(planner, monkeypatch, version="")
    result = planner._probe("/selected/iqtree3", "--version", "-h", planner.REQUIRED_IQTREE_HELP)
    assert result["status"] == result["help_contract"] == "PROBE_FAILED"
    assert result["version"] is None and result["version_exit"] == result["help_exit"] == 0


def test_missing_executable_never_launches_a_probe(planner, monkeypatch):
    def forbidden(*args, **kwargs): raise AssertionError("missing executable must not launch")
    monkeypatch.setattr(planner.subprocess, "run", forbidden)
    result = planner._probe(None, "--version", "-h", planner.REQUIRED_IQTREE_HELP)
    assert result["status"] == "MISSING" and result["help_contract"] == "NOT_CHECKED"


@pytest.mark.parametrize("error", ["OSError", "TimeoutExpired"])
def test_transport_failure_cannot_be_admitted(planner, monkeypatch, error):
    def child(argv, **kwargs):
        if error == "OSError": raise OSError("synthetic process launch failure")
        raise subprocess.TimeoutExpired(argv, 10)
    monkeypatch.setattr(planner.subprocess, "run", child)
    result = planner._probe("/selected/iqtree3", "--version", "-h", planner.REQUIRED_IQTREE_HELP)
    assert result["status"] == "PROBE_FAILED" and result["help_contract"] == "NOT_CHECKED"
    assert result["error"] == error


def test_selected_gtotree_route_is_delegated_unchanged(planner, monkeypatch):
    selected = {"status": "PRESENT", "version": "GToTree v1.8.19", "verified_interface": "PASS",
                "help_contract": "PASS", "required_helpers": [], "independent_marker": "preserved"}
    calls = []
    def gtotree(binary): calls.append(binary); return selected
    monkeypatch.setattr(planner, "_probe_gtotree", gtotree)
    child_response(planner, monkeypatch)
    result = planner.probe_toolchain("/selected/gtotree", "/selected/iqtree3")
    assert calls == ["/selected/gtotree"] and result["gtotree"] is selected
    assert result["iqtree"]["status"] == "PRESENT" and result["iqtree"]["help_contract"] == "PASS"


@pytest.mark.parametrize("failed_phase", ["version", "help"])
def test_actual_plan_creates_visible_hold_and_refusal_recipe_on_IQ_nonzero_exit(tmp_path, planner, monkeypatch, failed_phase):
    query = tmp_path / "query.fna"; query.write_text(">query_record\nAAAA\n")
    outgroup = tmp_path / "outgroup.fna"; outgroup.write_text(">outgroup_record\nCCCC\n")
    panel = tmp_path / "panel.tsv"
    with panel.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["role", "query_id", "strain_id", "label", "assembly_path"], delimiter="\t")
        writer.writeheader()
        writer.writerows([{"role": "QUERY", "query_id": "q", "strain_id": "invented_q", "label": "Public_query_GCA_000000001.1", "assembly_path": str(query)},
                          {"role": "OUTGROUP", "query_id": "", "strain_id": "invented_o", "label": "Public_outgroup_GCF_000000002.1", "assembly_path": str(outgroup)}])
    hmm = tmp_path / "synthetic_header.hmm"; hmm.write_text("HMMER3/f\nNAME invented_metadata_profile\n//\n")
    args = SimpleNamespace(panel_tsv=str(panel), prepared_panel=None, workspace=str(tmp_path / "work"),
        run_id="held_probe", hmm=str(hmm), panel_cap=3, references_per_query=1,
        max_concurrent_cores=4, threads_per_tree=1, gtotree_bin="/selected/gtotree", iqtree_bin="/selected/iqtree3")
    monkeypatch.setattr(planner, "resolve_executable", lambda explicit, names: explicit)
    monkeypatch.setattr(planner, "resolve_iqtree", lambda explicit: explicit)
    monkeypatch.setattr(planner, "_probe_gtotree", lambda binary: {
        "status": "PRESENT", "version": "GToTree v1.8.19", "help_contract": "PASS",
        "verified_interface": "PASS", "required_helpers": []})
    child_response(planner, monkeypatch, version_exit=7 if failed_phase == "version" else 0,
                   help_exit=9 if failed_phase == "help" else 0)
    assert planner.plan(args) == 2
    run = tmp_path / "work/runs/held_probe"
    state = json.loads((run / "RUN_STATE.json").read_text())
    manifest = json.loads((run / "RUN_MANIFEST.json").read_text())
    assert state["state"] == "HOLD_TOOL_MISSING" and state["approved"] is False
    assert manifest["execution_authorized"] is False
    assert manifest["toolchain"]["iqtree"][failed_phase + "_exit"] == (7 if failed_phase == "version" else 9)
    recipe = (run / "COMMAND.sh").read_text()
    assert "HOLD_TOOL_MISSING" in recipe and "exit 2" in recipe
    assert "/selected/gtotree" not in recipe and "/selected/iqtree3" not in recipe
