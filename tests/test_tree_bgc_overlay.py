from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("tree_bgc_overlay", ROOT / "tools" / "tree_bgc_overlay.py")
ov = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(ov)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tsv(path: Path, fields: list[str], rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(fields); writer.writerows(rows)


def _fixture(tmp_path: Path, output: str = "tree-output-a") -> Path:
    source = tmp_path / "source"
    source.mkdir(exist_ok=True)
    files = {
        "tree": source / "final.treefile",
        "alignment": source / "alignment.fasta",
        "tree_workflow_receipt": source / "workflow.json",
        "model_receipt": source / "model.json",
        "seed_receipt": source / "seed.json",
        "outgroup_roster": source / "outgroup.tsv",
        "final_tip_roster": source / "tip_roster.tsv",
        "tip_crosswalk": source / "crosswalk.tsv",
        "annotation_matrix": source / "annotations.tsv",
    }
    files["tree"].write_text("((tip_one:0.1,tip_two:0.2)95:0.3,tip_out:0.5)100;\n", encoding="utf-8")
    files["alignment"].write_text(">tip_one\nACGT\n>tip_two\nACGA\n>tip_out\nTCGA\n", encoding="utf-8")
    files["tree_workflow_receipt"].write_text(json.dumps({"tree_channel": "MLSA_PROTEIN5", "tool": "IQ-TREE 3"}), encoding="utf-8")
    files["model_receipt"].write_text(json.dumps({"model": "GTR+F+I+G4"}), encoding="utf-8")
    files["seed_receipt"].write_text(json.dumps({"seed": "12345"}), encoding="utf-8")
    _tsv(files["outgroup_roster"], ["newick_label"], [["tip_out"]])
    _tsv(files["final_tip_roster"], ["newick_label", "state", "reason"], [
        ["tip_one", "INCLUDED", "final roster"],
        ["tip_two", "INCLUDED", "final roster"],
        ["tip_out", "INCLUDED", "curator-nominated outgroup"],
        ["tip_held", "OMITTED", "typed assembly hold"],
    ])
    _tsv(files["tip_crosswalk"], ["newick_label", "strain", "display_label", "role", "genus"], [
        ["tip_one", "strain-one", "Genus alpha strain one", "STUDY", "Genus alpha"],
        ["tip_two", "strain-two", "Genus alpha strain two", "STUDY", "Genus alpha"],
        ["tip_out", "strain-out", "Genus beta reference", "OUTGROUP", "Genus beta"],
        ["tip_held", "strain-held", "Genus alpha held", "STUDY", "Genus alpha"],
    ])
    _tsv(files["annotation_matrix"], ["strain", "channel", "feature", "value", "state"], [
        ["strain-one", "ANI", "nearest_reference_percent", 94.1, "OBSERVED"],
        ["strain-two", "ANI", "nearest_reference_percent", 93.8, "OBSERVED"],
        ["strain-out", "ANI", "nearest_reference_percent", "", "NOT_APPLICABLE"],
        ["strain-one", "BGC", "class_count", 7, "OBSERVED"],
        ["strain-two", "BGC", "class_count", 5, "OBSERVED"],
        ["strain-out", "BGC", "class_count", 4, "OBSERVED"],
        ["strain-one", "DOMAIN", "feature_count", 12, "OBSERVED"],
        ["strain-two", "DOMAIN", "feature_count", "", "NOT_MEASURED"],
        ["strain-out", "DOMAIN", "feature_count", 3, "OBSERVED"],
        ["strain-one", "MODE_B", "complete_count", 2, "OBSERVED"],
        ["strain-two", "MODE_B", "complete_count", 1, "OBSERVED"],
        ["strain-out", "MODE_B", "complete_count", "", "NOT_APPLICABLE"],
    ])
    config = {
        "schema_version": "sapote.tree-figure-factory.v1",
        "tree_channel": "MLSA_PROTEIN5",
        "annotation_scope": "STRAIN_AGGREGATE_ONLY",
        "external_data_root": str(source),
        "output_dir": output,
        "figure_question": "How do separate strain-level evidence tracks align to the recorded tree?",
        "inputs": [{"role": role, "logical_locator": path.name, "sha256": _sha(path)} for role, path in files.items()],
        "methods": {
            "tool": "IQ-TREE 3", "model": "GTR+F+I+G4", "seed": "12345",
            "outgroup": "tip_out", "support": "recorded internal labels",
            "source_release": "generic-phylogeny-fixture-v1",
            "software_versions": "tree Figure Factory candidate v1",
        },
        "owner_notes": ["Internal typography preference only."],
    }
    config_path = tmp_path / f"config-{output}.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return config_path


def test_hash_bound_tree_consumer_is_deterministic_vector_and_explicit(tmp_path: Path) -> None:
    first = ov.build_publication(_fixture(tmp_path, "tree-output-a"))
    second = ov.build_publication(_fixture(tmp_path, "tree-output-b"))
    assert {row["logical_locator"]: row["sha256"] for row in first["outputs"]} == {
        row["logical_locator"]: row["sha256"] for row in second["outputs"]
    }
    assert first["tree_channel"] == "MLSA_PROTEIN5"
    assert first["tip_counts"] == {"included": 3, "omitted": 1}
    assert first["channel_separation"] == ["ANI", "BGC", "DOMAIN", "MODE_B"]
    assert all(profile["svg"]["vector_preserved"] for profile in first["profiles"])
    assert all(profile["png"]["effective_dpi"] >= 300 for profile in first["profiles"])
    assert all(
        profile["layout"]["tick_label_data_clearance"]["status"] == "PASS"
        for profile in first["profiles"]
    )
    assert all(
        profile["layout"]["tick_label_data_clearance"]["axis_ids"] == ["tracks"]
        for profile in first["profiles"]
    )
    output = tmp_path / "tree-output-a"
    svg = (output / "tree_bgc_overlay_double_column.svg").read_text(encoding="utf-8")
    assert "<text" in svg and "Genus alpha strain one" in svg
    assert "tip_held" not in svg and "strain-held" not in svg
    omitted = (output / "tree_bgc_overlay_omitted_tips.tsv").read_text(encoding="utf-8")
    assert "tip_held" in omitted and "typed assembly hold" in omitted
    caption = (output / "tree_bgc_overlay_caption_methods.json").read_text(encoding="utf-8")
    assert "Internal typography preference" not in caption
    assert "MLSA/core-genome topology equivalence is not asserted" in caption


def test_crosswalk_duplicates_unmapped_tips_and_hash_drift_refuse(tmp_path: Path) -> None:
    config_path = _fixture(tmp_path)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    crosswalk = Path(config["external_data_root"]) / "crosswalk.tsv"
    with crosswalk.open("a", encoding="utf-8") as handle:
        handle.write("tip_one\tstrain-extra\tExtra\tREFERENCE\tGenus alpha\n")
    next(row for row in config["inputs"] if row["role"] == "tip_crosswalk")["sha256"] = _sha(crosswalk)
    config_path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate crosswalk newick_label"):
        ov.build_publication(config_path)
    assert not (tmp_path / "tree-output-a").exists()

    config_path = _fixture(tmp_path, "tree-output-b")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    roster = Path(config["external_data_root"]) / "tip_roster.tsv"
    roster.write_text(roster.read_text(encoding="utf-8").replace("tip_held\tOMITTED", "tip_held\tINCLUDED"), encoding="utf-8")
    next(row for row in config["inputs"] if row["role"] == "final_tip_roster")["sha256"] = _sha(roster)
    config_path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="tree tips must equal"):
        ov.build_publication(config_path)

    config_path = _fixture(tmp_path, "tree-output-c")
    config = json.loads(config_path.read_text(encoding="utf-8"))
    next(row for row in config["inputs"] if row["role"] == "tree")["sha256"] = "0" * 64
    config_path.write_text(json.dumps(config), encoding="utf-8")
    with pytest.raises(ValueError, match="tree SHA-256 mismatch"):
        ov.build_publication(config_path)


