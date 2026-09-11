from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path

import pytest

from mamey.interactive_figures.figure_set_renderer_tranche7 import (
    HELD_IDS_7,
    IMPLEMENTED_IDS_7,
    render_tranche_7,
)
from mamey.interactive_figures.figure_source_bundle import build_source_bundle
from mamey.interactive_figures.owner_kept_inputs import build_owner_kept_inputs
from mamey.interactive_figures.publication_bridge import (
    PublicationBridgeRefusal,
    validate_figure_receipt_for_publication,
)

# Measured slow on the v9.7.417 seal (>=2s for this file alone; see the INDIGO_418 timing table).
# Marked explicitly rather than inferred from the filename, so the fast partition is defined by
# measurement and a rename cannot silently change what runs.
pytestmark = pytest.mark.slow


def _csv(fields, rows):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def _package(path: Path, strain: str, offset: int):
    inventory = _csv(
        ["BGC_ID", "Node_ID", "antiSMASH_Region", "Boundary", "Length_kb", "Products", "Arch", "KCB_top", "KCB_score", "needs_manual_kcb_check", "parse_confidence"],
        [
            {"BGC_ID": "BGC001", "Node_ID": f"NODE_{offset}_length_1000_cov_20", "antiSMASH_Region": "region001", "Boundary": "Interior", "Length_kb": "20", "Products": "NRPS; RiPP", "Arch": "A", "KCB_top": "BGC0000001", "KCB_score": str(100 + offset), "needs_manual_kcb_check": "no", "parse_confidence": "HIGH"},
            {"BGC_ID": "BGC002", "Node_ID": f"NODE_{offset+1}_length_900_cov_18", "antiSMASH_Region": "region002", "Boundary": "Edge", "Length_kb": "15", "Products": "PKS", "Arch": "B", "KCB_top": "clusterblast subject", "KCB_score": str(200 + offset), "needs_manual_kcb_check": "yes", "parse_confidence": "MEDIUM"},
        ],
    )
    triage = _csv(
        ["BGC_ID", "Arch", "Arch_Capacity", "Class_Conf", "Resistance_tier", "AB_auto", "AF_auto", "Novelty_auto"],
        [
            {"BGC_ID": "BGC001", "Arch": "A", "Arch_Capacity": "RiPP", "Class_Conf": "HIGH", "Resistance_tier": "NULL_NO_SOURCE_DERIVED_RESISTANCE", "AB_auto": "99", "AF_auto": "99", "Novelty_auto": "99"},
            {"BGC_ID": "BGC002", "Arch": "B", "Arch_Capacity": "PKS", "Class_Conf": "MODERATE", "Resistance_tier": "T2_RESISTANCE_LIKE_SOURCE_DERIVED", "AB_auto": "1", "AF_auto": "1", "Novelty_auto": "1"},
        ],
    )
    manifest = {"source_scans": {
        "cctt": {"status": "SOURCE_DERIVED", "hits": {"T43-HAL": [{"locus_tag": "g1"}], "T43-PHO": []}},
        "transporters": {"status": "SOURCE_DERIVED", "hits": {"ABC": [{"locus_tag": "g2"}], "MFS": []}},
        "regulators": {"status": "SOURCE_DERIVED", "hits": {"TetR": [{"locus_tag": "g3"}], "SARP": []}},
    }}
    empty_cds = _csv(["bgc_id", "contig", "locus_tag", "start", "end", "length_aa", "gene_functions"], [])
    empty_mibig = _csv(["bgc_id", "query_gene", "mibig_accession"], [])
    empty_modules = _csv(["bgc_id", "mapping_status", "domain", "substrate_consensus"], [])
    with zipfile.ZipFile(path, "w") as archive:
        prefix = f"package/{strain}"
        archive.writestr(prefix + "_2_inventory.csv", inventory)
        archive.writestr(prefix + "_4_triage_board.csv", triage)
        archive.writestr(prefix + "_cds_table.csv", empty_cds)
        archive.writestr(prefix + "_3_mibig_per_gene.csv", empty_mibig)
        archive.writestr(prefix + "_3_antismash_modules.csv", empty_modules)
        archive.writestr("package/manifest.json", json.dumps(manifest))
        archive.writestr(prefix + "_1_intake.json", json.dumps({"antismash_version": "8.0.4"}))


