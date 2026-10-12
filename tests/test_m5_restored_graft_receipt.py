"""Known-answer numerical fixtures: external tools are spied; admission is real."""
import hashlib
import json
import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
Phylo = pytest.importorskip("Bio.Phylo")
from tools import graft_integrity as gi

REF = "((REF_A:0.2,REF_B:0):0.3,REF_C:0.4,OG:0.5);\n"
BACKBONE = "((REF_A:0.2{0},REF_B:0.1053605157{1}):0.3{2},REF_C:0.4{3},OG:0.5{4}){5};"
RAW = "((REF_A:0.2,(REF_B:0.04,QUERY:{pendant}):0.0653605157):0.3,REF_C:0.4,OG:0.5);\n"


def fixture_sources(tmp_path, monkeypatch, default=False, nested=False):
    run = tmp_path / "run"
    place = run / "place" if nested else run
    report = run / "report" if nested else run
    ref = run / "refpkg"
    place.mkdir(parents=True)
    ref.mkdir()
    report.mkdir(exist_ok=True)
    sources = {"jplace": place / "epa_result.jplace", "reference_tree": ref / "ref.tree",
               "reference_alignment": ref / "ref.aln.fasta", "query_alignment": place / "query.aligned.fasta",
               "model": ref / "ref.bestModel", "placement_provenance": place / "_provenance.json",
               "reference_provenance": ref / "_provenance.json"}
    pendant = gi.PLACEHOLDER if default else .07
    data = {"tree": BACKBONE, "fields": ["edge_num", "likelihood", "like_weight_ratio", "distal_length", "pendant_length"],
            "placements": [{"n": ["QUERY"], "p": [[1, -1, 1, .04, pendant]]}]}
    sources["jplace"].write_text(json.dumps(data))
    sources["reference_tree"].write_text(REF)
    sources["reference_alignment"].write_text("".join(f">{name}\nACGT\n" for name in ("REF_A", "REF_B", "REF_C", "OG")))
    sources["query_alignment"].write_text(">QUERY\nACGA\n")
    sources["model"].write_text("GTR+G")
    sources["placement_provenance"].write_text('{"group":"synthetic"}')
    sources["reference_provenance"].write_text('{"molecule":"nucleotide"}')
    calls = []

    def external(argv, **kwargs):
        calls.append((list(argv), kwargs))
        if argv[1:3] == ["examine", "graft"]:
            Path(argv[argv.index("--out-dir")+1], "epa_result.newick").write_text(RAW.format(pendant=pendant))
            return SimpleNamespace(returncode=0)
        assert "--evaluate" in argv
        tree = Phylo.read(argv[argv.index("--tree")+1], "newick")
        next(tip for tip in tree.get_terminals() if tip.name == "QUERY").branch_length = .0123456789
        Phylo.write(tree, argv[argv.index("--prefix")+1] + ".raxml.bestTree", "newick", format_branch_length="%.17g")
        return SimpleNamespace(returncode=0, stdout="final logLikelihood -12.3\n", stderr="")

    monkeypatch.setattr(gi.subprocess, "run", external)
    return run, report, sources, calls


def produce(tmp_path, monkeypatch, **kwargs):
    run, report, sources, calls = fixture_sources(tmp_path, monkeypatch, **kwargs)
    before = {role: path.read_bytes() for role, path in sources.items()}
    admitted = gi.produce_graft_length_evidence(sources, report, "synthetic-gappa", sys.executable, {})
    assert {role: path.read_bytes() for role, path in sources.items()} == before
    return run, report, sources, calls, admitted


@pytest.mark.parametrize("default", [False, True])
@pytest.mark.parametrize("nested", [False, True])
def test_real_producer_admitter_geometry_and_portable_selection(tmp_path, monkeypatch, default, nested):
    run, report, sources, calls, admitted = produce(tmp_path, monkeypatch, default=default, nested=nested)
    assert admitted["state"] == "PASS_LENGTH_QA"
    portable = gi.admit_placement_run(run)
    assert portable["selected"]["restored"] == admitted["selected"]["restored"]
    tree = Phylo.read(portable["selected"]["restored"], "newick")
    refs = gi._tips(Phylo.read(sources["reference_tree"], "newick"))
    metric = gi._metric(tree, refs)
    assert metric[min(("REF_B",), tuple(sorted(refs - {"REF_B"})))][0] == 0
    assert gi.query_pendant_paths(tree, refs)["QUERY"] == pytest.approx(.0123456789 if default else .07, abs=1e-13)
    assert len(calls) == (2 if default else 1)
    if default:
        assert calls[1][1]["env"] == {key: "1" for key in gi.RESOURCE_KEYS}
        assert calls[1][0][calls[1][0].index("--threads")+1] == "1"


