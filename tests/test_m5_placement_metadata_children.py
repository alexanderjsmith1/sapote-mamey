"""Actual builder and child reader contracts with independently written tiny outputs."""
import csv
import hashlib
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest
Phylo = pytest.importorskip("Bio.Phylo")
from tools import phylo_place as native
from tools import _placement_report_metadata as contract
from .test_trees_432_color_strips_report_deliverable import _fixture, _build, _tsv, TIPS, bpi
from .test_m5_placement_metadata_contract import positive, table, TIP, LABEL


def test_actual_builder_only_marks_reviewed_exact_tip_and_keeps_tree_bytes(tmp_path):
    _fixture(tmp_path)
    original_tree = (tmp_path/"tree.newick").read_bytes()
    fields = list(positive()) + ["source_category", "geography_category"]
    reviewed = table(tmp_path/"type.tsv", [positive(source_category="Marine-associated", geography_category="South America")], fields)
    result = _build(tmp_path, ["--reviewed", reviewed])
    panel = Path(result["dir"])
    metadata = {row["tip"]: row for row in _tsv(panel/"metadata.tsv")}
    assert metadata[TIP]["type_display"] == "Type"
    assert metadata[TIP]["label"] == "Genus alpha A1 [Type; Marine-associated; South America] (NR_000001.1)"
    assert all(not row["type_display"] for tip, row in metadata.items() if tip != TIP)
    assert (panel/"tree_input.newick").read_bytes() == original_tree
    assert (tmp_path/"tree.newick").read_bytes() == original_tree
    assert json.loads((panel/"TYPE_EVIDENCE.json").read_text())["roles"][TIP]["source_accession"] == "NR_000001.1"
    assert result["input_tips"] == [tip.name for tip in Phylo.read(tmp_path/"tree.newick", "newick").get_terminals()]
    assert set(result["kept_tips"]) | set(result["omitted_tips"]) == set(result["input_tips"])


def test_builder_invalid_positive_refuses_before_creating_parent(tmp_path):
    _fixture(tmp_path)
    reviewed = table(tmp_path/"badtype.tsv", [positive(source_accession="NR_000001.2")])
    with pytest.raises(ValueError, match="SOURCE_ACCESSION_UNBOUND"):
        _build(tmp_path, ["--reviewed", reviewed])
    assert not (tmp_path/"out").exists()


def strip_args(tmp_path):
    return SimpleNamespace(owner_table=[str(tmp_path/"owner.tsv")], owner_table_original=[],
                 resolved_metadata=[str(tmp_path/"resolved.tsv")], reviewed=[str(tmp_path/"reviewed.tsv")], query_override=[],
                 query_prefix="ZZ", rscript="selected-Rscript", threads=2, _report_query_names=["ZZ_101", "ZZ_102"],
                 _report_type_evidence=contract.reviewed_type_map([str(tmp_path/"reviewed.tsv")], TIPS, query_tips=["ZZ_101", "ZZ_102"]))


def fake_renderer(tmp_path, monkeypatch, *, fail_variant=None, missing=False, mutate_input=False):
    executable = tmp_path/"selected Rscript"; executable.write_text("synthetic executable identity only; never executed")
    monkeypatch.setattr(shutil, "which", lambda command: str(executable))
    calls = []
    def run(argv, **kwargs):
        child = Path(kwargs["cwd"]); variant = argv[-1]; calls.append((list(argv), kwargs))
        assert Path(argv[0]) == executable
        assert kwargs["env"]["OMP_NUM_THREADS"] == "2" and kwargs["env"]["OMP_THREAD_LIMIT"] == "2"
        assert kwargs["env"]["NUMEXPR_NUM_THREADS"] == "2"
        assert not (child/"RENDER_RECEIPT.json").exists()
        if variant == fail_variant:
            return SimpleNamespace(returncode=7)
        md = _tsv(child/"metadata.tsv")
        stem = f"EPAng_Genus_R04_{variant}"
        for ext in ("png", "pdf"):
            if not (missing and ext == "png"):
                (child/f"{stem}.{ext}").write_bytes(b"same synthetic image bytes for independent fresh children")
        (child/f"{stem}_caption.txt").write_text("synthetic rendered child caption")
        (child/"R_SESSION.txt").write_text("synthetic R boundary, no actual R execution")
        tree = Phylo.read(child/"tree_input.newick", "newick")
        keep = {row["tip"] for row in md}
        for tip in list(tree.get_terminals()):
            if tip.name not in keep:
                tree.prune(tip)
        Phylo.write(tree, child/"tree_display.newick", "newick", format_branch_length="%.17g")
        rows = []
        for row in md:
            label = row["label"] + (" {"+row["sample_id"]+"}" if variant == "experiment_id" and row["role"] == "query" and row["sample_id"] else "")
            rows.append(dict(tip=row["tip"],label=label,source=row["source_category"],geography=row["geography_category"],Candida=row["Candida"],MRSA=row["MRSA"]))
        table(child/f"{stem}_display_audit.tsv", rows)
        checks = ["tip_metadata_bijection", "retained_pairwise_branch_distances", "source_category_palette", "geography_category_palette"]
        table(child/f"{stem}_validation.tsv", [dict(check=name,status="PASS") for name in checks])
        if mutate_input:
            (child/"title.txt").write_text("changed input")
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(native.subprocess, "run", run)
    return calls


