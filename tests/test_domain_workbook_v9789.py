"""v9.7.89: domain-level workbook sheets + cross-strain burden fields."""
from __future__ import annotations
import csv, os
import pytest

openpyxl = pytest.importorskip("openpyxl")
from mamey.master_workbook import update_domain_level_sheets, _DOMAIN_SHEETS


def _write_domain_tables(d):
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, "domain_rows_long.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=_DOMAIN_SHEETS["Domain_Rows_Long"])
        w.writeheader()
        for i, (dom, role) in enumerate([("PKS_KS", "PKS ketosynthase"),
                                          ("AMP-binding", "NRPS A-domain / loading"),
                                          ("LANC_like", "Lanthipeptide maturation")]):
            w.writerow({"Strain": "AS-901", "Rank": 1, "BGC_ID": "BGC001",
                        "Assembly_Locator": "NODE_1 region001", "locus_tag": f"c{i}",
                        "cds_start": 100 + i * 100, "cds_end": 200 + i * 100, "strand": 1,
                        "domain_name": dom, "domain_description": "", "evalue": "1e-20",
                        "domain_role_category": role, "BGC_products": "NRPS; PKS",
                        "KCB_top": "", "AB_score": 50, "AF_score": 40})
    with open(os.path.join(d, "domain_role_counts_by_bgc.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=_DOMAIN_SHEETS["Domain_Role_Counts_By_BGC"])
        w.writeheader()
        w.writerow({"Strain": "AS-901", "BGC_ID": "BGC001", "Assembly_Locator": "NODE_1 region001",
                    "domain_role_category": "PKS ketosynthase", "count": 1})
    with open(os.path.join(d, "domain_complexity_metrics_by_bgc.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["Strain", "Rank", "BGC_ID", "Assembly_Locator",
                                           "Products", "Domain_total", "Unique_domain_names",
                                           "Domain_CDS_count", "Biosynthetic_core_domain_count",
                                           "Tailoring_domain_count", "Transport_domain_count",
                                           "Regulatory_domain_count"])
        w.writeheader()
        w.writerow({"Strain": "AS-901", "Rank": 1, "BGC_ID": "BGC001",
                    "Assembly_Locator": "NODE_1 region001", "Products": "NRPS; PKS",
                    "Domain_total": 3, "Unique_domain_names": 3, "Domain_CDS_count": 3,
                    "Biosynthetic_core_domain_count": 3, "Tailoring_domain_count": 0,
                    "Transport_domain_count": 0, "Regulatory_domain_count": 0})
    with open(os.path.join(d, "domain_safe_unsafe_claims.csv"), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=_DOMAIN_SHEETS["Domain_Claim_Safety"])
        w.writeheader()
        w.writerow({"Strain": "AS-901", "Rank": 1, "BGC_ID": "BGC001",
                    "Assembly_Locator": "NODE_1 region001",
                    "Safe_domain_claims": "NRPS/PKS assembly-line architecture",
                    "Unsafe_domain_claims": "confirmed product scaffold",
                    "Domain_claim_ceiling": "assembly-line architecture; not product scaffold"})


def test_domain_sheets_created_and_populated(tmp_path):
    dl = str(tmp_path / "domain_level")
    _write_domain_tables(dl)
    wb = openpyxl.Workbook()
    wb.active.title = "A1_Dashboard"
    b1 = wb.create_sheet("B1_BGC_Master")
    b1.cell(1, 1).value = "BGC_ID"; b1.cell(1, 2).value = "strain"
    b1.cell(2, 1).value = "BGC001"; b1.cell(2, 2).value = "AS-901"
    mp = str(tmp_path / "master.xlsx")
    wb.save(mp)

    res = update_domain_level_sheets(dl, mp)
    assert res["status"] == "OK"
    assert res["sheets"] == 6

    wb2 = openpyxl.load_workbook(mp)
    for name in _DOMAIN_SHEETS:
        assert name in wb2.sheetnames, name
        assert wb2[name].max_row >= 2, f"{name} empty"  # header + >=1 data row

    # cross-strain burden columns landed on B1
    b1 = wb2["B1_BGC_Master"]
    hdr = [b1.cell(1, c).value for c in range(1, b1.max_column + 1)]
    assert "Domain_total" in hdr and "Core_domain_burden" in hdr
    tc = hdr.index("Domain_total") + 1
    assert str(b1.cell(2, tc).value) == "3"


def test_domain_sheets_idempotent_rerun(tmp_path):
    """Re-running for the same strain must not duplicate rows."""
    dl = str(tmp_path / "domain_level")
    _write_domain_tables(dl)
    wb = openpyxl.Workbook(); wb.active.title = "A1_Dashboard"
    mp = str(tmp_path / "master.xlsx"); wb.save(mp)
    r1 = update_domain_level_sheets(dl, mp)
    r2 = update_domain_level_sheets(dl, mp)
    wb2 = openpyxl.load_workbook(mp)
    # Domain_Rows_Long should have the same row count after the second run
    assert wb2["Domain_Rows_Long"].max_row == 1 + r1["n_rows_long"] == 1 + r2["n_rows_long"]


def test_no_domain_tables_is_noop(tmp_path):
    dl = str(tmp_path / "empty")
    os.makedirs(dl)
    wb = openpyxl.Workbook(); mp = str(tmp_path / "m.xlsx"); wb.save(mp)
    res = update_domain_level_sheets(dl, mp)
    assert res["status"] == "NO_DOMAIN_TABLES"