def test_existing_evidence_refuses_before_external_call_and_preserves_bytes(tmp_path, monkeypatch):
    run, report, sources, calls, admitted = produce(tmp_path, monkeypatch)
    before = {str(p): p.read_bytes() for p in run.rglob("*") if p.is_file()}
    count = len(calls)
    with pytest.raises(ValueError, match="LENGTH_EVIDENCE_EXISTS"):
        gi.produce_graft_length_evidence(sources, report, "synthetic-gappa")
    assert count == len(calls)
    assert before == {str(p): p.read_bytes() for p in run.rglob("*") if p.is_file()}


@pytest.mark.parametrize("role", gi.SOURCE_ROLES)
def test_every_selected_source_change_refuses(tmp_path, monkeypatch, role):
    run, report, sources, calls, admitted = produce(tmp_path, monkeypatch)
    sources[role].write_bytes(sources[role].read_bytes() + b"\n")
    with pytest.raises(ValueError, match="SOURCE_CHANGED"):
        gi.admit_graft_length_evidence(admitted["receipt"], sources)


def test_rehashed_restored_metric_corruption_is_not_admitted(tmp_path, monkeypatch):
    run, report, sources, calls, admitted = produce(tmp_path, monkeypatch)
    target = Path(admitted["selected"]["restored"])
    target.write_text(target.read_text().replace("REF_A:0.20000000000000001", "REF_A:0.9"))
    # Use a parser-level change so the test cannot silently depend on serialization spelling.
    tree = Phylo.read(target, "newick")
    next(t for t in tree.get_terminals() if t.name == "REF_A").branch_length = .9
    Phylo.write(tree, target, "newick", format_branch_length="%.17g")
    receipt = Path(admitted["receipt"])
    record = json.loads(receipt.read_text())
    record["outputs"] = gi._output_records(receipt.parent)
    receipt.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="REFERENCE_METRIC_INVALID"):
        gi.admit_graft_length_evidence(receipt, sources)


def test_missing_evaluation_inputs_retains_hold_no_false_restored_selection(tmp_path, monkeypatch):
    run, report, sources, calls = fixture_sources(tmp_path, monkeypatch, default=True)
    sources["model"].unlink()
    result = gi.produce_graft_length_evidence(sources, report, "synthetic-gappa", sys.executable, {})
    assert result["state"] == "HOLD_LENGTH_QA" and result["selected"] is None
    assert len(calls) == 1
    with pytest.raises(ValueError, match="HOLD"):
        gi.admit_graft_length_evidence(result["receipt"], sources)


def test_full_layout_relocation_accepts_identical_bound_contents(tmp_path, monkeypatch):
    run, report, sources, calls, admitted = produce(tmp_path, monkeypatch, default=True)
    relocated = tmp_path / "relocated"
    shutil.copytree(run, relocated)
    result = gi.admit_placement_run(relocated)
    assert result["state"] == "PASS_LENGTH_QA"
    assert str(relocated) in result["selected"]["restored"]


def test_tied_maximum_pendants_refuse_independent_of_row_order(tmp_path):
    path = tmp_path / "ambiguous.jplace"
    rows = [[1, -1, .5, 0, gi.PLACEHOLDER], [1, -1, .5, 0, .07]]
    for ordered in (rows, rows[::-1]):
        path.write_text(json.dumps({"fields": ["edge_num", "likelihood", "like_weight_ratio", "distal_length", "pendant_length"],
                                    "placements": [{"nm": [["QUERY", 3]], "p": ordered}]}))
        with pytest.raises(ValueError, match="AMBIGUOUS_BEST_PENDANT"):
            gi.default_pendant_queries(path)


def test_shared_query_stem_known_answer_and_unestimated_neighbor_preserved(tmp_path):
    import io
    tree = Phylo.read(io.StringIO("((REF_A:0.2,(REF_B:0,(QUERY1:0.0653605157,QUERY2:0.0653605157):0.04):0.1053605157):0.3,REF_C:0.4,OG:0.5);"), "newick")
    refs = {"REF_A", "REF_B", "REF_C", "OG"}
    before = gi.query_pendant_paths(tree, refs)
    assert before == {"QUERY1": pytest.approx(gi.PLACEHOLDER), "QUERY2": pytest.approx(gi.PLACEHOLDER)}
    gi.apply_pendant_estimates(tree, {"QUERY1": .012}, refs)
    after = gi.query_pendant_paths(tree, refs)
    assert after["QUERY1"] == pytest.approx(.012)
    assert after["QUERY2"] == pytest.approx(before["QUERY2"])
    assert all((c.branch_length or 0) >= 0 for c in tree.find_clades())


