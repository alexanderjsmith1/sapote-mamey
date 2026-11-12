# Read one saved package

Use this page with a `Complete_Package.zip`, or the folder extracted from one. It shows how
to see whether the run finished, find the region list and read the workbook. You need a
browser and a spreadsheet reader. Python is needed only for the commands below.

## Open it

1. Extract the ZIP into a review folder. Keep the original ZIP unchanged.
2. Keep the extracted files together, so the links between them work.
3. Open `OPEN_ME_FIRST.html` in a browser. If it is not there, open `issue_log.md` instead.

[Reading your results](../READING_YOUR_RESULTS.md#open-these-in-order) lists the other
files in reading order. The examples on this page use the strain name `EXAMPLE`; use the
name on your own files.

## Check what finished

Read `issue_log.md` before you look at any ranking.

- A line starting `- [BLOCKING]` means the run hit a blocking problem. Go to
  [Recovery and limits](04_RECOVERY_AND_LIMITS.md).
- Other lines are warnings. Read them: an optional step can fail and the run still finish.
  A failed optional phase is marked `ERROR` in `run_phase_receipts.jsonl` and may have written
  no output. Check that each file you plan to use exists.
- `- No blocking issues recorded.` is the summary line when there is nothing to report.

Then open `package_status.json`. It holds three status fields:

| Field | What it tells you |
|---|---|
| `terminal_status` | How the run ended. Read this one first. `MAMEY_COMPLETE_WITH_ISSUES` means it finished and recorded issues. |
| `validator_status` | The result of the last `validate`, for example `MAMEY_COMPLETE`. |
| `package_status` | The package's recovery state. A normal run shows `MAMEY_COMPLETE`, even when it recorded issues. A failed fresh validation shows `PARTIAL_FAILED`. |

Recovery markers in the package can also change `package_status`.

So a package can show `terminal_status: MAMEY_COMPLETE_WITH_ISSUES` and
`package_status: MAMEY_COMPLETE` at the same time. That is normal.
[Status values](04_RECOVERY_AND_LIMITS.md#status-values) lists every value.

In `gate_validation.json`, `gold_completeness` reads `JUDGMENT_PENDING` until written
cards cover every region. That is normal for a fresh run.

The entry page is written during the run. If a later check changed a status, the issue
log and the newest `validate` result are the ones to trust.

## Ask the package what it holds

From the program folder, with the bundle installed:

```bash
python mamey_run.py explain runs/EXAMPLE/package
python mamey_run.py list-bgcs runs/EXAMPLE/package
```

- `explain` prints the package status, taxonomy, source, assembly tier, BGC counts, the top
  leads and the first few issues. Its status line uses the terminal status in
  `package_status.json`, then `manifest.json`. If neither has one, it uses the earlier
  status in `manifest_short.json`. Read the issues it lists too.
- `list-bgcs` prints each region's full identity, products, boundary, scores and lead tier,
  in triage order. It hides rows for primary metabolism, mobile elements and standing-rule
  exclusions. Add `--include-dropped` to show them.

## Follow a region

1. Open `EXAMPLE_4_triage_board.csv`, the triage board. It ranks the BGCs the run scored,
   with node name, boundary and products.
2. Match the row's `BGC_ID` to `BGC_ID` in `EXAMPLE_2_inventory.csv`, or to `BGC` on the
   `BGC_Inventory` sheet of `EXAMPLE_5_workbook.xlsx`. That row gives coordinates and
   annotations.
3. Copy the region's four-part identity into your notes: strain, full node or contig name,
   antiSMASH region and BGC alias. [Row identity](../READING_YOUR_RESULTS.md#row-identity)
   names the columns.

Before you count BGCs from the board, compare its row count with the inventory and with the
holds in the issue log. A region that could not be parsed or scored is not on the board.
`--include-dropped` brings back filtered rows, not unparsed regions.

The workbook's `Triage_Board` sheet is shorter than the CSV. It has the scores and lead
tier, but not the node, boundary or products.

Scores tell you what to look at first. They do not measure antimicrobial activity, and a
reference match shows similarity, not a compound. A blank reference cell can mean "no hits"
or "not read". [Reference-match columns](../READING_YOUR_RESULTS.md#reference-match-columns)
shows how to tell them apart.

## Run a fresh check if needed

`validate` writes to `package_status.json`, so run it on a review copy:

```bash
python mamey_run.py validate runs/EXAMPLE/package --workbook-strict
```

Replace the path with your review copy. It prints a JSON result, then a
`WORKBOOK_CONTENT` block. Read both.

`--workbook-strict` fails the check if the workbook is missing or its content check fails.
The content check reads four sheets: `BGC_Inventory`, `Triage_Board`,
`WetLab_Decision_Matrix` and `Mode_B_Summary`. Each needs at least one real BGC ID. Every ID
cell must be blank, `PENDING`, or an ID listed in `EXAMPLE_2_inventory.csv`.

Two results need a closer look:

- **`bgc_id_authority: FORMAT_ONLY`.** The check could not use the inventory, so it only
  checked that IDs look like `BGC` plus three or more digits. It did not check that they
  belong to this package.
- **`package_status_receipt_write: FAILED`.** Validation ran, but the saved status was not
  updated. Trust the printed result, not the file.

An older workbook's `Triage_First_Board` sheet is accepted in place of `Triage_Board`; the
result then shows `legacy_alias: true`. The check does not read the evidence tables, so
open the ones you plan to use. If a check fails, go to
[Recovery and limits](04_RECOVERY_AND_LIMITS.md).

## Save your notes

Keep your notes beside the result, outside the package, so the package stays unchanged.
Write down the package path, the selected row's full identity, what you found and the next
question. A short note has five lines:

- **Question:** what am I trying to decide?
- **Identity and source:** which exact record and run am I reading?
- **Observed:** what does the source show?
- **Interpretation and alternative:** what else could explain it?
- **Gap and next evidence:** what would tell the alternatives apart?