def execute_strips(tmp_path):
    return native._color_strips_deliverable(strip_args(tmp_path), str(tmp_path), "Genus", str(tmp_path/"tree.newick"), str(tmp_path/"labelmap.tsv"))


def test_two_fresh_variant_children_preserve_first_receipt_after_later_render(tmp_path, monkeypatch):
    _fixture(tmp_path); calls = fake_renderer(tmp_path, monkeypatch)
    result = execute_strips(tmp_path)
    assert result["state"] == "RENDERED_WITH_OMISSIONS" and len(calls) == 2
    assert result["kept"] == 4 and result["omitted"] == 4
    first, second = result["variants"]
    assert first["state"] == second["state"] == "RENDERED"
    assert first["receipt"] != second["receipt"]
    for child in (first, second):
        assert hashlib.sha256(Path(child["receipt"]).read_bytes()).hexdigest() == child["receipt_sha256"]
        for artifact in child["artifacts"]:
            assert hashlib.sha256(Path(artifact["path"]).read_bytes()).hexdigest() == artifact["sha256"]
    # Identical byte output is still a current fresh child, not inferred from changed hashes.
    first_png = next(item for item in first["artifacts"] if item["path"].endswith(".png"))
    second_png = next(item for item in second["artifacts"] if item["path"].endswith(".png"))
    assert first_png["sha256"] == second_png["sha256"]
    before = {str(path): path.read_bytes() for path in (tmp_path/"color_strips").rglob("*") if path.is_file()}
    refused = execute_strips(tmp_path)
    assert refused["state"] == "HOLD_OUTPUT_EXISTS" and len(calls) == 2
    assert before == {str(path): path.read_bytes() for path in (tmp_path/"color_strips").rglob("*") if path.is_file()}


@pytest.mark.parametrize("kind", ["second_failure", "missing_output", "changed_input"])
def test_requested_child_failure_is_visible_and_never_claimed_rendered(tmp_path, monkeypatch, kind):
    _fixture(tmp_path)
    calls = fake_renderer(tmp_path, monkeypatch, fail_variant="experiment_id" if kind == "second_failure" else None,
                          missing=kind == "missing_output", mutate_input=kind == "changed_input")
    result = execute_strips(tmp_path)
    assert result["state"] == "HOLD_REQUESTED_STRIPS" and result["requested"]
    assert result["variants"][-1]["state"] == "HOLD"
    receipt = json.loads(Path(result["receipt"]).read_text())
    assert receipt["state"] == "HOLD_REQUESTED_STRIPS"
    if kind == "second_failure":
        assert result["variants"][0]["state"] == "RENDERED" and len(calls) == 2
    else:
        assert len(calls) == 1 and result["artifacts"] == []


def test_nearest_type_requires_evidence_and_nearest_any_distances_stay_unchanged(tmp_path):
    tree = tmp_path/"metric.nwk"; tree.write_text(f"(({TIP}:0.1,PUBLIC_QUERY_01:0.2):0.3,OTHER:0.4);")
    unknown = tmp_path/"unknown.tsv"; reviewed = tmp_path/"reviewed.tsv"
    native._grafted_neighborhoods(str(tree), {TIP: LABEL}, str(unknown), query_names={"PUBLIC_QUERY_01"})
    native._grafted_neighborhoods(str(tree), {TIP: LABEL}, str(reviewed), query_names={"PUBLIC_QUERY_01"}, type_evidence={"roles": {TIP: positive()}})
    a, b = _tsv(unknown)[0], _tsv(reviewed)[0]
    assert a["nearest_type_strain"] == a["patristic_dist"] == ""
    assert b["nearest_type_strain"] and b["patristic_dist"] == "0.3000"
    assert a["nearest_reference_any"] == b["nearest_reference_any"]
    assert a["nearest_reference_dist"] == b["nearest_reference_dist"] == "0.3000"