@pytest.mark.parametrize("mutation", ["missing_best", "nonzero", "bad_model_hash", "extra_file"])
def test_retained_evaluation_evidence_is_required(tmp_path, monkeypatch, mutation):
    run, report, sources, calls, admitted = produce(tmp_path, monkeypatch, default=True)
    receipt = Path(admitted["receipt"])
    directory = next((receipt.parent / "evaluation").iterdir())
    if mutation == "missing_best":
        (directory / "bestTree.newick").unlink()
    elif mutation == "extra_file":
        (directory / "undeclared.txt").write_text("not an admitted evidence role")
    else:
        command = json.loads((directory / "command.json").read_text())
        command["returncode" if mutation == "nonzero" else "model_sha256"] = 1 if mutation == "nonzero" else "0" * 64
        (directory / "command.json").write_text(json.dumps(command))
    record = json.loads(receipt.read_text())
    record["outputs"] = gi._output_records(receipt.parent)
    receipt.write_text(json.dumps(record))
    with pytest.raises((ValueError, OSError)):
        gi.admit_graft_length_evidence(receipt, sources)


def test_rehashed_internal_support_edit_is_not_a_length_only_derivative(tmp_path, monkeypatch):
    run, report, sources, calls, admitted = produce(tmp_path, monkeypatch)
    restored = Path(admitted["selected"]["restored"])
    tree = Phylo.read(restored, "newick")
    tree.root.clades[0].confidence = 42
    Phylo.write(tree, restored, "newick", format_branch_length="%.17g", format_confidence="%.17g")
    receipt = Path(admitted["receipt"])
    record = json.loads(receipt.read_text()); record["outputs"] = gi._output_records(receipt.parent)
    receipt.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="TOPOLOGY_CHANGED"):
        gi.admit_graft_length_evidence(receipt, sources)


@pytest.mark.parametrize("change", ["content", "removed"])
def test_evaluator_change_during_child_retains_hold_and_before_after_evidence(tmp_path, monkeypatch, change):
    run, report, sources, calls = fixture_sources(tmp_path, monkeypatch, default=True)
    # Minimal synthetic executable identity only: no interpreter/runtime payload copy,
    # and the subprocess boundary is spied, so this file is never executed.
    evaluator = tmp_path / "synthetic-raxml"
    evaluator.write_text("#!/bin/sh\nexit 0\n")
    evaluator.chmod(0o700)
    before = hashlib.sha256(evaluator.read_bytes()).hexdigest()
    external = gi.subprocess.run
    def changing_child(argv, **kwargs):
        result = external(argv, **kwargs)
        if "--evaluate" in argv:
            if change == "content":
                evaluator.write_text("#!/bin/sh\nexit 2 # changed\n")
            else:
                evaluator.unlink()
        return result
    monkeypatch.setattr(gi.subprocess, "run", changing_child)
    admission = gi.produce_graft_length_evidence(sources, report, "synthetic-gappa", str(evaluator), {})
    assert admission["state"] == "HOLD_LENGTH_QA" and admission["selected"] is None
    assert "EVALUATION_EXECUTABLE_CHANGED_OR_UNAVAILABLE" in admission["reason"]
    record = json.loads(Path(admission["receipt"]).read_text())
    directory = next((Path(admission["receipt"]).parent / "evaluation").iterdir())
    command = json.loads((directory / "command.json").read_text())
    assert command["executable"]["sha256"] == before
    assert command["executable_identity_state"] == "CHANGED_OR_UNAVAILABLE"
    assert command["executable_after"] != command["executable"]
    assert command["resource_environment"]["OMP_THREAD_LIMIT"] == "1"
    assert (directory / "bestTree.newick").is_file()
    assert (directory / "stdout.log").read_text() == "final logLikelihood -12.3\n"
    assert record["state"] == "HOLD_LENGTH_QA"
    with pytest.raises(ValueError, match="HOLD"):
        gi.admit_graft_length_evidence(admission["receipt"], sources)