def test_newick_parser_supports_quoted_labels_and_rejects_ambiguous_extensions() -> None:
    root = ov.parse_newick("('tip one':0.1,tip_two:0.2)95;")
    assert ov.tip_order(root) == ["tip one", "tip_two"]
    with pytest.raises(ValueError, match="comments/annotations are unsupported"):
        ov.parse_newick("(tip_one[&x=1]:0.1,tip_two:0.2)95;")
    with pytest.raises(ValueError, match="duplicate tip labels"):
        ov.parse_newick("(tip_one:0.1,tip_one:0.2)95;")


def test_long_explicit_display_labels_wrap_without_content_loss() -> None:
    label = "Bifidobacterium_longum_NCC2705_OUTGROUP"
    single = ov._wrapped_display_label(label, "SINGLE_COLUMN")
    double = ov._wrapped_display_label(label, "DOUBLE_COLUMN")
    assert "\n" in single
    assert single.replace("\n", "") == label
    assert double.replace("\n", "") == label
    assert ov._is_perfect_support("100/100") is True
    assert ov._is_perfect_support("100") is True
    assert ov._is_perfect_support("99/100") is False


def test_distributable_tree_consumer_has_no_workspace_or_prefix_inference() -> None:
    text = (ROOT / "tools" / "tree_bgc_overlay.py").read_text(encoding="utf-8")
    prohibited = ("/" + "Users/", "Co" + "dex", "Clau" + "de", "startswith(\"AS")
    assert not any(marker in text for marker in prohibited)
