"""Tests for mamey.cohort_assemble (ADD-01 substrate cohort assembler).

Builds tiny synthetic sealed packages (intake json + inventory csv + manifest)
and asserts row counts for strain_summary / bgc_inventory / class_by_strain and
that no per-run O(N^2) rewrite is needed (pure read of sealed files).
"""
import csv
import json
import os

import pytest

from mamey.cohort_assemble import (
    assemble_cohort,
    write_cohort_csv,
    STRAIN_SUMMARY_COLUMNS,
    BGC_INVENTORY_COLUMNS,
)

INV_HEADER = [
    "BGC_ID", "Release", "Contig", "Region", "antiSMASH_Region", "Boundary",
    "Length_kb", "Products", "Arch", "KCB_top", "KCB_score", "safe_claim",
]


def _write_package(runs_dir, strain, taxonomy, source, engine, bgcs):
    pkg = os.path.join(runs_dir, strain, "package")
    os.makedirs(pkg, exist_ok=True)
    intake = {
        "strain_id": strain,
        "display_name": strain,
        "taxonomy": taxonomy,
        "source": source,
        "release": "PUBLIC",
        "antismash_version": "8.0.4",
        "bgc_count": len(bgcs),
        "assembly": {"genome_bp": 5000000, "contigs": 200, "n50": 60000, "gc_pct": 70.0},
    }
    with open(os.path.join(pkg, f"{strain}_1_intake.json"), "w", encoding="utf-8") as fh:
        json.dump(intake, fh)
    with open(os.path.join(pkg, f"{strain}_2_inventory.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=INV_HEADER)
        w.writeheader()
        for b in bgcs:
            w.writerow(b)
    with open(os.path.join(pkg, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump({"strain_id": strain, "workflow_version": engine}, fh)
    return pkg


def _bgc(bgc, contig, products, arch="NRPS", kcb="", kcbscore="", claim="class-capacity only"):
    return {
        "BGC_ID": bgc, "Release": "PUBLIC", "Contig": contig, "Region": "region001",
        "antiSMASH_Region": "region001", "Boundary": "Full-contig", "Length_kb": "11.8",
        "Products": products, "Arch": arch, "KCB_top": kcb, "KCB_score": kcbscore,
        "safe_claim": claim,
    }


@pytest.fixture
def cohort_dir(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    _write_package(
        str(runs), "AS-001", "Streptomyces sp.", "bee-associated", "Mamey v1.9.118",
        [
            _bgc("BGC001", "NODE_1", "NRPS", kcb="mannopeptimycin", kcbscore="1366"),
            _bgc("BGC002", "NODE_2", "RiPP; lassopeptide"),
        ],
    )
    _write_package(
        str(runs), "AS-002", "Nocardia sp.", "wasp-associated", "Mamey v1.9.118",
        [
            _bgc("BGC010", "NODE_9", "PKS"),
            _bgc("BGC011", "NODE_8", "NRPS; betalactone"),
            _bgc("BGC012", "NODE_7", "terpene"),
        ],
    )
    return str(runs)


def test_strain_and_bgc_counts(cohort_dir):
    cohort = assemble_cohort(cohort_dir)
    assert cohort["meta"]["n_strains"] == 2
    assert cohort["meta"]["n_bgcs"] == 5  # 2 + 3
    assert len(cohort["strain_summary"]) == 2
    assert len(cohort["bgc_inventory"]) == 5


def test_genus_and_source_extracted(cohort_dir):
    cohort = assemble_cohort(cohort_dir)
    by_strain = {r["strain"]: r for r in cohort["strain_summary"]}
    assert by_strain["AS-001"]["genus"] == "Streptomyces"
    assert by_strain["AS-002"]["genus"] == "Nocardia"
    assert by_strain["AS-001"]["source"] == "bee-associated"
    assert by_strain["AS-001"]["bgc_count"] == 2


def test_class_by_strain_matrix(cohort_dir):
    cohort = assemble_cohort(cohort_dir)
    # products are ';'-split into classes
    assert cohort["class_by_strain"]["AS-001"].get("lassopeptide") == 1
    assert cohort["class_by_strain"]["AS-001"].get("RiPP") == 1
    assert cohort["class_by_strain"]["AS-002"].get("NRPS") == 1
    assert cohort["class_by_strain"]["AS-002"].get("betalactone") == 1
    # union class list covers every observed class
    for c in ("NRPS", "RiPP", "lassopeptide", "PKS", "betalactone", "terpene"):
        assert c in cohort["classes"]


def test_safe_claim_carried_verbatim(cohort_dir):
    cohort = assemble_cohort(cohort_dir)
    assert all(r["safe_claim"] == "class-capacity only" for r in cohort["bgc_inventory"])


def test_write_cohort_csv_row_counts(cohort_dir, tmp_path):
    cohort = assemble_cohort(cohort_dir)
    out = tmp_path / "COHORT_MASTER.csv"
    paths = write_cohort_csv(cohort, str(out))
    # main = bgc_inventory: 5 data rows + header
    with open(paths["main"], newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 5
    assert list(rows[0].keys()) == BGC_INVENTORY_COLUMNS
    # strain_summary sibling: 2 rows
    with open(paths["strain_summary"], newline="", encoding="utf-8") as fh:
        srows = list(csv.DictReader(fh))
    assert len(srows) == 2
    assert list(srows[0].keys()) == STRAIN_SUMMARY_COLUMNS
    # class_by_strain sibling: 2 rows (one per strain)
    with open(paths["class_by_strain"], newline="", encoding="utf-8") as fh:
        crows = list(csv.DictReader(fh))
    assert len(crows) == 2


def test_optional_xlsx(cohort_dir, tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    from mamey.cohort_assemble import write_cohort_xlsx
    cohort = assemble_cohort(cohort_dir)
    out = tmp_path / "COHORT_MASTER.xlsx"
    write_cohort_xlsx(cohort, str(out))
    wb = openpyxl.load_workbook(str(out))
    assert set(wb.sheetnames) == {"strain_summary", "bgc_inventory", "class_by_strain"}
