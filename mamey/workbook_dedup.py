"""workbook_dedup.py — make master-append idempotent (P2)."""
def drop_existing_strain(wb, strain_id, sheets=None):
    """Remove all rows for strain_id from every per-strain sheet so a re-ingest replaces,
    never duplicates. Returns total rows removed.

    OUT-P11 (v9.7.325): the strain column is located from each sheet's header row rather than
    assumed to be column A — C4_Strain_Decision_Table and D3_RGGMCI_Promoted key strain in
    column 2, so the old column-1 assumption silently no-op'd on C4 (already listed) and left
    D3 out entirely. The allowlist now also covers B6/C1/C2/D2/D3/E3, which
    _write_canonical_v1_views appends per strain and which duplicated on a strain re-run.
    Append-log sheets are deliberately excluded (A3_Run_Manifest, H1_Handoff_Log, H2_Gap_Queue) —
    they accumulate run/handoff history, not one row per strain; a sheet with no "strain" header
    column is skipped, never guessed.
    """
    PER_STRAIN = ("A2_Strain_Registry", "A4_Completeness_Audit", "B1_BGC_Master",
                  "B2_Product_Class_Matrix", "B3_Known_Cluster_Matrix", "B4_Cross_Strain_Scans",
                  "B6_Compound_Reference", "C1_DAPR_Antibacterial", "C2_DAPR_Antifungal",
                  "C3_Lead_Tier_Summary", "C4_Strain_Decision_Table", "D1_RGGMCI_All_Strains",
                  "D2_RGGMCI_Top_Pairs", "D3_RGGMCI_Promoted", "E1_Mode_B_Index",
                  "E3_Megacluster_Registry", "F1_Ecology_Readiness", "G2_Validation_Roles")
    # v9.7.335: `sheets` restricts the drop to the caller's own sheets. Without it, the Sapote
    # write-back helpers (update_g2_from_sapote / update_c3c4_from_sapote) cleared the strain from
    # ALL 18 sheets and then restored only the one or two they meant to touch — silently deleting
    # the registry row, every BGC row, the DAPR boards and the RG-GMCI pairs. workbook_schema_check
    # returned PASS on the result, because every sheet lost the strain consistently.
    removed = 0
    for sh in (sheets if sheets is not None else PER_STRAIN):
        if sh not in wb.sheetnames:
            continue
        ws = wb[sh]
        # locate the strain column from the header row (frozen schema: col 1, or col 2 for C4/D3)
        strain_col = None
        for c in range(1, ws.max_column + 1):
            if str(ws.cell(row=1, column=c).value or "").strip().lower() == "strain":
                strain_col = c
                break
        if strain_col is None:
            continue  # no strain column (an append-log) — never dedup
        # collect row indices to delete (bottom-up so indices stay valid)
        to_del = [r for r in range(ws.max_row, 1, -1)
                  if ws.cell(row=r, column=strain_col).value == strain_id]
        for r in to_del:
            ws.delete_rows(r, 1)
            removed += 1
    return removed
