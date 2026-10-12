"""Producer-to-consumer contracts, with no native tools or R rendering."""
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
Phylo = pytest.importorskip("Bio.Phylo")
from tools import graft_integrity as gi, placement_display as display, phylo_place as native
from .test_m5_restored_graft_receipt import produce, fixture_sources


def display_args(run, out):
    return [str(run), "--name", "synthetic", "--group", "synthetic", "--host-table", str(run / "host.tsv"),
            "--ref-source-db", str(run / "sources.sqlite"), "--out", str(out)]


@pytest.mark.parametrize("nested", [False, True])
def test_actual_layout_admission_selects_restored_not_coexisting_raw(tmp_path, monkeypatch, nested):
    run, report, sources, calls, admitted = produce(tmp_path, monkeypatch, nested=nested)
    actual = display._admit_run_layout(run)
    assert actual["selected"]["restored"] == admitted["selected"]["restored"]
    assert actual["selected"]["restored"] != actual["selected"]["raw"]
    assert Path(actual["selected"]["raw"]).is_file()


@pytest.mark.parametrize("case", ["missing", "malformed", "hold", "stale_source", "competing"])
def test_actual_display_frontdoor_refuses_before_output_or_builder(tmp_path, monkeypatch, case):
    run, report, sources, calls, admitted = produce(tmp_path, monkeypatch)
    receipt = Path(admitted["receipt"])
    if case == "missing":
        receipt.unlink()
    elif case == "malformed":
        receipt.write_text('{"schema":')
    elif case == "hold":
        value = json.loads(receipt.read_text()); value["state"] = "HOLD_LENGTH_QA"
        receipt.write_text(json.dumps(value))
    elif case == "stale_source":
        sources["model"].write_text("changed")
    else:
        competing = run / "report" / "graft_length_evidence" / "receipt.json"
        competing.parent.mkdir(parents=True)
        competing.write_bytes(receipt.read_bytes())
    original_load = display._load
    def guarded_load(name):
        assert name == "graft_integrity", "builder imported before length admission"
        return original_load(name)
    monkeypatch.setattr(display, "_load", guarded_load)
    out = tmp_path / "display"
    assert display.main(display_args(run, out)) == 2
    assert not out.exists()


def test_rooted_derivative_preserves_exact_restored_split_metrics(tmp_path, monkeypatch):
    run, report, sources, calls, admitted = produce(tmp_path, monkeypatch, default=True)
    src = Path(admitted["selected"]["restored"])
    before = src.read_bytes()
    output = tmp_path / "rooted.nwk"
    assert display.root_on_outgroup(src, output, "OG") == "OG"
    raw = Phylo.read(src, "newick"); rooted = Phylo.read(output, "newick")
    tips = gi._tips(raw)
    original, actual = gi._metric(raw, tips), gi._metric(rooted, tips)
    assert original.keys() == actual.keys()
    assert all(gi._close_length(actual[key][0], value[0]) for key, value in original.items())
    assert src.read_bytes() == before
    assert next(t.branch_length for t in rooted.get_terminals() if t.name == "QUERY") == pytest.approx(.0123456789, abs=1e-13)


def test_export_evidence_is_bound_and_excludes_alignment_payload(tmp_path, monkeypatch):
    run, report, sources, calls, admitted = produce(tmp_path, monkeypatch, default=True)
    out = tmp_path / "display"; out.mkdir()
    paths = display._length_audit_supplements(out, admitted, [])
    index = json.loads(paths[-1].read_text())
    assert index["receipt_sha256"] == admitted["receipt_sha256"]
    assert {item["role"] for item in index["files"]} >= {"receipt", "source/jplace", "source/model"}
    assert not {item["role"] for item in index["files"]} & {"source/reference_alignment", "source/query_alignment"}
    for item in index["files"]:
        assert display.digest(out / item["export_filename"]) == item["sha256"]


def test_export_collision_refuses_before_any_copy(tmp_path, monkeypatch):
    run, report, sources, calls, admitted = produce(tmp_path, monkeypatch)
    out = tmp_path / "display"; out.mkdir()
    first = tmp_path / "one"; first.mkdir(); (first / "HOST.tsv").write_text("one")
    second = tmp_path / "two"; second.mkdir(); (second / "host.tsv").write_text("two")
    with pytest.raises(ValueError, match="BASENAME_COLLISION"):
        display._length_audit_supplements(out, admitted, [first / "HOST.tsv", second / "host.tsv"])
    assert list(out.iterdir()) == []


