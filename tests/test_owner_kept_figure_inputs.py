from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path

import pytest

from mamey.interactive_figures.figure_source_bundle import build_source_bundle
from mamey.interactive_figures.owner_kept_inputs import build_owner_kept_inputs


def _csv(fields, rows):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def _package(path: Path, strain: str, genus: str, *, snapshot=True):
    inventory = _csv(
        ["BGC_ID", "Boundary", "Length_kb", "Products"],
        [{"BGC_ID": "BGC001", "Boundary": "Interior", "Length_kb": "20", "Products": "NRPS"}],
    )
    cds = _csv(
        ["bgc_id", "contig", "locus_tag", "start", "end", "length_aa", "gene_functions"], []
    )
    mibig = _csv(["bgc_id", "query_gene", "mibig_accession"], [])
    modules = _csv(["bgc_id", "mapping_status", "domain", "substrate_consensus"], [])
    payload = {
        "strain_id": strain,
        "taxonomy": f"{genus} testensis",
        "assembly": {"genome_bp": 8_000_000},
        "bgc_counts": {"corrected": 1.0, "assembly_tier": "GOOD"},
        "source_scans": {
            "domain_architecture": {
                "status": "SOURCE_DERIVED",
                "per_bgc": {"BGC001": {"domain_counts": {"NRPS_A": 2, "NRPS_C": 1}}},
            },
            "cassettes": {"status": "SOURCE_DERIVED", "counts": {"siderophore": 1}},
            "resistance": {"status": "SOURCE_DERIVED", "counts": {"ABC_family": 2}},
        },
    }
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"package/{strain}_2_inventory.csv", inventory)
        archive.writestr(f"package/{strain}_cds_table.csv", cds)
        archive.writestr(f"package/{strain}_3_mibig_per_gene.csv", mibig)
        archive.writestr(f"package/{strain}_3_antismash_modules.csv", modules)
        if snapshot:
            archive.writestr(f"package/{strain}_Project_Memory_Snapshot.json", json.dumps(payload))


def _widget(records):
    strains = {}
    for strain, package, host, role, include in records:
        strains[strain] = {
            "governance": "GOVERNED",
            "package": package,
            "bgcRows": 1,
            "uniquePhysicalGenes": 0,
            "machineryGenes": 0,
            "classes": {"NRPS": {"total": 1, "edge": 0, "full": 0, "interior": 1}},
            "machinery": {},
            "hostContext": {"group": host},
            "cohort_role": role,
            "include_by_default": include,
        }
    return {"meta": {"sourceRelease": "synthetic"}, "strains": strains}


def _rows(path):
    return list(csv.DictReader(path.open(newline="", encoding="utf-8")))


def test_current_source_tables_and_nine_figure_readiness(tmp_path):
    records = []
    for strain, genus, host in (
        ("TEST-ALPHA", "Streptomyces", "BEE"),
        ("TEST-BETA", "Actinomadura", "WASP"),
    ):
        package = f"{strain}.zip"
        _package(tmp_path / package, strain, genus)
        records.append((strain, package, host, "STUDY", True))
    widget = tmp_path / "widget.json"
    widget.write_text(json.dumps(_widget(records)), encoding="utf-8")
    bundle = tmp_path / "source"
    source_receipt = build_source_bundle(widget, tmp_path, bundle)
    assert source_receipt["status"] == "PASS"
    assert len(_rows(bundle / "STRAIN_CONTEXT.csv")) == 2
    assert len(_rows(bundle / "DOMAIN_CATEGORY_COUNTS.csv")) == 4
    assert len(_rows(bundle / "CASSETTE_FAMILY_COUNTS.csv")) == 2
    assert len(_rows(bundle / "RESISTANCE_FAMILY_COUNTS.csv")) == 2

    result = build_owner_kept_inputs(widget, bundle, tmp_path / "adapted")
    assert result["status"] == "PASS"
    assert result["study_denominator"] == 2
    assert {row["status"] for row in result["figures"]} == {"REBUILD_READY"}
    assert len(_rows(tmp_path / "adapted/domain_counts.csv")) == 4
    assert len(_rows(tmp_path / "adapted/class_by_strain.csv")) == 2


