"""v9.7.345 next-cut: sealed source bundle and 21-set tranche 2."""

from __future__ import annotations

import csv
import io
import json
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from mamey.interactive_figures.figure_set_renderer_tranche2 import IMPLEMENTED_IDS_2, render_tranche_2
from mamey.interactive_figures.figure_set_renderer_tranche3 import IMPLEMENTED_IDS_3, render_tranche_3
from mamey.interactive_figures.figure_set_renderer_tranche4 import IMPLEMENTED_IDS_4, render_tranche_4
from mamey.interactive_figures.figure_set_renderer_tranche5 import IMPLEMENTED_IDS_5, render_tranche_5
from mamey.interactive_figures.figure_set_renderer_tranche6 import IMPLEMENTED_IDS_6, render_tranche_6
from mamey.interactive_figures.figure_atlas import render_implemented_atlas
from mamey.interactive_figures.figure_source_bundle import build_source_bundle


def _csv(fields, rows):
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader(); writer.writerows(rows)
    return stream.getvalue()


def _write_package(path: Path, strain: str):
    inventory = _csv(
        ["BGC_ID", "Boundary", "Length_kb", "Products", "KCB_top", "KCB_score", "TTA_tier", "Resistance_tier", "claim_ceiling", "product_claim_ceiling"],
        [
            {"BGC_ID": "BGC001", "Boundary": "Edge", "Length_kb": "20", "Products": "PKS; NRPS", "KCB_top": "BGC0001", "KCB_score": "10"},
            {"BGC_ID": "BGC002", "Boundary": "Interior", "Length_kb": "30", "Products": "RiPP", "KCB_top": "", "KCB_score": ""},
        ],
    )
    cds = _csv(
        ["bgc_id", "contig", "locus_tag", "start", "end", "length_aa", "gene_functions"],
        [
            {"bgc_id": "BGC001", "contig": "c1", "locus_tag": "g1", "start": "1", "end": "900", "length_aa": "300", "gene_functions": "biosynthetic (x) p450"},
            {"bgc_id": "BGC001", "contig": "c1", "locus_tag": "g2", "start": "901", "end": "1800", "length_aa": "300", "gene_functions": "regulatory"},
        ],
    )
    mibig = _csv(
        ["bgc_id", "query_gene", "mibig_accession", "mibig_compound", "pct_identity", "pct_coverage_interpretation", "blast_score", "reference_rank", "reference"],
        [{"bgc_id": "BGC001", "query_gene": "g1", "mibig_accession": "BGC0001", "mibig_compound": "example", "pct_identity": "50", "pct_coverage_interpretation": "90", "blast_score": "100", "reference_rank": "1", "reference": "BGC0001.1"}],
    )
    modules = _csv(
        ["bgc_id", "mapping_status", "domain", "substrate_consensus"],
        [{"bgc_id": "BGC001", "mapping_status": "MAPPED", "domain": "PKS_AT", "substrate_consensus": "mal"}],
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(f"package/{strain}_2_inventory.csv", inventory)
        archive.writestr(f"package/{strain}_cds_table.csv", cds)
        archive.writestr(f"package/{strain}_3_mibig_per_gene.csv", mibig)
        archive.writestr(f"package/{strain}_3_antismash_modules.csv", modules)


def _widget(package_names):
    strains = {}
    groups = ("BEE", "UNRESOLVED")
    for index, (strain, package) in enumerate(package_names.items()):
        strains[strain] = {
            "governance": "GOVERNED", "package": package, "bgcRows": 2,
            "uniquePhysicalGenes": 2, "machineryGenes": 2,
            "classes": {
                "PKS": {"total": 1, "edge": 1, "full": 0, "interior": 0},
                "NRPS": {"total": 1, "edge": 1, "full": 0, "interior": 0},
                "RiPP": {"total": 1, "edge": 0, "full": 0, "interior": 1},
            },
            "machinery": {"Biosynthetic core": [300], "Regulatory": [300]},
            "hostContext": {"group": groups[index], "source": "test" if index == 0 else "", "hostSpecies": "bee" if index == 0 else "", "location": "x" if index == 0 else ""},
        }
    return {"meta": {"sourceRelease": "synthetic"}, "strains": strains}


def test_source_bundle_and_tranche2_render(tmp_path):
    packages = {}
    for strain in ("AS-1", "AS-2"):
        name = f"{strain}_Complete_Package.zip"
        packages[strain] = name
        _write_package(tmp_path / name, strain)
    widget_path = tmp_path / "widget.json"
    widget_path.write_text(json.dumps(_widget(packages)), encoding="utf-8")
    bundle = tmp_path / "bundle"
    source_receipt = build_source_bundle(widget_path, tmp_path, bundle)
    assert source_receipt["status"] == "PASS"
    assert source_receipt["present_package_count"] == 2
    assert len(list(csv.DictReader((bundle / "BGC_RECORDS.csv").open()))) == 4
    assert len(list(csv.DictReader((bundle / "BGC_CLASS_PAIRS.csv").open()))) == 2
    assert len(list(csv.DictReader((bundle / "MIBIG_GENE_CONVERGENCE.csv").open()))) == 2
    out = tmp_path / "figures"
    render_receipt = render_tranche_2(widget_path, bundle, out)
    assert render_receipt["status"] == "PASS"
    assert tuple(render_receipt["implemented_ids"]) == IMPLEMENTED_IDS_2
    assert len(list((out / "figures").glob("*.svg"))) == 21
    assert len(list((out / "data").glob("*.csv"))) == 21
    assert len(list((out / "text").glob("*.md"))) == 21
    for svg in (out / "figures").glob("*.svg"):
        ET.parse(svg)
    out3 = tmp_path / "figures3"
    receipt3 = render_tranche_3(widget_path, bundle, out3)
    assert receipt3["status"] == "PASS"
    assert tuple(receipt3["implemented_ids"]) == IMPLEMENTED_IDS_3
    assert len(list((out3 / "figures").glob("*.svg"))) == 28
    for svg in (out3 / "figures").glob("*.svg"):
        ET.parse(svg)
    out4 = tmp_path / "figures4"
    receipt4 = render_tranche_4(widget_path, bundle, out4)
    assert receipt4["status"] == "PASS"
    assert tuple(receipt4["implemented_ids"]) == IMPLEMENTED_IDS_4
    assert len(list((out4 / "figures").glob("*.svg"))) == 14
    out5 = tmp_path / "figures5"
    receipt5 = render_tranche_5(widget_path, bundle, out5)
    assert receipt5["status"] == "PASS"
    assert tuple(receipt5["implemented_ids"]) == IMPLEMENTED_IDS_5
    assert len(list((out5 / "figures").glob("*.svg"))) == 92
    lead_ledger = tmp_path / "lead_ledger.csv"
    lead_ledger.write_text("strain,bgc_id,include_state,provenance\nAS-1,,INCLUDED,synthetic test\n", encoding="utf-8")
    out6 = tmp_path / "figures6"
    receipt6 = render_tranche_6(widget_path, bundle, lead_ledger, out6)
    assert receipt6["status"] == "PASS"
    assert tuple(receipt6["implemented_ids"]) == IMPLEMENTED_IDS_6
    assert len(list((out6 / "figures").glob("*.svg"))) == 25
    atlas = render_implemented_atlas(widget_path, bundle, tmp_path / "atlas")
    assert atlas["status"] == "PASS"
    assert atlas["implemented_count"] == 175
    atlas200 = render_implemented_atlas(widget_path, bundle, tmp_path / "atlas200", lead_ledger=lead_ledger)
    assert atlas200["status"] == "PASS"
    assert atlas200["implemented_count"] == 200


def test_cli_parser_registers_source_bundle_and_tranche2():
    from mamey.cli import build_parser
    source = build_parser().parse_args(["codex-figure-sources", "--widget-data", "w.json", "--package-dir", "packages", "--outdir", "bundle"])
    assert source.command == "codex-figure-sources"
    render = build_parser().parse_args(["codex-figure-sets", "--widget-data", "w.json", "--source-bundle", "bundle", "--tranche", "2", "--outdir", "figures"])
    assert render.command == "codex-figure-sets"
    assert render.tranche == "2"
    render3 = build_parser().parse_args(["codex-figure-sets", "--widget-data", "w.json", "--source-bundle", "bundle", "--tranche", "3", "--outdir", "figures"])
    assert render3.tranche == "3"
    render5 = build_parser().parse_args(["codex-figure-sets", "--widget-data", "w.json", "--source-bundle", "bundle", "--tranche", "5", "--outdir", "figures"])
    assert render5.tranche == "5"
    render6 = build_parser().parse_args(["codex-figure-sets", "--widget-data", "w.json", "--source-bundle", "bundle", "--lead-ledger", "leads.csv", "--tranche", "6", "--outdir", "figures"])
    assert render6.tranche == "6"
    assert render6.lead_ledger == "leads.csv"
