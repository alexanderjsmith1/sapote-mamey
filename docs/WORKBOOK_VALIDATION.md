# Master workbook validation

Two workbook checks exist. Pick the one that fits.

| You have | Run | Where it is described |
|---|---|---|
| One run's package and its workbook | `python mamey_run.py validate runs/EXAMPLE/package --workbook-strict` | [First run](reader/01_FIRST_RUN.md) |
| A **master workbook** | `python -m mamey.workbook_schema_check /absolute/path/to/master.xlsx` | This page |

A master workbook is one `.xlsx` that holds many strains. Its sheets carry codes `A1` to `H3` (for example `A2_Strain_Registry` and `B1_BGC_Master`). `python mamey_run.py run ... --master <path>` creates it if absent and updates it on every run. A single run's own workbook has none of these coded sheets.

This page describes `mamey/workbook_schema_check.py`. The [schema design reference](WORKBOOK_SCHEMA.md) and the [frozen requirements](MASTER_SCHEMA_FROZEN_v1_1.md) name some guarantees the checker does not enforce. A PASS here does not mean those are met.

## Run the check

From the bundle root, in the environment you run Mamey in:

```bash
python -m mamey.workbook_schema_check /absolute/path/to/master.xlsx
python -m mamey.workbook_schema_check --full /absolute/path/to/master.xlsx
python -m mamey.workbook_schema_check --full --v12 /absolute/path/to/master.xlsx
```

Use one path and the switches shown. Use one of `--fast` or `--full`, not both. If both are given, `--full` wins.

The checker opens the workbook read-only and never repairs it. It prints JSON and exits `0` on `"status": "PASS"` and `1` on `"status": "FAIL"`. A sample:

```json
{
  "file": "/absolute/path/to/master.xlsx",
  "status": "FAIL",
  "sheets_found": 26,
  "sheets_missing": [],
  "column_errors": [],
  "consistency_errors": ["..."],
  "warnings": [],
  "validation_path": "full-deep"
}
```

Read these keys:

- `status`: `PASS` or `FAIL`.
- `validation_path`: `fast-structural` or `full-deep`.
- `sheets_missing`, `sheets_extra`: sheets the checker expected but did not find, and sheets it does not know.
- `column_errors`, `consistency_errors`: what failed. Either one non-empty means `FAIL`.
- `v1_2_errors`: present only with `--v12`. Its failures (missing `Fragment_Rescue_Tiers`, missing `Activity_Ref` headers, recomputed tier or tag mismatches) set `FAIL` without appearing in the two lists above.
- `warnings`: for example, that the fast path skipped the value checks.
- `error`: present when the file cannot be opened, or when it has no coded master sheets.

The error "No canonical master sheets found" means the file is not a master workbook. Do not add sheets to satisfy it. Save the JSON next to the workbook's SHA-256 and the switches you used.

## What it checks

- **Required sheets.** There are 26. They come from the builder's `CANONICAL_V1_HEADERS`, minus the additive `B5_BLASTp_Hits`, plus `A1_Dashboard`.
- **Headers.** Each sheet's declared columns are compared by position, ignoring case. A blank header cell inside the checked columns is a mismatch. Extra trailing headers are allowed.
- **Row counts.** Non-empty per-strain sheets must agree on row count. The count is the sheet's stored last row minus the header, not a count of non-blank records, so formatting or blank rows can change it. A mismatch does not say which strains are missing; compare the strain identifiers yourself.
- **Cohort size picks the path.** In auto mode, 26 or more non-blank strain cells in the first column of `A2_Strain_Registry` selects the fast path. Smaller cohorts, and any run with `--full`, also check that the strains in `A2` and `B1_BGC_Master` match. The fast path skips that check.
- **`--v12`** also requires the `Fragment_Rescue_Tiers` sheet (code D5) and an `Activity_Ref` header on the C1 and C2 sheets. `--full` then recomputes D5 tier labels and checks that each non-blank `Activity_Ref` is in a fixed tag set. The fast path skips these row checks. A tag in the set does not verify any literature or strain activity.
- **Version stamp.** `H3_Schema_Version` carries the header `Schema version / v1.1`.

The sheet codes are listed in the [sheet index](WORKBOOK_SCHEMA.md#sheet-index).

## What PASS does not prove

A PASS does not check:

- unique strain or locus rows;
- the full `strain / full node-or-contig / region / BGC alias` identity;
- coordinates, or source and package hashes;
- formula freshness (the checker reads cached values and does not recalculate);
- completeness, measured activity, or provenance values.

A workbook with header-only sheets can pass. Duplicate `A2` rows can push a small cohort onto the fast path. Check duplicates, orphans and empty-versus-missing sheets yourself, and keep that evidence with the result.

## Assembly and coverage warnings

A per-strain workbook shows the BGC-boundary `Assembly tier` and selected assembly metrics on its cover and `Strain_Summary`. Keep that run's full manifest and issue log with the workbook. The displayed tier is not the contig/N50 contiguity tier, and it does not show that every eligible record was analyzed.

The master keeps issue text in `A3_Run_Manifest.issues`. These are text notes, not hash-bound coverage receipts, and `A3` accumulates run history. Bind the run and package you mean before you read one cell as current. When you export a comparison or caption, state the FASTA scope used and any probe that failed. For any individual locus, take the full `strain / full node-or-contig / region / BGC alias` from the same admitted inventory.

## Exported tables are a separate check

`python tools/check_provenance_columns.py /path/to/table.csv` checks the column names of CSV and TSV exports. It is not a workbook validator.

- It picks out per-BGC tables by a BGC-ID header, or by cells that read `BGC` plus three or more digits.
- It then requires a strain header and contig and region headers, or one accepted locator header (`locus`, `locus_label` or `exact_locus`).
- It does not read the cell values. Blank or arbitrary values can pass, so bind each row to its identity and source yourself.
- Exit `0` means no finding for the tables it accepted. Exit `1` means an unreadable table or a missing anchor. The count in the failure heading counts problem lines, not tables. Exit `2` means a glob matched nothing or a path is missing or has an unsupported suffix.

## Before you accept a master

1. Record the expected schema, roster and source hashes.
2. Run the check. Use `--full` when you need the orphan and value checks, and `--v12` only for the extra sheets.
3. Read `validation_path`, `warnings`, `sheets_missing`, `column_errors` and `consistency_errors`, and `v1_2_errors` when you used `--v12`.
4. Confirm the data and provenance by hand.
5. Keep the original workbook. Repair or merge in one named working copy, with a new output destination.

## Updating a master

The validator reads one master. It does not compare a before and after pair or an expected roster. The writer replaces rows for the incoming strain on the selected sheets. Extra sheets and extra headers survive, but notes on replaced rows are lost. Three sheets append history, so a re-ingest does not repeat the same output. Read the [master-writer scope](reference/06_CURRENT_SOURCE_SCOPE.md#plumbing-part-2-master-writer-and-retained-values) and keep a copy of the before state. The producer-stamped PASS on `H1_Handoff_Log` does not show that this check ran.

See also [reading your results](READING_YOUR_RESULTS.md) and the [handoff protocol](CLAUDE_CHATGPT_HANDOFF_PROTOCOL.md).
