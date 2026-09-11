"""Synthetic-package tests for mamey.interactive_figures.widget_data.

Builds a tiny sealed-package layout on disk, emits the widget-data aggregate,
and asserts the class/machinery/governance derivations, including the
AS-920 (EXCLUSION_ONLY) and AS-922 (AUDIT_ONLY_QUARANTINED) governance flags.
"""

from __future__ import annotations

import csv
from pathlib import Path

from mamey.interactive_figures import widget_data as wd


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _make_package(runs_dir: Path, strain: str, inventory: list[dict], cds: list[dict]) -> None:
    pkg = runs_dir / strain / "package"
    _write_csv(
        pkg / f"{strain}_2_inventory.csv",
        ["BGC_ID", "Products", "Boundary"],
        inventory,
    )
    # triage board mirrors inventory row count.
    _write_csv(
        pkg / f"{strain}_4_triage_board.csv",
        ["BGC_ID", "Products", "Boundary"],
        inventory,
    )
    _write_csv(
        pkg / f"{strain}_cds_table.csv",
        ["contig", "locus_tag", "start", "end", "length_aa", "gene_functions"],
        cds,
    )


def _fixture(runs_dir: Path) -> None:
    # Normal strain: two BGCs, one hybrid so a class is nonexclusive.
    inv = [
        {"BGC_ID": "BGC001", "Products": "NRPS; PKS", "Boundary": "Edge"},
        {"BGC_ID": "BGC002", "Products": "NRPS", "Boundary": "Full-contig"},
        {"BGC_ID": "BGC003", "Products": "terpene", "Boundary": "Interior"},
    ]
    cds = [
        # role by precedence: additional wins over core when both present
        {"contig": "c1", "locus_tag": "g1", "start": "1", "end": "9",
         "length_aa": "300",
         "gene_functions": "biosynthetic (rule-based-clusters) NRPS: AMP-binding"},
        {"contig": "c1", "locus_tag": "g2", "start": "10", "end": "19",
         "length_aa": "150",
         "gene_functions": "biosynthetic-additional (smcogs) SMCOG1002"},
        {"contig": "c1", "locus_tag": "g3", "start": "20", "end": "29",
         "length_aa": "400",
         "gene_functions": "regulatory (smcogs) SMCOG1041: SARP"},
        {"contig": "c1", "locus_tag": "g4", "start": "30", "end": "39",
         "length_aa": "500",
         "gene_functions": "transport (smcogs) SMCOG1000: ABC transporter"},
        {"contig": "c1", "locus_tag": "g5", "start": "40", "end": "49",
         "length_aa": "250",
         "gene_functions": "resistance (rule-based-clusters) some_resistance_gene"},
        {"contig": "c1", "locus_tag": "g6", "start": "50", "end": "59",
         "length_aa": "120", "gene_functions": ""},  # not machinery
        # duplicate physical CDS (same key) must collapse
        {"contig": "c1", "locus_tag": "g6", "start": "50", "end": "59",
         "length_aa": "120", "gene_functions": ""},
    ]
    _make_package(runs_dir, "AS-999", inv, cds)

    # AS-920: EXCLUSION_ONLY governance override.
    _make_package(
        runs_dir, "AS-920",
        [{"BGC_ID": "BGC001", "Products": "NRPS", "Boundary": "Edge"}],
        [{"contig": "c1", "locus_tag": "g1", "start": "1", "end": "9",
          "length_aa": "100", "gene_functions": "regulatory (smcogs) X"}],
    )
    # AS-922: AUDIT_ONLY_QUARANTINED governance override.
    _make_package(
        runs_dir, "AS-922",
        [{"BGC_ID": "BGC001", "Products": "PKS", "Boundary": "Full-contig"}],
        [{"contig": "c1", "locus_tag": "g1", "start": "1", "end": "9",
          "length_aa": "200", "gene_functions": "biosynthetic-additional (smcogs) X"}],
    )


