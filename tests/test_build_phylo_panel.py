import csv
import importlib.util
import json
import pathlib
import sys
import zipfile

import pytest


TOOL = pathlib.Path(__file__).parents[1] / "tools" / "build_phylo_panel.py"
SPEC = importlib.util.spec_from_file_location("build_phylo_panel", TOOL)
mod = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mod
SPEC.loader.exec_module(mod)


def fasta(seq, name="x"):
    return f">{name}\n{seq}\n"


def write_manifest(path, rows):
    fields = ["candidate_id", "role", "source_path", "source_member", "priority",
              "cohort", "taxonomy", "display_label", "tree_label", "selection_basis",
              "related_query_ids", "reference_status", "assembly_fromtype"]
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, delimiter="\t", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def test_panel_size_options_are_visible_and_capped():
    assert mod.panel_size(None) == 40
    assert [mod.panel_size(x) for x in (20, 40, 60, 37)] == [20, 40, 60, 37]
    with pytest.raises(mod.PanelError, match="hard maximum 60"):
        mod.panel_size(61)


def test_show_options_needs_no_manifest(capsys):
    assert mod.main(["--show-options"]) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["preset_total_tips"] == [20, 40, 60]
    assert shown["default_total_tips"] == 40
    assert shown["hard_max_total_tips"] == 60


def test_reference_requires_explicit_basis_and_query_link(tmp_path):
    f = tmp_path / "r.fna"
    f.write_text(fasta("ACGT"))
    manifest = tmp_path / "m.tsv"
    write_manifest(manifest, [{"candidate_id": "R1", "role": "REFERENCE", "source_path": f}])
    with pytest.raises(mod.PanelError, match="selection_basis and related_query_ids"):
        mod.read_manifest(manifest)


def test_relative_source_paths_are_resolved_from_manifest_directory(tmp_path):
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "q.fna").write_text(fasta("ACGT"))
    manifest = tmp_path / "m.tsv"
    write_manifest(manifest, [{"candidate_id": "Q", "role": "QUERY",
                               "source_path": "sources/q.fna"}])
    assert mod.read_manifest(manifest)[0].source_path == (sources / "q.fna").resolve()


def test_antismash_zip_member_provenance_and_exact_content_dedup(tmp_path):
    q = tmp_path / "as.fna"
    q.write_text(fasta("ACGTACGT", "different_header"))
    sid_zip = tmp_path / "sid_antismash.zip"
    with zipfile.ZipFile(sid_zip, "w") as zf:
        zf.writestr("SID10815/SID10815.gbk", "LOCUS x\nORIGIN\n        1 acgtacgt\n//\n")
        zf.writestr("SID10815/region001.gbk", "LOCUS r\nORIGIN\n        1 aaaa\n//\n")
    outgroup = tmp_path / "out.fna"
    outgroup.write_text(fasta("TTTTCCCC"))
    ref = tmp_path / "ref.fna"
    ref.write_text(fasta("AAAACCCC"))
    manifest = tmp_path / "m.tsv"
    write_manifest(manifest, [
        {"candidate_id": "AS-921", "role": "QUERY", "source_path": q,
         "priority": 1, "taxonomy": "Streptomyces sp.", "cohort": "AS"},
        {"candidate_id": "SID10815", "role": "QUERY", "source_path": sid_zip,
         "source_member": "SID10815/SID10815.gbk", "priority": 2, "cohort": "SID"},
        {"candidate_id": "OUT", "role": "OUTGROUP", "source_path": outgroup},
        {"candidate_id": "REF1", "role": "REFERENCE", "source_path": ref,
         "selection_basis": "curator-supplied comparator accession", "related_query_ids": "AS-921"},
    ])
    receipt = mod.build(manifest, tmp_path / "panel", 3, 3)
    assert receipt["selected_count"] == 3
    assert receipt["exact_content_duplicate_count"] == 1
    assert receipt["exact_content_duplicates"][0]["candidate_id"] == "SID10815"
    rows = list(csv.DictReader((tmp_path / "panel/panel_candidates.tsv").open(), delimiter="\t"))
    sid = next(r for r in rows if r["candidate_id"] == "SID10815")
    assert sid["resolved_member"] == "SID10815/SID10815.gbk"
    assert sid["decision"] == "EXCLUDED_DUPLICATE"
    cross = list(csv.DictReader((tmp_path / "panel/label_crosswalk.tsv").open(), delimiter="\t"))
    assert next(r for r in cross if r["candidate_id"] == "AS-921")["display_label"] == "Streptomyces sp. AS-921"