def test_tranche7_four_provisional_renders_and_q017_hold(tmp_path):
    strains = {}
    for index, strain in enumerate(("TEST-ALPHA", "TEST-BETA"), start=1):
        package = f"{strain}.zip"
        _package(tmp_path / package, strain, index * 10)
        strains[strain] = {
            "governance": "GOVERNED", "package": package, "bgcRows": 2,
            "uniquePhysicalGenes": 0, "machineryGenes": 0,
            "classes": {"NRPS": {"total": 1}, "RiPP": {"total": 1}, "PKS": {"total": 1}},
            "machinery": {}, "hostContext": {"group": "BEE"},
            "cohort_role": "STUDY", "include_by_default": True,
        }
    widget = tmp_path / "widget.json"
    widget.write_text(json.dumps({"meta": {"sourceRelease": "synthetic"}, "strains": strains}), encoding="utf-8")
    source = tmp_path / "source"
    assert build_source_bundle(widget, tmp_path, source)["status"] in {"PASS", "PASS_WITH_ISSUES"}
    owner = tmp_path / "owner"
    owner_receipt = build_owner_kept_inputs(widget, source, owner)
    readiness = {row["figure_id"]: row for row in owner_receipt["a8_figures"]}
    assert readiness["Q017_SCI01A"]["holds"] == "SCOPE_1_VS_RENDER_CONTRADICTION"
    assert all(readiness[figure_id]["status"] == "PROVISIONAL_READY" for figure_id in IMPLEMENTED_IDS_7)

    output = tmp_path / "rendered"
    receipt = render_tranche_7(owner, output)
    assert tuple(receipt["implemented_ids"]) == IMPLEMENTED_IDS_7
    assert tuple(receipt["held_ids"]) == HELD_IDS_7
    assert len(list((output / "figures").glob("*.png"))) == 4
    assert len(list((output / "figures").glob("*.svg"))) == 4
    assert len(list((output / "data").glob("*.csv"))) == 4
    figure_rows = [json.loads(line) for line in (output / "figure_receipts.jsonl").read_text().splitlines()]
    assert {row["binding_state"] for row in figure_rows} == {"PROVISIONAL_BINDING"}
    for row in figure_rows:
        with pytest.raises(PublicationBridgeRefusal, match="FIGURE_PUBLICATION_PROVISIONAL_BINDING"):
            validate_figure_receipt_for_publication(row)
    architecture = list(csv.DictReader((output / "data/Q013_F14.csv").open()))
    assert all("ab_auto" not in row and "af_auto" not in row and "novelty_auto" not in row for row in architecture)
    assert all(row["complete_identity"].count(" / ") == 3 for row in architecture)


def test_publication_bridge_accepts_nonprovisional_receipt():
    validate_figure_receipt_for_publication({"binding_state": "BOUND"})


def test_q020_governed_tertiles_and_fallback_marker(tmp_path, monkeypatch):
    from mamey.interactive_figures.kcb_tertile_figure import KcbTertileRefusal, render_kcb_tertiles
    strains = {}
    for index, strain in enumerate(("TEST-ALPHA", "TEST-BETA"), start=1):
        package = f"{strain}.zip"; _package(tmp_path / package, strain, index * 10)
        strains[strain] = {"governance": "GOVERNED", "package": package, "bgcRows": 2,
            "uniquePhysicalGenes": 0, "machineryGenes": 0,
            "classes": {"NRPS": {"total": 1}, "RiPP": {"total": 1}, "PKS": {"total": 1}},
            "machinery": {}, "hostContext": {"group": "BEE"}, "cohort_role": "STUDY", "include_by_default": True}
    widget = tmp_path / "widget.json"
    widget.write_text(json.dumps({"meta": {"sourceRelease": "synthetic"}, "strains": strains}))
    source = tmp_path / "source"; build_source_bundle(widget, tmp_path, source)
    owner = tmp_path / "owner"; build_owner_kept_inputs(widget, source, owner)
    official = tmp_path / "official"; official.mkdir()
    (official / "exclusions.json").write_text(json.dumps({"governed": {"strains": 2, "regions": 4}}))
    monkeypatch.setenv("MAMEY_OFFICIAL_DATA", str(official))
    output = tmp_path / "q020"
    receipt = render_kcb_tertiles(owner, output)
    assert receipt["denominator"] == {"admitted_scores": 4, "total_governed_bgc_rows": 4}
    assert "tertile bands" in (output / "Q020_G03.svg").read_text()
    assert "derived (clusterblast-only), MEDIUM ceiling" in (output / "Q020_G03.svg").read_text()
    (official / "exclusions.json").write_text(json.dumps({"governed": {"strains": 44, "regions": 1753}}))
    with pytest.raises(KcbTertileRefusal, match="G03_GOVERNED_DENOMINATOR_UNBOUND"):
        render_kcb_tertiles(owner, tmp_path / "q020_wrong_denominator")