def native_args(report, sources):
    return SimpleNamespace(outdir=str(report), jplace=str(sources["jplace"]),
                           refpkg=str(sources["reference_tree"].parent), taxonomy=None)


def setup_native(monkeypatch, tmp_path):
    monkeypatch.setattr(native, "_which", lambda command, env: "synthetic-gappa" if command == "gappa" else None)
    monkeypatch.setattr(native, "_env", lambda env: {})
    monkeypatch.setattr(native, "_dedup_summary", lambda path: None)
    monkeypatch.setattr(native, "ROOT", str(tmp_path / "no-signoff"))
    monkeypatch.setitem(sys.modules, "figure_methods", SimpleNamespace(
        caption=lambda *args, **kwargs: json.dumps(kwargs),
        detect_versions=lambda: pytest.fail("live version probe is not historical provenance")))


def test_native_hold_gates_every_tree_distance_consumer_and_returns_nonzero(tmp_path, monkeypatch):
    run, report, sources, calls = fixture_sources(tmp_path, monkeypatch)
    setup_native(monkeypatch, tmp_path)
    sources["reference_tree"].unlink()
    for name in ("_grafted_neighborhoods", "_render_tree", "_color_strips_deliverable"):
        monkeypatch.setattr(native, name, lambda *a, **k: pytest.fail("held tree consumed"))
    assert native.cmd_report(native_args(report, sources)) == 2
    assert (report / "synthetic_placements.tsv").is_file()
    readme = (report / "synthetic_PLACEMENT_README.md").read_text()
    assert "HOLD_LENGTH_QA" in readme
    assert "sits confidently" not in readme
    assert len(calls) == 0


def test_native_failed_current_render_never_selects_stale_derived_filename(tmp_path, monkeypatch):
    run, report, sources, calls = fixture_sources(tmp_path, monkeypatch)
    setup_native(monkeypatch, tmp_path)
    stale = report / "synthetic_placement_tree.rooted_split.newick"
    stale.write_text("historical stale evidence")
    consumed = []
    monkeypatch.setattr(native, "_grafted_neighborhoods", lambda path, *a, **k: consumed.append(path) or 0)
    def render(*args, **kwargs):
        assert kwargs["molecule"] == "nucleotide"
        raise ValueError("intentional synthetic render failure")
    monkeypatch.setattr(native, "_render_tree", render)
    def current_strips(a, outdir, grp, path, lm):
        consumed.append(path)
        return {"state": "NOT_REQUESTED", "requested": False, "variants": [], "artifacts": []}
    monkeypatch.setattr(native, "_color_strips_deliverable", current_strips)
    assert native.cmd_report(native_args(report, sources)) == 0
    assert len(consumed) == 2
    assert all(path.endswith("lengths_restored.newick") for path in consumed)
    assert stale.read_text() == "historical stale evidence"
    caption = (report / "synthetic_placement_FIGURE_CAPTION.txt").read_text()
    assert "synthetic nucleotide phylogenetic placement" in caption
    assert "PASS_LENGTH_QA" in caption


def test_all_propagates_actual_report_hold(tmp_path, monkeypatch):
    ref = tmp_path / "refpkg"; ref.mkdir(); (ref / "ref.tree").write_text("present")
    args = SimpleNamespace(threads=1, refpkg=str(ref), outdir=str(tmp_path / "place"))
    monkeypatch.setattr(native, "cmd_place", lambda a: 0)
    monkeypatch.setattr(native, "cmd_report", lambda a: 2)
    assert native.cmd_all(args) == 2