def test_gtotree_labels_are_two_columns_headerless_and_use_staged_filenames(tmp_path):
    q, o, r = tmp_path / "q.fna", tmp_path / "o.fna", tmp_path / "r.fna"
    q.write_text(fasta("AAAA")); o.write_text(fasta("CCCC")); r.write_text(fasta("GGGG"))
    manifest = tmp_path / "m.tsv"
    write_manifest(manifest, [
        {"candidate_id": "AS-441", "role": "QUERY", "source_path": q,
         "tree_label": "Streptomyces_sp_AS-441"},
        {"candidate_id": "OUT", "role": "OUTGROUP", "source_path": o,
         "tree_label": "Sister_genus_OUTGROUP"},
        {"candidate_id": "REF", "role": "REFERENCE", "source_path": r,
         "tree_label": "Streptomyces_reference_1",
         "selection_basis": "curator-supplied comparator", "related_query_ids": "AS-441"},
    ])
    receipt = mod.build(manifest, tmp_path / "panel", 3, 3)
    lines = (tmp_path / "panel/labels.tsv").read_text().splitlines()
    fields = [line.split("\t") for line in lines]
    assert len(fields) == 3
    assert all(len(row) == 2 for row in fields)
    assert fields[0] != ["staged_filename", "tree_label"]
    assert {row[0] for row in fields} == {
        "Streptomyces_sp_AS-441.fna", "Sister_genus_OUTGROUP.fna",
        "Streptomyces_reference_1.fna",
    }
    assert all(mod.safe_tree_label(row[1]) == row[1] for row in fields)
    assert receipt["gtotree_label_map"]["format"] == "two tab-separated columns, no header"
    assert receipt["gtotree_label_map"]["human_crosswalk_is_not_gtotree_m_input"] is True


def test_related_reference_cap_is_three(tmp_path):
    paths = {}
    for i, seq in enumerate(("AAAA", "CCCC", "GGGG", "TTTT", "ACAC", "GTGT")):
        paths[i] = tmp_path / f"g{i}.fna"
        paths[i].write_text(fasta(seq))
    rows = [
        {"candidate_id": "AS-1", "role": "QUERY", "source_path": paths[0]},
        {"candidate_id": "OUT", "role": "OUTGROUP", "source_path": paths[1]},
    ]
    for i in range(4):
        rows.append({"candidate_id": f"R{i}", "role": "REFERENCE", "source_path": paths[i + 2],
                     "priority": i, "selection_basis": "explicit candidate comparator",
                     "related_query_ids": "AS-1"})
    manifest = tmp_path / "m.tsv"
    write_manifest(manifest, rows)
    receipt = mod.build(manifest, tmp_path / "panel", 5, 3)
    assert receipt["selected_role_counts"] == {"QUERY": 1, "REFERENCE": 3, "OUTGROUP": 1}
    candidates = list(csv.DictReader((tmp_path / "panel/panel_candidates.tsv").open(), delimiter="\t"))
    assert next(r for r in candidates if r["candidate_id"] == "R3")["decision"] == "EXCLUDED_RELATED_CAP"


def test_insufficient_candidates_fails_instead_of_silent_short_panel(tmp_path):
    q, o = tmp_path / "q.fna", tmp_path / "o.fna"
    q.write_text(fasta("AAAA")); o.write_text(fasta("CCCC"))
    manifest = tmp_path / "m.tsv"
    write_manifest(manifest, [
        {"candidate_id": "AS-1", "role": "QUERY", "source_path": q},
        {"candidate_id": "OUT", "role": "OUTGROUP", "source_path": o},
    ])
    candidates = mod.read_manifest(manifest)
    for c in candidates:
        mod.load_candidate_sequences(c)
    with pytest.raises(mod.PanelError, match="fill 2/20"):
        mod.select_panel(candidates, 20, 3)


def test_receipt_is_json_and_tool_does_not_run_tree_software(tmp_path):
    text = TOOL.read_text()
    assert "import subprocess" not in text
    assert "os.system" not in text
    assert "subprocess.run" not in text