def test_external_benchmark_is_default_off_and_never_enters_study_n(tmp_path):
    records = []
    for strain, genus, role, include in (
        ("TEST-STUDY", "Streptomyces", "STUDY", True),
        ("TEST-BENCH", "Streptomyces", "EXTERNAL_BENCHMARK", False),
    ):
        package = f"{strain}.zip"
        _package(tmp_path / package, strain, genus)
        records.append((strain, package, "BEE", role, include))
    widget = tmp_path / "widget.json"
    widget.write_text(json.dumps(_widget(records)), encoding="utf-8")
    bundle = tmp_path / "source"
    build_source_bundle(widget, tmp_path, bundle)

    default = build_owner_kept_inputs(widget, bundle, tmp_path / "default")
    assert default["selected_records"] == 1
    assert default["study_denominator"] == 1
    selected = build_owner_kept_inputs(
        widget, bundle, tmp_path / "selected", external_benchmark_ids=["TEST-BENCH"]
    )
    assert selected["selected_records"] == 2
    assert selected["study_denominator"] == 1
    assert selected["external_benchmarks"]["selected"] == ["TEST-BENCH"]
    context = _rows(tmp_path / "selected/strain_context.csv")
    assert next(row for row in context if row["strain"] == "TEST-BENCH")["study_denominator"] == "False"


def test_missing_snapshot_is_held_not_converted_to_zero(tmp_path):
    _package(tmp_path / "TEST-MISSING.zip", "TEST-MISSING", "Streptomyces", snapshot=False)
    widget = tmp_path / "widget.json"
    widget.write_text(json.dumps(_widget([
        ("TEST-MISSING", "TEST-MISSING.zip", "BEE", "STUDY", True)
    ])), encoding="utf-8")
    bundle = tmp_path / "source"
    build_source_bundle(widget, tmp_path, bundle)
    result = build_owner_kept_inputs(widget, bundle, tmp_path / "adapted")
    assert result["status"] == "PASS_WITH_HOLDS"
    statuses = {row["figure_id"]: row for row in result["figures"]}
    assert statuses["F03a"]["status"] == "HOLD"
    assert "NO_DOMAIN_ROWS" in statuses["F03a"]["holds"]
    assert _rows(tmp_path / "adapted/domain_counts.csv") == []


def test_default_on_external_benchmark_refuses_before_output(tmp_path):
    _package(tmp_path / "TEST-BENCH.zip", "TEST-BENCH", "Streptomyces")
    widget = tmp_path / "widget.json"
    widget.write_text(json.dumps(_widget([
        ("TEST-BENCH", "TEST-BENCH.zip", "BEE", "EXTERNAL_BENCHMARK", True)
    ])), encoding="utf-8")
    with pytest.raises(ValueError, match="FIGURE_EXTERNAL_BENCHMARK_DEFAULT_ON"):
        build_source_bundle(widget, tmp_path, tmp_path / "source")
    assert not (tmp_path / "source").exists()


def test_adapter_refuses_existing_destination(tmp_path):
    _package(tmp_path / "TEST-STUDY.zip", "TEST-STUDY", "Streptomyces")
    widget = tmp_path / "widget.json"
    widget.write_text(json.dumps(_widget([
        ("TEST-STUDY", "TEST-STUDY.zip", "BEE", "STUDY", True)
    ])), encoding="utf-8")
    bundle = tmp_path / "source"
    build_source_bundle(widget, tmp_path, bundle)
    destination = tmp_path / "already"
    destination.mkdir()
    with pytest.raises(ValueError, match="FIGURE_INPUT_OUTPUT_EXISTS"):
        build_owner_kept_inputs(widget, bundle, destination)
