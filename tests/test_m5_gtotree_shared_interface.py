"""Independent option rosters and actual wrapper refusals; no native tree tools."""
import importlib.util
import csv
import json
from pathlib import Path
import shlex
import sys
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))
import _gtotree_versions as shared
import _trees_432_fakes as F
from _trees_432_fakes import native_tree_tmp_path  # noqa: F401


def load(name):
    spec = importlib.util.spec_from_file_location("m5_shared_" + name, ROOT / "tools" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# Independently transcribed declaration spellings from the pinned native sources.
# These are not generated from the adapter's required-option list.
V1_HELP = "\n".join([
    " - [-f <file>] FASTA list", " - [-H <file>] HMM file", " - [-m <file>] mapping file",
    " - [-n <int> ] num cpus", " - [-M <int> ] num muscle threads", " - [-j ] num jobs",
    " - [-N ] do not make a tree", " - [-k ] keep alignments", " - [-o <str>] output",
])
V2_HELP = "\n".join([
    "-f <file> input list", "-H <file> HMM", "-m | --mapping-file <file>",
    "-j | --num-jobs <int>", "-M | --muscle-threads <int>", "-N | --no-tree",
    "-k | --keep-gene-alignments", "-o | --output-dir <dir>",
])


@pytest.mark.parametrize("text,expected", [
    ("GToTree v1.8.19", "1.8.19"), ("1.8.19", "1.8.19"),
    ("GToTree v2.0.0", "2.0.0"), ("GToTree v2.0.3", "2.0.3"),
    ("\x1b[32mGToTree v2.0.0\x1b[0m", "2.0.0"),
    ("warning: Python 3.12.0\nGToTree v2.0.0", "2.0.0"),
    ("GToTree v2.0.0\nGToTree v2.0.0", "2.0.0"),
    ("GToTree v1.8.16", None), ("GToTree v3.0.0", None), ("GToTree v2.1.0", None),
    ("GToTree v2.0.0rc1", None), ("GToTree v2.0.0+local", None),
    ("GToTree v1.8.190", None), ("GToTree v2.0.0\nGToTree v1.8.19", None),
    ("installed 2.0.0, requires GToTree 1.8.19", None), ("Python 2.0.0", None), ("", None),
])
def test_numeric_version_admission_is_unambiguous(text, expected):
    assert shared.accepted(text) is (expected is not None)
    if expected:
        assert shared.profile(text)["version"] == expected
    else:
        with pytest.raises(ValueError, match="GTOTREE_VERSION"):
            shared.profile(text)


@pytest.mark.parametrize("version,help_text,help_flag", [
    ("GToTree v1.8.19", V1_HELP, "-h"), ("GToTree v2.0.0", V2_HELP, "-s"),
])
def test_source_style_help_contract_and_native_exit_status(version, help_text, help_flag):
    calls = []
    def child(argv, **kwargs):
        calls.append(argv)
        assert kwargs["stdin"] == shared.subprocess.DEVNULL
        return SimpleNamespace(stdout=version if argv[-1] == "-v" else help_text, stderr="", returncode=0)
    result = shared.probe("/selected/gtotree", run=child)
    assert result["verified_interface"] == result["help_contract"] == "PASS"
    assert result["version_exit"] == result["help_exit"] == 0
    assert calls == [["/selected/gtotree", "-v"], ["/selected/gtotree", help_flag]]
    assert result["mapping_contract"] == (
        "two_or_three_column_tsv_input_basename_to_label" if help_flag == "-h" else
        "two_or_three_column_tsv_exact_provided_path_or_genome_id_to_label")


@pytest.mark.parametrize("phase", ["version", "help"])
def test_nonzero_probe_cannot_be_repaired_by_valid_text(phase):
    def child(argv, **kwargs):
        is_version = argv[-1] == "-v"
        return SimpleNamespace(stdout="GToTree v2.0.0" if is_version else V2_HELP, stderr="",
                               returncode=9 if (is_version == (phase == "version")) else 0)
    result = shared.probe("/selected/gtotree", run=child)
    assert result["status"] == "PROBE_FAILED" and result["verified_interface"] != "PASS"
    assert result[phase + "_exit"] == 9


def test_flags_only_mentioned_in_prose_do_not_establish_interface():
    def child(argv, **kwargs):
        return SimpleNamespace(stdout="GToTree v2.0.0" if argv[-1] == "-v" else
                               "This prose mentions -f -H -m -j -M -N -k -o but declares no options.",
                               stderr="", returncode=0)
    result = shared.probe("/selected/gtotree", run=child)
    assert result["help_contract"] == "HOLD_HELP_DRIFT"
    assert set(result["missing_help_tokens"]) == {"-f", "-H", "-m", "-j", "-M", "-N", "-k", "-o"}


@pytest.mark.parametrize("version", ["1.8.19", "2.0.0"])
def test_planner_and_runner_delegate_exact_profile_argv(version):
    planner = load("plan_gtotree_iqtree")
    runner = load("run_planned_tree")
    script = planner._command_text(Path("/fresh/run"), Path("hmm/targets.hmm"),
                                   "/bin/gtotree", "/bin/iqtree", 1, version_text=version)
    if version == "2.0.0":
        assert "HOLD: governed v2 runner bindings missing" in script
        assert "exit 2" in script
        assert "/bin/gtotree" not in script and "/bin/iqtree" not in script
    else:
        argv = next(shlex.split(line) for line in script.splitlines()
                    if line.startswith("/bin/gtotree "))
        expected = ["/bin/gtotree", "-f", "input_view/genomes.txt", "-H", "hmm/targets.hmm",
                    "-m", "input_view/labels.tsv", "-j", "1", "-n", "1",
                    "-M", "1", "-N", "-k", "-o", "outputs/gtotree_alignment"]
        assert argv == expected
    actual = runner.gtotree_command("/bin/gtotree", version, "genomes.txt", "targets.hmm", 1, 1, "out")
    base = ["/bin/gtotree", "-f", "genomes.txt", "-H", "targets.hmm", "-j", "1"]
    base += ["-n", "1"] if version == "1.8.19" else []
    assert actual == base + ["-M", "1", "-N", "-o", "out"]


def test_unknown_planner_profile_emits_refusal_stub_not_version_guess():
    planner = load("plan_gtotree_iqtree")
    script = planner._command_text(Path("/fresh/run"), Path("hmm/targets.hmm"),
                                   "/bin/gtotree", "/bin/iqtree", version_text="GToTree v9.0.0")
    assert "HOLD_UNVERIFIED_VERSION" in script and "exit 2" in script
    assert "/bin/gtotree" not in script and "/bin/iqtree" not in script


def test_planner_resolves_lowercase_executable_without_uppercase(monkeypatch):
    planner = load("plan_gtotree_iqtree")
    monkeypatch.setattr(planner.shutil, "which", lambda name: "/selected/bin/gtotree" if name == "gtotree" else None)
    assert planner.resolve_executable(None, planner.GTOTREE_BINS) == "/selected/bin/gtotree"


@pytest.mark.parametrize("version", ["GToTree v1.8.16", "GToTree v3.0.0", "GToTree v2.0.0rc1",
                                     "GToTree v2.0.0\nGToTree v1.8.19"])
def test_actual_runner_refuses_unsupported_or_conflicting_version_before_compute(tmp_path, monkeypatch, version):
    runner = F.load_runner()
    fake = F.install_fake_bins(tmp_path, monkeypatch, version=version)
    listing = F.stage_genomes(tmp_path)
    output = tmp_path / "fresh_output"
    assert runner.main(F.base_args(listing, output)) == 3
    assert not output.exists() and F.records(fake["record"]) == []


@pytest.mark.parametrize("variable,value", [("FAKE_GTOTREE_VERSION_RC", "6"),
                                            ("FAKE_GTOTREE_HELP_RC", "7"),
                                            ("FAKE_GTOTREE_HELP_MISSING", "-M")])
def test_actual_runner_probe_failure_preserves_fresh_boundary(tmp_path, monkeypatch, variable, value):
    runner = F.load_runner()
    fake = F.install_fake_bins(tmp_path, monkeypatch)
    monkeypatch.setenv(variable, value)
    listing = F.stage_genomes(tmp_path)
    output = tmp_path / "fresh_output"
    assert runner.main(F.base_args(listing, output)) == 3
    assert not output.exists() and F.records(fake["record"]) == []


def test_actual_v1_wrapper_carries_resolved_hmm_threads_and_alignment_only(tmp_path, monkeypatch):
    runner = F.load_runner()
    fake = F.install_fake_bins(tmp_path, monkeypatch, version="GToTree v1.8.19", gtotree_name="GToTree")
    monkeypatch.setenv("FAKE_ALN_NAME", "Aligned_SCGs.faa")
    listing = F.stage_genomes(tmp_path)
    output = tmp_path / "fresh_output"
    assert runner.main(F.base_args(listing, output, threads=1)) == 0
    analysis = next(row for row in F.records(fake["record"]) if row["tool"] == "gtotree")
    argv = analysis["argv"]
    assert argv[argv.index("-H") + 1] == fake["hmm"]
    assert argv[argv.index("-n") + 1] == argv[argv.index("-M") + 1] == "1"
    assert "-N" in argv
    receipt = json.loads((output / "run_status.json").read_text())
    assert receipt["status"] == "DONE"
    assert receipt["gtotree_probe"]["version_exit"] == receipt["gtotree_probe"]["help_exit"] == 0
    assert receipt["gtotree_probe"]["profile"] == "1.8.19"


def test_v2_helper_contract_does_not_require_v1_concatenation_executable():
    assert "gtt-cat-alignments" not in shared.profile("2.0.0")["required_helpers"]
    assert "gtt-cat-alignments" in shared.profile("1.8.19")["required_helpers"]


def test_v2_default_resource_policy_does_not_claim_requested_one_hmm_cpu():
    result = shared.resource_contract("2.0.0", 1, 1)
    assert result["status"] == "HOLD_UNVERIFIED_V2_RESOURCE_PROFILE"
    assert result["hmm_threads"] is None and result["maximum_parallel_search_threads"] is None
    assert result["muscle_threads"] == 1
    assert result["reviewed_upstream_fact"]["hardcoded_threads"] == 2
    assert result["source_profile"] is None


def test_actual_v2_runner_keeps_interface_pass_separate_from_resource_hold(tmp_path, monkeypatch, capsys):
    runner = F.load_runner()
    fake = F.install_fake_bins(tmp_path, monkeypatch, admit_synthetic_resource_profile=False)
    listing = F.stage_genomes(tmp_path)
    output = tmp_path / "held_native_v2"
    assert runner.main(F.base_args(listing, output, threads=1, parallel=1)) == 3
    assert "GTOTREE_RESOURCE_PROFILE" in capsys.readouterr().err
    assert not output.exists() and F.records(fake["record"]) == []


@pytest.mark.parametrize("version,expected_state,hmm_threads", [
    ("GToTree v1.8.19", "PLANNED_AWAITING_APPROVAL", 1),
    ("GToTree v2.0.0", "HOLD_RESOURCE_PROFILE", None),
])
def test_actual_planner_retains_resource_truth_and_immutable_advice(tmp_path, monkeypatch, version, expected_state, hmm_threads):
    planner = load("plan_gtotree_iqtree")
    panel = tmp_path / "panel.tsv"
    fields = ["role", "query_id", "strain_id", "label", "assembly_path", "archive_member",
              "accession", "reference_rank", "selection_basis"]
    with panel.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        for i, role in enumerate(["QUERY", "REFERENCE", "OUTGROUP"]):
            genome = tmp_path / (role + ".fna")
            genome.write_text(">synthetic_unknown\n" + "N" * (8 + i) + "\n")
            writer.writerow({"role": role, "query_id": "Q" if role != "OUTGROUP" else "",
                "strain_id": "SYNTHETIC_" + role, "label": "Synthetic " + role,
                "assembly_path": str(genome), "reference_rank": "1" if role == "REFERENCE" else "",
                "selection_basis": "fixed synthetic format test"})
    hmm = tmp_path / "markers.hmm"; hmm.write_text("HMMER3/f\nNAME synthetic\n//\n")
    selected = shared.profile(version)
    monkeypatch.setattr(planner, "resolve_executable", lambda explicit, names: explicit)
    monkeypatch.setattr(planner, "resolve_iqtree", lambda explicit: explicit)
    monkeypatch.setattr(planner, "probe_toolchain", lambda *args: {
        "gtotree": {"status": "PRESENT", "version": version, "profile": selected["profile"],
                    "help_contract": "PASS", "verified_interface": "PASS"},
        "iqtree": {"status": "PRESENT", "help_contract": "PASS"}, "helpers": {},
    })
    args = SimpleNamespace(panel_tsv=str(panel), prepared_panel=None, workspace=str(tmp_path / "work"),
        run_id="fixed", hmm=str(hmm), panel_cap=3, references_per_query=1,
        max_concurrent_cores=1, threads_per_tree=1, gtotree_bin="/fake/gtotree", iqtree_bin="/fake/iqtree")
    assert planner.plan(args) == (0 if hmm_threads == 1 else 2)
    run = tmp_path / "work" / "runs" / "fixed"
    manifest = json.loads((run / "RUN_MANIFEST.json").read_text())
    assert json.loads((run / "RUN_STATE.json").read_text())["state"] == expected_state
    assert manifest["resource_policy"]["hmm_threads"] == hmm_threads
    assert manifest["resource_policy"]["max_concurrent_trees"] == (1 if hmm_threads == 1 else 0)
    command = (run / "COMMAND.sh").read_text()
    handoff = (run / "HANDOFF.md").read_text()
    if hmm_threads is None:
        assert "HOLD_RESOURCE_PROFILE" in command and "exit 2" in command
        assert "/fake/gtotree" not in command and "NOT_BOUND" in handoff
    else:
        assert "-n 1 -M 1 -N -k" in command
    before = {p.relative_to(run): p.read_bytes() for p in run.rglob("*") if p.is_file()}
    with pytest.raises(FileExistsError):
        planner.plan(args)
    assert before == {p.relative_to(run): p.read_bytes() for p in run.rglob("*") if p.is_file()}


@pytest.mark.parametrize("version", ["GToTree v2.0.0rc1", "GToTree v1.8.19\nGToTree v2.0.0"])
def test_actual_packet_gate_rejects_ambiguous_version_before_file_admission(tmp_path, version):
    gate = load("gtotree_execution_gate")
    packet = dict(run_id="fixed", gtotree={"version": version}, hmm={}, panel=[],
                  working_directory="work", output_directory="out", max_concurrent_jobs=1)
    with pytest.raises(ValueError, match="GTOTREE_VERSION"):
        gate.validate(packet, tmp_path)


@pytest.mark.parametrize("threads,jobs", [(0, 1), (1, 0), (True, 1)])
def test_invalid_resource_values_cannot_become_executable_argv(threads, jobs):
    with pytest.raises(ValueError, match="GTOTREE_RESOURCE"):
        shared.command("/tool", "1.8.19", "list", "hmm", threads, jobs, "out")


def test_probe_timeout_is_a_hold_not_version_fallback():
    def child(argv, **kwargs):
        raise shared.subprocess.TimeoutExpired(argv, 10)
    result = shared.probe("/selected/gtotree", run=child)
    assert result["status"] == "PROBE_FAILED" and result["error"] == "TimeoutExpired"
    assert result["verified_interface"] != "PASS"
