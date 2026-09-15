"""TREES_432: reference labels are built from the NCBI Assembly record (organism + strain +
accession), never from the deposit title, and [Type] is written only when
fromtype == "assembly from type material". Organism names stay exactly as deposited.

Records TSV columns the binder expects: accession, organism, strain, fromtype
(extra columns such as level and biosample are tolerated).
"""
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tests"))

import bind_panel_metadata as bpm  # noqa: E402
from trees_432_panel_fixture import make_panel, rows  # noqa: E402

RECORDS = (
    "accession\torganism\tstrain\tfromtype\tlevel\tbiosample\n"
    "GCF_000000001.1\tGenus alpha\tDSM 1\tassembly from type material\tComplete Genome\tSAMN1\n"
    "GCF_000000002.1\tGenus sp. X-2\tX-2\t\tContig\tSAMN2\n"
    "GCF_000000009.1\tOuter beta DSM 9\tDSM 9\tassembly from type material\tScaffold\tSAMN9\n"
    "GCF_000000005.1\tGenus epsilon\tK5\tassembly from synonym type material\tContig\tSAMN5\n"
)


def test_type_tag_only_from_exact_fromtype():
    assert bpm.is_type_material("assembly from type material")
    assert bpm.is_type_material(" Assembly From Type Material ")
    assert not bpm.is_type_material("")
    assert not bpm.is_type_material("assembly from synonym type material")
    assert not bpm.is_type_material("assembly designated as neotype")


def test_label_from_organism_and_strain_not_deposit_title(tmp_path):
    rec_path = tmp_path / "ASSEMBLY_RECORDS_ncbi_esummary.tsv"
    rec_path.write_text(RECORDS)
    records = bpm.load_assembly_records(rec_path)
    assert set(records) == {"GCF_000000001.1", "GCF_000000002.1", "GCF_000000009.1", "GCF_000000005.1"}

    deposit = dict(tip="GCF_000000001.1", identifier="GCF_000000001.1", role="REFERENCE", reference_class="Reference",
                   label_concise="Genus alpha strain DSM 1, whole genome shotgun sequence (GCF_000000001.1)")
    out = bpm.build_reference_label(deposit, records["GCF_000000001.1"])
    assert out["label_concise"] == "Genus alpha DSM 1 [Type] (GCF_000000001.1)"
    assert out["label_experiment"] == out["label_concise"]
    assert out["reference_class"] == "Type"
    assert "whole genome shotgun" not in out["label_concise"]

    nontype = dict(tip="GCF_000000002.1", identifier="GCF_000000002.1", role="REFERENCE", label_concise="x")
    out = bpm.build_reference_label(nontype, records["GCF_000000002.1"])
    assert out["label_concise"] == "Genus sp. X-2 (GCF_000000002.1)"     # sp. kept, strain not duplicated
    assert "[Type]" not in out["label_concise"] and out["reference_class"] == "Reference"

    synonym = dict(tip="GCF_000000005.1", identifier="GCF_000000005.1", role="REFERENCE", label_concise="x")
    out = bpm.build_reference_label(synonym, records["GCF_000000005.1"])
    assert out["label_concise"] == "Genus epsilon K5 (GCF_000000005.1)"   # synonym type material is not [Type]

    outgroup = dict(tip="OUT_OUTGROUP", identifier="GCF_000000009.1", role="OUTGROUP", label_concise="x")
    out = bpm.build_reference_label(outgroup, records["GCF_000000009.1"])
    assert out["label_concise"] == "Outer beta DSM 9 [Type; outgroup] (GCF_000000009.1)"


def test_query_rows_and_unrecorded_references_are_left_alone(tmp_path):
    rec_path = tmp_path / "r.tsv"
    rec_path.write_text(RECORDS)
    data = [dict(tip="AS-1", identifier="AS-1", role="QUERY", label_concise="Genus sp. AS-1", label_experiment="Genus sp. AS-1", reference_class="Owner query"),
            dict(tip="GCF_000000077.1", identifier="GCF_000000077.1", role="REFERENCE", label_concise="old title", label_experiment="old title", reference_class="Reference")]
    report = bpm.bind_reference_labels(data, bpm.load_assembly_records(rec_path))
    assert data[0]["label_concise"] == "Genus sp. AS-1"
    assert data[1]["label_concise"] == "old title"
    assert report == {"GCF_000000077.1": "NO_ASSEMBLY_RECORD"}


def test_records_header_is_documented_and_enforced(tmp_path):
    bad = tmp_path / "bad.tsv"
    bad.write_text("accession\torganism\ttype\nGCF_1\tG a\tyes\n")
    with pytest.raises(SystemExit, match="ASSEMBLY_RECORDS_HEADER"):
        bpm.load_assembly_records(bad)
    assert bpm.ASSEMBLY_RECORD_COLUMNS == ("accession", "organism", "strain", "fromtype")
    doc = bpm.__doc__
    assert "accession, organism," in doc and "strain, fromtype" in doc


def test_cli_rebuilds_labels_and_copies_records(tmp_path):
    data = rows()
    data[1]["label_concise"] = data[1]["label_experiment"] = "Genus alpha strain DSM 1, whole genome shotgun sequence (GCF_000000001.1)"
    data[1]["reference_class"] = "Reference"       # untagged type strain on the baseline panel
    data[2]["label_concise"] = data[2]["label_experiment"] = "Genus sp. X-2 [Type] (GCF_000000002.1)"   # unverified tag
    panel = make_panel(tmp_path, "GTR-09-GENUS", data=data)
    rec_path = tmp_path / "ASSEMBLY_RECORDS_ncbi_esummary.tsv"
    rec_path.write_text(RECORDS)
    out = tmp_path / "out"
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "bind_panel_metadata.py"), "--panel-dir", str(panel),
                        "--out-dir", str(out), "--assembly-records", str(rec_path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    lines = (out / "figure_metadata.tsv").read_text().splitlines()
    header = lines[0].split("\t")
    by = {d["identifier"]: d for d in (dict(zip(header, l.split("\t"))) for l in lines[1:])}
    assert by["GCF_000000001.1"]["label_concise"] == "Genus alpha DSM 1 [Type] (GCF_000000001.1)"
    assert by["GCF_000000001.1"]["reference_class"] == "Type"
    assert by["GCF_000000002.1"]["label_concise"] == "Genus sp. X-2 (GCF_000000002.1)"
    assert by["GCF_000000002.1"]["reference_class"] == "Reference"
    assert by["QRY-1"]["label_concise"] == "Genus sp. QRY-1 [Wasp; US] (PX000001)"
    assert (out / "ASSEMBLY_RECORDS_ncbi_esummary.tsv").exists()
    assert "2 [Type]" in r.stdout