def _anchor_manifest(tmp_path, anchors):
    """TST-1 + outgroup + three ordinary references for TST-1 (the related cap is full), then anchors."""
    seqs = iter(("AAAA", "CCCC", "GGGG", "TTTT", "ACAC", "GTGT", "AGAG", "CTCT"))
    def genome(name):
        f = tmp_path / f"{name}.fna"
        f.write_text(fasta(next(seqs)))
        return f
    rows = [
        {"candidate_id": "TST-1", "role": "QUERY", "source_path": genome("TST-1")},
        {"candidate_id": "OUT", "role": "OUTGROUP", "source_path": genome("OUT")},
    ]
    for i in range(3):
        rows.append({"candidate_id": f"R{i}", "role": "REFERENCE", "source_path": genome(f"R{i}"),
                     "priority": i, "selection_basis": "mlsa_prune_k3", "related_query_ids": "TST-1"})
    for cid, fromtype in anchors:
        rows.append({"candidate_id": cid, "role": "REFERENCE", "source_path": genome(cid),
                     "selection_basis": "nearest_type_strain_ani", "related_query_ids": "TST-1",
                     "assembly_fromtype": fromtype})
    manifest = tmp_path / "m.tsv"
    write_manifest(manifest, rows)
    return manifest


def test_type_anchor_is_added_past_the_related_cap_and_listed_apart(tmp_path):
    manifest = _anchor_manifest(tmp_path, [("T1", "assembly from type material")])
    receipt = mod.build(manifest, tmp_path / "panel", 6, 3)
    assert receipt["selected_candidate_ids"] == ["TST-1", "OUT", "R0", "R1", "R2", "T1"]
    assert [a["candidate_id"] for a in receipt["type_anchors"]] == ["T1"]
    selected = list(csv.DictReader((tmp_path / "panel/panel_selected.tsv").open(), delimiter="\t"))
    assert [r["candidate_id"] for r in selected if r["type_anchor"] == "yes"] == ["T1"]
    assert all(r["role"] in {"QUERY", "REFERENCE", "OUTGROUP"} for r in selected)


def test_type_anchor_counts_toward_the_panel_total_and_never_displaces_a_reference(tmp_path):
    manifest = _anchor_manifest(tmp_path, [("T1", "assembly from type material")])
    receipt = mod.build(manifest, tmp_path / "panel", 5, 3)
    assert receipt["selected_candidate_ids"] == ["TST-1", "OUT", "R0", "R1", "R2"]
    candidates = list(csv.DictReader((tmp_path / "panel/panel_candidates.tsv").open(), delimiter="\t"))
    assert next(r for r in candidates if r["candidate_id"] == "T1")["decision"] == "EXCLUDED_PANEL_FULL"


def test_related_plus_anchors_never_exceed_four_per_query(tmp_path):
    manifest = _anchor_manifest(tmp_path, [("T1", "assembly from type material"),
                                           ("T2", "assembly from type material")])
    candidates = mod.read_manifest(manifest)
    for c in candidates:
        mod.load_candidate_sequences(c)
    selected = mod.select_panel(candidates, 6, 3, 2)
    assert [c.candidate_id for c in selected] == ["TST-1", "OUT", "R0", "R1", "R2", "T1"]
    assert next(c for c in candidates if c.candidate_id == "T2").decision == "EXCLUDED_COMPARATOR_CEILING"


@pytest.mark.parametrize("fromtype", ["", "not type material", "assembly from synonym type material"])
def test_type_anchor_without_type_material_is_refused(tmp_path, fromtype):
    manifest = _anchor_manifest(tmp_path, [("T1", fromtype)])
    with pytest.raises(mod.PanelError, match="type anchor requires assembly_fromtype"):
        mod.read_manifest(manifest)


def test_plan_step_accepts_a_staged_type_anchor_but_not_a_forged_one(tmp_path):
    plan_path = pathlib.Path(__file__).parents[1] / "tools" / "plan_gtotree_iqtree.py"
    spec = importlib.util.spec_from_file_location("plan_gtotree_iqtree_anchor_test", plan_path)
    plan = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = plan
    spec.loader.exec_module(plan)
    manifest = _anchor_manifest(tmp_path, [("T1", "assembly from type material")])
    mod.build(manifest, tmp_path / "panel", 6, 3)
    rows, meta = plan.read_prepared_panel(tmp_path / "panel", 3)
    assert meta["role_counts"] == {"QUERY": 1, "REFERENCE": 4, "OUTGROUP": 1}
    selected = tmp_path / "panel/panel_selected.tsv"
    selected.write_text(selected.read_text().replace("assembly from type material", "not type material"))
    with pytest.raises(ValueError, match="type anchor needs"):
        plan.read_prepared_panel(tmp_path / "panel", 3)
