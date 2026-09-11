import json
from pathlib import Path
import subprocess
import pytest
from tools.graft_integrity import generate_checked_graft, verify_graft


def inputs(tmp_path, tree="((RefA:0.25,query_any_name:0.123456789):0.75,RefB:0.4);"):
    jp = tmp_path / "input.jplace"
    jp.write_text(json.dumps({"tree": "(RefA:1{0},RefB:0.4{1}):0{2};",
        "version": 3, "metadata": {},
        "fields": ["edge_num", "likelihood", "like_weight_ratio", "distal_length", "pendant_length"],
        "placements": [{"n": ["query_any_name"], "p": [[0, -1, 1, .25, .123456789]]}]}))
    graft = tmp_path / "input.newick"
    graft.write_text(tree)
    return graft, jp


def test_split_edge_preserved_byte_for_byte(tmp_path):
    graft, jp = inputs(tmp_path)
    before = graft.read_bytes()
    assert verify_graft(graft, jp)["status"] == "PASS"
    assert graft.read_bytes() == before


@pytest.mark.parametrize("tree", [
    "((RefA:1,query_any_name:0.123456789):0.75,RefB:0.4);",
    "((RefA:0.25,query_any_name:0.9):0.75,RefB:0.4);",
    "((RefA:0.25,query_any_name:0.123456789):0.75,Other:0.4);",
    "((RefA:0.25,RefA:0.1):0.75,RefB:0.4);",
    "((RefA:-0.25,query_any_name:0.123456789):1.25,RefB:0.4);",
    "((RefA,query_any_name:0.123456789):0.75,RefB:0.4);",
    "(RefA:1,RefB:0.4);",
])
def test_bad_tree_refused_without_mutation(tmp_path, tree):
    graft, jp = inputs(tmp_path, tree)
    before = graft.read_bytes()
    with pytest.raises(ValueError):
        verify_graft(graft, jp)
    assert graft.read_bytes() == before


def test_repeated_number_is_not_a_placeholder(tmp_path):
    graft, jp = inputs(tmp_path, "((RefA:0.105360516,query_any_name:0.123456789):0.894639484,RefB:0.4);")
    assert verify_graft(graft, jp)["status"] == "PASS"


def test_zero_length_backbone_and_nm_names(tmp_path):
    graft, jp = inputs(tmp_path, "((RefA:0,query_any_name:0.123456789):0,RefB:0.4);")
    data = json.loads(jp.read_text())
    data["tree"] = "(RefA:0{0},RefB:0.4{1}):0{2};"
    data["placements"][0]["nm"] = [["query_any_name", 5]]
    del data["placements"][0]["n"]
    jp.write_text(json.dumps(data))
    assert verify_graft(graft, jp)["status"] == "PASS"


@pytest.mark.parametrize("kind", ["collision", "duplicate", "empty", "nan"])
def test_bad_placement_refused(tmp_path, kind):
    graft, jp = inputs(tmp_path)
    data = json.loads(jp.read_text())
    item = data["placements"][0]
    if kind == "collision": item["n"] = ["RefA"]
    if kind == "duplicate": item["n"] *= 2
    if kind == "empty": item["p"] = []
    if kind == "nan": item["p"][0][2] = float("nan")
    jp.write_text(json.dumps(data))
    with pytest.raises(ValueError): verify_graft(graft, jp)


@pytest.mark.parametrize("failure", ["exit", "empty", "ambiguous", "invalid", "success"])
def test_generation_is_transactional(tmp_path, monkeypatch, failure):
    graft, jp = inputs(tmp_path)
    original = graft.read_bytes()
    def run(command, **kwargs):
        assert kwargs["check"] is True and "--fully-resolve" in command
        stage = Path(command[command.index("--out-dir") + 1])
        if failure == "exit": raise subprocess.CalledProcessError(2, command)
        if failure == "empty": return
        (stage / graft.name).write_bytes(original if failure != "invalid" else b"(Wrong:1);")
        if failure == "ambiguous": (stage / "other.newick").write_bytes(original)
    monkeypatch.setattr(subprocess, "run", run)
    if failure == "success":
        assert generate_checked_graft("gappa", jp, tmp_path, {}) == str(graft)
    else:
        with pytest.raises((ValueError, subprocess.CalledProcessError)):
            generate_checked_graft("gappa", jp, tmp_path, {})
    assert graft.read_bytes() == original
    assert not list(tmp_path.glob(".graft-check-*"))


def test_internal_topology_mismatch(tmp_path):
    graft, jp = inputs(tmp_path, "((RefA:1,RefC:0.2):0.3,(RefB:0.4,query_any_name:0.123456789):0);")
    data = json.loads(jp.read_text())
    data["tree"] = "((RefA:1{0},RefB:0.4{1}):0.3{2},RefC:0.2{3}):0{4};"
    jp.write_text(json.dumps(data))
    with pytest.raises(ValueError): verify_graft(graft, jp)


def test_multiple_query_insertions_share_one_reference_edge(tmp_path):
    graft, jp = inputs(tmp_path, "(((RefA:0.25,query_any_name:0.123456789):0.25,query_two:0.2):0.5,RefB:0.4);")
    data = json.loads(jp.read_text())
    data["placements"].append({"n": ["query_two"], "p": [[0, -1, 1, .5, .2]]})
    jp.write_text(json.dumps(data))
    assert verify_graft(graft, jp)["query_tips"] == 2


def test_report_aborts_before_consumers_on_graft_failure(tmp_path, monkeypatch):
    import importlib.util
    from types import SimpleNamespace
    import tools.graft_integrity as integrity
    source = Path(__file__).resolve().parents[1] / "tools/phylo_place.py"
    spec = importlib.util.spec_from_file_location("graft_report_integration", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    graft, jp = inputs(tmp_path)
    before = graft.read_bytes()
    monkeypatch.setattr(module, "_which", lambda *a: "gappa")
    def fail(*a): raise ValueError("GRAFT_INTEGRITY: synthetic refusal")
    def consumed(*a): pytest.fail("downstream consumer ran after graft refusal")
    monkeypatch.setattr(integrity, "generate_checked_graft", fail)
    monkeypatch.setattr(module, "_jplace_besthit_tsv", consumed)
    monkeypatch.setattr(module, "_grafted_neighborhoods", consumed)
    args = SimpleNamespace(outdir=str(tmp_path), jplace=str(jp), refpkg=None, taxonomy=None)
    with pytest.raises(ValueError, match="synthetic refusal"):
        module.cmd_report(args)
    assert graft.read_bytes() == before
