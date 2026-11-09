"""v9.7.464: domain-level master sheets keep strains apart when they share a BGC alias.

BGCnnn repeats in every strain. update_domain_level_sheets used to key the architecture
strings and the B1_BGC_Master burden join by the bare alias, so two strains that both have
BGC001 merged into one architecture row, and one strain's burden landed on the other's B1 row.
"""
from __future__ import annotations
import csv, os
import pytest

openpyxl = pytest.importorskip("openpyxl")
from mamey.master_workbook import update_domain_level_sheets, _DOMAIN_SHEETS

_CX_FIELDS = ["Strain", "Rank", "BGC_ID", "Assembly_Locator", "Products", "Domain_total",
              "Biosynthetic_core_domain_count", "Tailoring_domain_count",
              "Transport_domain_count", "Regulatory_domain_count"]

# same alias, different strain and contig
_LOCI = [("STRAINX", "contigX_7 region001", ["PKS_KS", "PKS_AT"], 2),
         ("STRAINY", "contigY_3 region004", ["AMP-binding", "PCP", "Condensation"], 3)]


def _write_tables(d, loci):
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "domain_rows_long.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=_DOMAIN_SHEETS["Domain_Rows_Long"])
        w.writeheader()
        for strain, loc, doms, _n in loci:
            for i, dom in enumerate(doms):
                w.writerow({"Strain": strain, "Rank": 1, "BGC_ID": "BGC001",
                            "Assembly_Locator": loc, "locus_tag": f"{strain}_{i}",
                            "cds_start": 100 + i * 100, "cds_end": 190 + i * 100, "strand": 1,
                            "domain_name": dom, "domain_role_category": "core",
                            "BGC_products": "T1PKS"})
    with open(os.path.join(d, "domain_complexity_metrics_by_bgc.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=_CX_FIELDS)
        w.writeheader()
        for strain, loc, _doms, n in loci:
            w.writerow({"Strain": strain, "Rank": 1, "BGC_ID": "BGC001",
                        "Assembly_Locator": loc, "Domain_total": n,
                        "Biosynthetic_core_domain_count": n, "Tailoring_domain_count": 0,
                        "Transport_domain_count": 0, "Regulatory_domain_count": 0})


def _master(tmp_path):
    wb = openpyxl.Workbook()
    wb.active.title = "A1_Dashboard"
    b1 = wb.create_sheet("B1_BGC_Master")
    for j, h in enumerate(["strain", "assembly_locator", "BGC_ID"], 1):
        b1.cell(1, j).value = h
    for i, (strain, loc, _d, _n) in enumerate(_LOCI, 2):
        b1.cell(i, 1).value = strain
        b1.cell(i, 2).value = loc
        b1.cell(i, 3).value = "BGC001"
    mp = str(tmp_path / "master.xlsx")
    wb.save(mp)
    return mp


def _b1_totals(mp):
    b1 = openpyxl.load_workbook(mp)["B1_BGC_Master"]
    hdr = [b1.cell(1, c).value for c in range(1, b1.max_column + 1)]
    tc = hdr.index("Domain_total") + 1
    return {b1.cell(r, 1).value: b1.cell(r, tc).value for r in range(2, b1.max_row + 1)}


def test_architecture_strings_one_row_per_strain_locus(tmp_path):
    dl = str(tmp_path / "dl")
    _write_tables(dl, _LOCI)
    mp = _master(tmp_path)
    update_domain_level_sheets(dl, mp)
    ws = openpyxl.load_workbook(mp)["Domain_Architecture_Strings"]
    hdr = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
    rows = [dict(zip(hdr, [ws.cell(r, c).value for c in range(1, ws.max_column + 1)]))
            for r in range(2, ws.max_row + 1)]
    got = {(r["Strain"], r["Assembly_Locator"], r["BGC_ID"]):
           (r["domain_architecture_string"], int(r["n_domains"])) for r in rows}
    assert len(rows) == 2
    assert got == {("STRAINX", "contigX_7 region001", "BGC001"): ("PKS_KS - PKS_AT", 2),
                   ("STRAINY", "contigY_3 region004", "BGC001"):
                   ("AMP-binding - PCP - Condensation", 3)}


def test_b1_burden_lands_on_own_strain_only(tmp_path):
    mp = _master(tmp_path)
    # one strain at a time, as a master is appended
    dlx = str(tmp_path / "dlx")
    _write_tables(dlx, _LOCI[:1])
    update_domain_level_sheets(dlx, mp)
    assert _b1_totals(mp) == {"STRAINX": "2", "STRAINY": None}
    dly = str(tmp_path / "dly")
    _write_tables(dly, _LOCI[1:])
    update_domain_level_sheets(dly, mp)
    assert _b1_totals(mp) == {"STRAINX": "2", "STRAINY": "3"}


def test_b1_burden_cohort_tables(tmp_path):
    dl = str(tmp_path / "dl")
    _write_tables(dl, _LOCI)
    mp = _master(tmp_path)
    res = update_domain_level_sheets(dl, mp)
    assert _b1_totals(mp) == {"STRAINX": "2", "STRAINY": "3"}
    assert res["n_master_updated"] == 2
