"""C1/C2 lead rows in the master workbook carry the region, so each row holds the full identity.

The C1/C2 DAPR sheets had strain, contig and BGC but no region column, so a lead row could not
supply the four-part locus identity the workbook guide asks readers to take from one row.
"""
import csv

import openpyxl

import mamey.cli as cli


def test_c1_and_c2_rows_have_a_region_matching_the_inventory(tmp_path, synthetic_single_contig_full_locus_zip):
    strain = "SYNLEAD"
    master = tmp_path / "master.xlsx"
    cli.run_one_strain(
        strain_id=strain, display_name=strain,
        input_zip=str(synthetic_single_contig_full_locus_zip), outdir=str(tmp_path / "runs"), mode="full",
        taxonomy="", source="", bioactivity="", master_path=str(master), json_mode="off",
    )
    inv = {r["BGC_ID"]: r for r in csv.DictReader(open(next((tmp_path / "runs" / strain / "package").glob("*_2_inventory.csv")), newline=""))}
    wb = openpyxl.load_workbook(master, read_only=True)
    for sheet in ("C1_DAPR_Antibacterial", "C2_DAPR_Antifungal"):
        rows = list(wb[sheet].iter_rows(values_only=True))
        header = list(rows[0])
        assert "region" in header, header
        body = [dict(zip(header, r)) for r in rows[1:] if r and r[0]]
        assert body
        for row in body:
            assert row["region"] == inv[row["BGC_ID"]]["antiSMASH_Region"], row
    wb.close()