@pytest.mark.parametrize("case", ["traversal", "symlink", "malformed_source", "unknown_model", "mixed_refroot"])
def test_portable_receipt_layout_and_roster_refuse(tmp_path, monkeypatch, case):
    run, report, sources, calls, admitted = produce(tmp_path, monkeypatch)
    receipt = Path(admitted["receipt"])
    value = json.loads(receipt.read_text())
    if case == "traversal":
        value["selected"]["restored"] = "../outside.newick"
    elif case == "symlink":
        target = Path(admitted["selected"]["restored"])
        preserved = tmp_path / "preserved.newick"; target.rename(preserved); target.symlink_to(preserved)
    elif case == "malformed_source":
        value["sources"]["model"] = []
    elif case == "unknown_model":
        value["sources"]["model"]["creation_path"] = "/arbitrary/not-allowed.model"
    else:
        value["layout"]["reference_root"] = "."
    receipt.write_text(json.dumps(value))
    with pytest.raises((ValueError, OSError)):
        gi.admit_placement_run(run)


def test_actual_display_frontdoor_roots_admitted_restored_tree_before_build_boundary(tmp_path, monkeypatch):
    run, report, sources, calls, admitted = produce(tmp_path, monkeypatch, default=True)
    (run / "host.tsv").write_text("strain\taccession\n")
    (run / "sources.sqlite").write_text("synthetic metadata boundary only")
    builder = SimpleNamespace(_is_query=lambda name: name == "QUERY", _ref_accession=lambda name: name)
    original_load = display._load
    monkeypatch.setattr(display, "_load", lambda name: builder if name == "build_placement_ggtree_inputs" else original_load(name))
    monkeypatch.setattr(display, "_reference_organisms", lambda *a: {})
    invoked = []
    def boundary(argv, env=None):
        assert argv[1].endswith("build_placement_ggtree_inputs.py")
        tree = Phylo.read(argv[argv.index("--graft")+1], "newick")
        assert next(t.branch_length for t in tree.get_terminals() if t.name == "QUERY") == pytest.approx(.0123456789, abs=1e-13)
        invoked.append(argv)
        raise ValueError("INTENTIONAL_BUILD_BOUNDARY_STOP")
    monkeypatch.setattr(display, "_run", boundary)
    out = tmp_path / "display"
    assert display.main(display_args(run, out) + ["--outgroup-substr", "OG"]) == 2
    assert len(invoked) == 1
    assert (out / "rooted.nwk").is_file()
    assert not (out / "placement_display_receipt.json").exists()


def test_native_late_source_change_refuses_report_completion(tmp_path, monkeypatch):
    run, report, sources, calls = fixture_sources(tmp_path, monkeypatch)
    setup_native(monkeypatch, tmp_path)
    monkeypatch.setattr(native, "_grafted_neighborhoods", lambda *a, **k: 0)
    monkeypatch.setattr(native, "_render_tree", lambda *a, **k: None)
    def strips(*args):
        sources["model"].write_text("changed after rendering began")
    monkeypatch.setattr(native, "_color_strips_deliverable", strips)
    assert native.cmd_report(native_args(report, sources)) == 2
    assert (report / "LENGTH_ADMISSION_CHANGED.txt").is_file()


def test_methods_counts_use_actual_selected_restored_tree_and_bound_molecule(tmp_path, monkeypatch):
    run, report, sources, calls, admitted = produce(tmp_path, monkeypatch)
    out = tmp_path / "display"; out.mkdir()
    prefix = out / "synthetic"
    Path(str(prefix) + "_display.nwk").write_bytes(Path(admitted["selected"]["restored"]).read_bytes())
    # Poison the historical hardcoded path: selected-tree count must still be five.
    legacy = run / "report" / "epa_result.newick"; legacy.parent.mkdir(exist_ok=True)
    legacy.write_text("(WRONG:1,OTHER:1);")
    rows = [{"role": role, "category": "", "source": ""} for role in
            ("reference", "reference", "reference", "outgroup", "query")]
    args = SimpleNamespace(group="synthetic", name="synthetic", label_style="withloc", max_nt=1, min_cols=500,
                           keep_all_references=False, neighbors_per_query=2)
    ledger, methods = display.write_methods_package(
        run, out, prefix, sources["reference_alignment"], sources["query_alignment"], rows, [],
        "OG", args, 0, out / "plot.png", out / "plot.pdf", length_admission=admitted)
    record = json.loads(ledger.read_text())
    assert record["counts"]["analysis_tree_tips"] == 5
    assert record["workflow"].startswith("nucleotide ")
    assert record["length_admission"]["receipt_sha256"] == admitted["receipt_sha256"]
    assert "Numerical length state: `PASS_LENGTH_QA`" in methods.read_text()
