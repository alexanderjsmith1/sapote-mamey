"""Portable regressions for FIGURE_SCREENSHOT_001.

The fixtures are generic.  Deposited fields are copied only from an explicitly
supplied SQLite input; no biological source is inferred from a tip label.
"""
import csv
from importlib import util
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "build_placement_ggtree_inputs.py"


def _tool():
    spec = util.spec_from_file_location("terra04_figure_builder", TOOL)
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _database(path, rows):
    with sqlite3.connect(path) as con:
        con.execute(
            "CREATE TABLE record(acc_base TEXT, isolation_source TEXT, host TEXT, country TEXT)"
        )
        con.executemany("INSERT INTO record VALUES (?,?,?,?)", rows)


def test_reference_label_preserves_post_16s_strain_designation():
    module = _tool()
    tip = (
        "Example_species_gene_for_16S_rRNA_partial_sequence_"
        "strain_IFM_10428_non_type_AB123456_1"
    )

    label = module._ref_label(tip, "Example")

    assert label == "E. species IFM 10428 (AB123456)"
    assert "gene for" not in label


def test_explicit_deposited_fields_reach_optional_renderer_metadata(tmp_path):
    tree = tmp_path / "input.nwk"
    tip = (
        "Example_species_gene_for_16S_rRNA_partial_sequence_"
        "strain_IFM_10428_non_type_AB123456_1"
    )
    tree.write_text(f"({tip}:0.1,outgroup_X:0.2);\n", encoding="utf-8")
    database = tmp_path / "reference.sqlite"
    _database(database, [("AB123456", "patient", "", "Japan")])
    prefix = tmp_path / "result"
    rect_meta = tmp_path / "rect_meta.tsv"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--graft",
            str(tree),
            "--keep-all-refs",
            "--ref-source-db",
            str(database),
            "--rect-meta-out",
            str(rect_meta),
            "--out-prefix",
            str(prefix),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    with open(str(prefix) + "_ggtree_annotation.tsv", newline="", encoding="utf-8") as fh:
        annotation = {row["tip"]: row for row in csv.DictReader(fh, delimiter="\t")}
    with open(rect_meta, newline="", encoding="utf-8") as fh:
        rectangle = {row["tip"]: row for row in csv.DictReader(fh, delimiter="\t")}

    assert annotation[tip]["reference_habitat_status"] == "DEPOSITED_METADATA"
    assert annotation[tip]["reference_habitat"] == "patient"
    assert annotation[tip]["reference_country_status"] == "DEPOSITED_METADATA"
    assert annotation[tip]["reference_country"] == "Japan"
    assert rectangle[tip] == {
        "tip": tip,
        "label": "E. species IFM 10428 [patient · Japan] (AB123456)",
        "category": "clinical/animal-associated",
        "source": "Japan",
        "category_raw": "patient",
        "category_state": "RULE_NORMALIZED",
        "source_raw": "Japan",
        "source_state": "AS_RECORDED",
    }
    assert rectangle["outgroup_X"]["category"] == ""
    assert rectangle["outgroup_X"]["source"] == ""


def test_unmatched_reference_stays_typed_and_blank(tmp_path):
    module = _tool()
    database = tmp_path / "reference.sqlite"
    _database(database, [("AB123456", "patient", "", "Japan")])

    combined, fields = module._load_ref_source_bundle(database)
    status, category, location = module._reference_source_fields(
        "Example_species_AB654321_1", fields, True
    )

    assert combined["AB123456"] == "patient · Japan"
    assert fields["AB123456"] == {"category": "patient", "location": "Japan"}
    assert (status, category, location) == ("ACCESSION_UNMATCHED", "", "")


def test_reference_fields_do_not_leak_across_loader_calls(tmp_path):
    module = _tool()
    first = tmp_path / "first.sqlite"
    second = tmp_path / "second.sqlite"
    _database(first, [("AB123456", "patient", "", "Japan")])
    _database(second, [("CD123456", "unknown", "Example host", "Canada")])

    first_combined, first_fields = module._load_ref_source_bundle(first)
    second_combined, second_fields = module._load_ref_source_bundle(second)
    omitted_combined, omitted_fields = module._load_ref_source_bundle("")

    assert set(first_combined) == set(first_fields) == {"AB123456"}
    assert set(second_combined) == set(second_fields) == {"CD123456"}
    assert first_fields["AB123456"] == {"category": "patient", "location": "Japan"}
    assert second_fields["CD123456"] == {
        "category": "Example host",
        "location": "Canada",
    }
    assert omitted_combined == omitted_fields == {}


def test_optional_fourth_output_is_in_publication_rollback(tmp_path, monkeypatch):
    module = _tool()
    finals = [tmp_path / f"final-{index}" for index in range(4)]
    staged = [tmp_path / f"staged-{index}" for index in range(4)]
    before = {}
    for index, (stage, final) in enumerate(zip(staged, finals)):
        stage.write_text(f"new-{index}", encoding="utf-8")
        final.write_text(f"old-{index}", encoding="utf-8")
        before[final] = final.read_bytes()
    real_replace = module.os.replace
    publications = 0

    def fail_fourth_publication(src, dst):
        nonlocal publications
        if Path(src) in staged and Path(dst) in finals:
            publications += 1
            if publications == 4:
                raise OSError("injected fourth-output failure")
        return real_replace(src, dst)

    monkeypatch.setattr(module.os, "replace", fail_fourth_publication)
    with pytest.raises(SystemExit) as caught:
        module._publish_output_set(
            list(zip(map(str, staged), map(str, finals))),
            str(tmp_path / "recovery.json"),
        )

    assert caught.value.code == 2
    assert {path: path.read_bytes() for path in finals} == before
    assert not list(tmp_path.glob("*.prepublish.bak"))
    assert not (tmp_path / "recovery.json").exists()


def test_renderer_metadata_neutralises_formula_and_preserves_plain_value(tmp_path):
    tree = tmp_path / "input.nwk"
    tip = "Example_species_strain_SAFE_1_AB123456_1"
    tree.write_text(f"({tip}:0.1,outgroup_X:0.2);\n", encoding="utf-8")
    database = tmp_path / "reference.sqlite"
    formula = '=HYPERLINK("https://example.invalid/","x")'
    _database(database, [("AB123456", formula, "", "Plain country")])
    prefix = tmp_path / "result"
    rect_meta = tmp_path / "rect_meta.tsv"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL),
            "--graft",
            str(tree),
            "--keep-all-refs",
            "--ref-source-db",
            str(database),
            "--rect-meta-out",
            str(rect_meta),
            "--out-prefix",
            str(prefix),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
    with open(rect_meta, newline="", encoding="utf-8") as fh:
        row = {item["tip"]: item for item in csv.DictReader(fh, delimiter="\t")}[tip]
    assert row["category"] == "other documented"
    assert row["source"] == "Plain country"
    assert row["category_raw"] == "'" + formula
    assert row["category_state"] == "DOCUMENTED_OTHER"