def test_python_renderer_uses_admitted_type_map_not_accession_prefix(tmp_path, monkeypatch):
    tree = tmp_path/"tiny.nwk"; tree.write_text(f"(({TIP}:0.1,PUBLIC_QUERY_01:0.2):0.3,OTHER:0.4);")
    original = tree.read_bytes()
    monkeypatch.setattr(native, "_graft_sane", lambda *args: (True, "synthetic metric already admitted"))
    for name, proof, expected in [("unknown", None, "reference_nontype"), ("reviewed", {"roles": {TIP: positive()}}, "reference_type")]:
        result = native._render_tree(str(tree), {TIP: LABEL}, str(tmp_path/f"{name}.png"), str(tmp_path/f"{name}.svg"),
                                     "synthetic", query_names={"PUBLIC_QUERY_01"}, molecule="nucleotide", type_evidence=proof)
        assert result["state"] == "PRODUCED_DIAGNOSTIC"
        labels = json.loads((tmp_path/f"{name}.svg.labels.json").read_text())
        assert labels["roles"][TIP] == expected
        assert labels["roles"]["PUBLIC_QUERY_01"] == "query"
        assert labels["role_basis"]["reference_type"] == "explicit reviewed exact native-tip/source-sequence type evidence"
        assert len(result["artifacts"]) == 3
    assert tree.read_bytes() == original


def test_portable_label_does_not_reanimate_legacy_role_without_admitted_map():
    from tools import placement_display
    row = dict(tip=TIP, ref_label=LABEL, reference_species="Genus alpha", reference_habitat="Soil",
               reference_source="soil", reference_country="Italy", reference_role="type_reference", type_strain_of="Genus alpha")
    unknown = placement_display._publication_reference_label(row)
    reviewed = placement_display._publication_reference_label(row, type_evidence={"roles": {TIP: positive()}})
    assert "type strain" not in unknown
    assert "type strain of Genus alpha" in reviewed
    # Publication labels intentionally compact accession versions; proof retains the exact sequence.
    assert "(NR_000001)" in unknown and "(NR_000001)" in reviewed


def test_portable_actual_frontdoor_invalid_type_proof_refuses_before_output(tmp_path, monkeypatch):
    from tools import placement_display
    from .test_m5_restored_graft_receipt import produce
    from .test_m5_placement_display_length_admission import display_args
    run, report, sources, calls, admitted = produce(tmp_path, monkeypatch)
    (run/"host.tsv").write_text("strain\taccession\n")
    (run/"sources.sqlite").write_text("synthetic metadata boundary only")
    original_load = placement_display._load
    builder = SimpleNamespace(_is_query=lambda tip: tip == "QUERY", _ref_accession=lambda tip: tip)
    monkeypatch.setattr(placement_display, "_load", lambda name: builder if name == "build_placement_ggtree_inputs" else original_load(name))
    monkeypatch.setattr(placement_display, "_reference_organisms", lambda *args: {})
    role = table(tmp_path/"unbound-role.tsv", [dict(accession="REF_A", role="type_reference", tip="REF_A")])
    monkeypatch.setattr(placement_display, "_run", lambda *args: pytest.fail("builder invoked before type admission"))
    out = tmp_path/"display"
    assert placement_display.main(display_args(run, out) + ["--reference-role-table", role]) == 2
    assert not out.exists()
    assert Path(admitted["receipt"]).is_file()


def test_explicit_selected_real_r_renderer_synthetic_saved_geometry(tmp_path, monkeypatch):
    """Opt-in root-scheduled graphics gate; an explicitly selected broken R runtime fails."""
    import os
    import subprocess
    selected = os.environ.get("SAPOTE_TEST_RSCRIPT")
    if not selected:
        pytest.skip("real R graphics gate requires coordinator-selected SAPOTE_TEST_RSCRIPT; not validated by fake-child tests")
    executable = Path(selected).resolve(strict=True)
    assert executable.is_file()
    _fixture(tmp_path)
    result = _build(tmp_path)
    panel = Path(result["dir"])
    source = Path(native.__file__).parent/"render_placement_COLOR_STRIPS.R"
    metadata = {row["tip"]: row for row in _tsv(panel/"metadata.tsv")}
    env = dict(os.environ)
    from tools import graft_integrity as gi
    env.update({key: "1" for key in gi.RESOURCE_KEYS})
    receipts = []
    for variant in ("concise", "experiment_id"):
        child = panel/"renders"/variant/"Genus"; child.mkdir(parents=True)
        for name in result["input_files"]:
            shutil.copyfile(panel/name, child/name)
        shutil.copyfile(source, child/source.name)
        with (child/"render.log").open("x") as log:
            completed = subprocess.run([str(executable), str(child/source.name), variant], cwd=str(child), env=env,
                                       stdout=log, stderr=subprocess.STDOUT, timeout=120)
        assert completed.returncode == 0, (child/"render.log").read_text()
        artifacts = native._strip_artifacts_checked(child, "Genus", variant, metadata)
        caption = (child/f"EPAng_Genus_R04_{variant}_caption.txt").read_text()
        assert "Displayed 4 of 8 source tips and 1 of 2 query tips" in caption
        assert "accession prefixes do not establish type material" in caption
        assert "Length evidence state: NOT_RECORDED" in caption
        receipts.append(artifacts)
    assert len(receipts) == 2
