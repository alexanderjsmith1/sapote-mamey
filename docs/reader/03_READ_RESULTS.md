# Read one saved package

Use a `Complete_Package.zip` or its extracted folder to find the region list,
read the workbook and check warnings. You need a browser and a spreadsheet reader.
Python is only needed for the optional fresh check below.

## Open it

Extract the ZIP into a review folder. Keep the original ZIP. Open `OPEN_ME_FIRST.html`
in the folder that holds `manifest.json`. It links the triage board, the lead boards, the workbook, the issue log
and the validation gate. The inventory CSV and `manifest.json` sit in the same folder. Keep the folder's
files together so the links work.

The examples use `EXAMPLE`. Use the label on your own files.

## Check what finished

Read `issue_log.md` before the rankings. A line containing `[BLOCKING]` means the run failed;
see [Recovery and limits](04_RECOVERY_AND_LIMITS.md). Then open `package_status.json`:

- `terminal_status` is how the run ended. `MAMEY_COMPLETE_WITH_ISSUES` means extraction
  finished with warnings to read in the issue log.
- `validator_status` is the last validation result, for example `MAMEY_COMPLETE`.

In `gate_validation.json`, `gold_completeness` reads `JUDGMENT_PENDING` until written
cards exist. That is normal for a fresh run: interpretation still needs to be written.

The entry page may have been written before a later check. If its counts or statuses
differ from `issue_log.md` or the terminal result, trust those. For a fresh check, see
below. [Reading your results](../READING_YOUR_RESULTS.md) explains the other statuses.

## Follow a region

1. Open `EXAMPLE_4_triage_board.csv`, the triage board. It ranks every region and
   carries the node name, boundary and products.
2. Match the row's `BGC_ID` to `BGC_ID` in `EXAMPLE_2_inventory.csv`, or to `BGC` on the
   `BGC_Inventory` sheet of `EXAMPLE_5_workbook.xlsx`. That row gives the coordinates
   and annotations. The workbook's own `Triage_Board` sheet is shorter than the CSV: it
   has scores and lead tier but no node, boundary or products.
3. Copy the region's four-part identity into your notes: strain, full node or contig
   name, antiSMASH region, and BGC alias. The columns are listed in
   [Row identity](../READING_YOUR_RESULTS.md#row-identity).

Scores help you decide what to inspect. They do not measure antimicrobial activity.
A reference match shows similarity, not a compound. The reference columns also carry an
evidence state, and "no hits" is not the same as "not read". Read
[Reference-match columns](../READING_YOUR_RESULTS.md#reference-match-columns) before you
trust a blank.

## Run a fresh check if needed

Use an installed bundle and a writable review copy because validation can update
`package_status.json`. From the program folder, replace the path with your review copy (an extracted package,
wherever it is):

```bash
python mamey_run.py validate runs/EXAMPLE/package --workbook-strict
```

`--workbook-strict` makes a missing workbook or a failed `WORKBOOK_CONTENT` check an
error. That check needs at least one row with a real BGC ID (not blank, not `PENDING`)
in the first 200 rows of each of four sheets: `BGC_Inventory`, `Triage_Board`,
`WetLab_Decision_Matrix` and `Mode_B_Summary`. It does not check the evidence tables.
Inspect the ones you plan to use.

Read both the main result and `WORKBOOK_CONTENT`. If
`package_status_receipt_write` says `FAILED`, the saved status was not refreshed
even when validation exits successfully; keep the terminal result. If either validation check fails, follow
[Recovery and limits](04_RECOVERY_AND_LIMITS.md).

## Save your notes

Write down the package path, the selected row's full identity, what you found,
and the question you want to investigate next. Keep the notes beside the result.

A short note has five lines:

- **Question:** what am I trying to decide?
- **Identity and source:** which exact record and run am I reading?
- **Observed:** what does the source show?
- **Interpretation and alternative:** what else could explain it?
- **Gap and next evidence:** what would tell the alternatives apart?

Save the note outside the package, so the package stays unchanged.