def test_widget_data_emit(tmp_path):
    runs_dir = tmp_path / "runs"
    _fixture(runs_dir)

    data = wd.build_widget_data(
        runs_dir,
        measured_activity=tmp_path / "no_such_measured.csv",  # force UNRESOLVED
        strain_genus=tmp_path / "no_such_genus.csv",
    )

    # structural validation passes
    assert wd.validate_widget_data(data) == []
    assert set(data["strains"]) == {"AS-999", "AS-920", "AS-922"}

    s = data["strains"]["AS-999"]

    # bgcRows from inventory
    assert s["bgcRows"] == 3
    # physical CDS dedup: 7 rows -> 6 unique
    assert s["cdsRows"] == 6
    assert s["uniquePhysicalGenes"] == 6

    # classes: NRPS in BGC001(Edge)+BGC002(Full) => total2 edge1 full1
    assert s["classes"]["NRPS"] == {"total": 2, "edge": 1, "full": 1, "interior": 0}
    assert s["classes"]["PKS"] == {"total": 1, "edge": 1, "full": 0, "interior": 0}
    assert s["classes"]["terpene"] == {"total": 1, "edge": 0, "full": 0, "interior": 1}

    # machinery roles by precedence
    assert sorted(s["machinery"]["Biosynthetic core"]) == [300]
    assert sorted(s["machinery"]["Biosynthetic additional"]) == [150]
    assert sorted(s["machinery"]["Regulatory"]) == [400]
    assert sorted(s["machinery"]["Transport"]) == [500]
    assert sorted(s["machinery"]["Resistance"]) == [250]
    assert s["machineryGenes"] == 5  # g6 (empty) excluded, dup collapsed

    # governance overrides
    assert s["governance"] == "GOVERNED"
    assert data["strains"]["AS-920"]["governance"] == "EXCLUSION_ONLY"
    assert data["strains"]["AS-922"]["governance"] == "AUDIT_ONLY_QUARANTINED"
    assert data["meta"]["governance"]["AS-920"] == "EXCLUSION_ONLY"
    assert data["meta"]["governance"]["AS-922"] == "AUDIT_ONLY_QUARANTINED"

    # governed count excludes the two overridden strains
    assert data["meta"]["governedStrainCount"] == 1
    assert data["meta"]["strainCount"] == 3

    # hostContext defaults to UNRESOLVED with no crosswalk support
    assert s["hostContext"]["group"] == "UNRESOLVED"


def test_machinery_role_precedence():
    # additional wins over a co-annotated core marker
    both = ("biosynthetic (rule-based-clusters) NRPS: micKC "
            "biosynthetic-additional (rule-based-clusters) Pkinase")
    assert wd.machinery_role(both) == "Biosynthetic additional"
    assert wd.machinery_role("biosynthetic (rule-based-clusters) NRPS: AMP-binding") == "Biosynthetic core"
    assert wd.machinery_role("") is None
    assert wd.machinery_role("other (smcogs) hypothetical") is None


def test_attine_host_group():
    # The attine cohort is governed data loaded from OFFICIAL_DATA and is empty in a
    # data-free code tier, so the test supplies the membership it asserts on.
    saved = wd.ATTINE_ANT_STRAINS
    wd.ATTINE_ANT_STRAINS = {"AS-103"}
    try:
        hc = wd.host_context("AS-103", crosswalk={})
        assert hc["group"] == "ATTINE_ANT"
    finally:
        wd.ATTINE_ANT_STRAINS = saved
    # a bee host maps to BEE; a wasp host maps to WASP
    xwalk = {"AS-421": {"host": "Bombus sp.", "genus": "X"},
             "AS-441": {"host": "Wasp", "genus": "Y"}}
    assert wd.host_context("AS-421", xwalk)["group"] == "BEE"
    assert wd.host_context("AS-441", xwalk)["group"] == "WASP"
    assert wd.host_context("AS-000", xwalk)["group"] == "UNRESOLVED"
