# Read one saved package

Use a `Complete_Package.zip` or its extracted folder to find the region list,
read the workbook and check warnings. You need a browser and a spreadsheet reader.
Python is only needed for the optional fresh check below.

## Open it

Extract the ZIP into a review folder, keeping the original ZIP. Open
`OPEN_ME_FIRST.html` in the folder containing `manifest.json`.
Keep that folder's files together so its links work.

The examples use `EXAMPLE`; use the label on your own files.

## Check what finished

Read `issue_log.md` and the saved validation results before the rankings.
`MAMEY_COMPLETE_WITH_ISSUES` means extraction finished with warnings to read.
`JUDGMENT_PENDING` means interpretation still needs to be written.

If counts or statuses differ, use `issue_log.md` and the terminal result; the
entry page may have been written earlier. For a fresh check, use the command below. [Detailed results](../READING_YOUR_RESULTS.md) explains the
other statuses and evidence files.

## Follow a region

Open `AS-40_5_workbook.xlsx` and start on `Triage_Board`. Match its `BGC_ID`
to `BGC` on `BGC_Inventory` for the region's coordinates and annotations.

Copy the inventory fields **Strain / Node/contig ID / antiSMASH region / BGC**
into your notes. Together they identify the strain, full contig, region and alias.

The CSV versions are `AS-40_4_triage_board.csv` and `AS-40_2_inventory.csv`.

Scores help decide what to inspect; they are not measurements of antimicrobial
activity. A reference match shows similarity, rather than identifying a compound.
Read the channel's status beside its values: missing input, a failed check and a
completed search with no hits mean different things.

## Run a fresh check if needed

Use an installed bundle and a writable review copy because validation can update
`package_status.json`. From the program folder, replace the path with that copy:

```bash
python mamey_run.py validate runs/EXAMPLE/package --workbook-strict
```

`--workbook-strict` makes a missing workbook or failed `WORKBOOK_CONTENT` an error.
That check requires a nonblank, non-`PENDING` BGC ID in each of four sheets,
scanning up to 200 data rows per sheet. Inspect the evidence tables you plan to use.

Read both the main result and `WORKBOOK_CONTENT`. If
`package_status_receipt_write` says `FAILED`, the saved status was not refreshed
even when validation exits successfully; keep the terminal result. If either validation check fails, follow
[Recovery and limits](04_RECOVERY_AND_LIMITS.md).

## Save your notes

Write down the package path, the selected row's full identity, what you found,
and the question you want to investigate next. Keep the notes beside the result.
