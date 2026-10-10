# Master workbook validation — deployed contract and limits

This guide describes `mamey/workbook_schema_check.py` and `mamey/master_workbook.py` in v9.7.447. The [schema design reference](WORKBOOK_SCHEMA.md) and [retained frozen requirements](MASTER_SCHEMA_FROZEN_v1_1.md) include historical/prospective names and guarantees that differ from deployed code. Preserve those requirements; do not treat checker PASS as proof that they are all implemented.

## Check an existing master

From the bundle root in the intended environment:

```bash
python -m mamey.workbook_schema_check /absolute/path/to/master.xlsx
python -m mamey.workbook_schema_check --full /absolute/path/to/master.xlsx
python -m mamey.workbook_schema_check --full --v12 /absolute/path/to/master.xlsx
```

The checker opens the workbook read-only with `data_only=True` and closes it. It reports JSON to stdout; it does not write or repair the workbook. Capture the JSON externally with the workbook SHA-256, source/checker hashes and selected flags. PASS exits zero; reported FAIL exits one. Do not combine `--fast` and `--full`: the simple argument-removal code selects full when both occur rather than rejecting a conflict. Unknown/extra positional tokens are not robustly validated; use one path and the declared switches.

This checker targets master workbooks with coded sheets, not per-strain extraction workbooks or arbitrary custom spreadsheets. “No canonical master sheets found” is a type mismatch, not a request to fabricate missing master sheets.

## What it checks

- Required sheets derive from the builder's `CANONICAL_V1_HEADERS`, excluding additive `B5_BLASTp_Hits`, plus `A1_Dashboard`. The .447 declaration has 26 builder header entries and 26 required sheets after that exclusion/addition. Source comments saying 25 are stale. The `OPTIONAL_SHEETS` list does not make a sheet optional if it is already in the required derived set.
- Most headers are compared positionally, ignoring case, after empty header cells are removed; extra trailing headers are allowed. Removing blank header cells can hide a physical column shift: an inert workbook fixture with the actual required header declarations and an inserted blank A2 header column passes full structural checking. Inspect physical data/header alignment separately; this is a validator repair hold. B3 checks only its leading `strain` header. A1 requires at least one nonempty header, not a specific workbook type value.
- Nonempty per-strain sheet row counts are compared. Empty sheets are not included in that count consistency comparison. Extra sheets are reported but do not themselves fail the core check.
- Auto mode uses fast structural checking at 26 or more **nonblank first-column A2 rows**, not 26 unique strains. Smaller auto cohorts and `--full` also compare the first-column strain sets of A2 and B1. Fast mode skips that orphan check.
- `--v12` additionally requires `Fragment_Rescue_Tiers` with its locked column prefix and an `Activity_Ref` header in C1/C2. Full mode recomputes D5 tier labels and checks nonblank Activity_Ref membership in a hard-coded tag set. Fast mode skips those row values. Tag membership does not verify literature or strain-specific activity.

## What PASS does not prove

The core check does not validate unique strain/locus rows, exact four-part locus identity, coordinate ranges, source/package hashes, formula freshness, data completeness, measured activity or source provenance field values. It uses cached Excel formula values, without recalculating formulas. H3's deployed header is `Schema version / v1.1`; the checker does not enforce the frozen document's promised `workbook_type=MASTER_STRAIN_WORKBOOK` metadata value or use that value to exempt arbitrary custom files.

Header-only required sheets can pass. Duplicate A2 rows can inflate the auto threshold: an isolated in-memory source probe passed with 26 identical A2 rows and header-only B1/other sheets under fast mode. The same source's full path rejects a supplied A2 strain absent from B1. These probes establish checker scope, not validation of any scientific workbook. Keep empty-versus-missing and duplicate/orphan checks in the acceptance evidence.

The frozen design names B5_Strict_Marker_Calls/B6_Protein_Marker_Hits and further class views; the deployed builder instead includes additive B5_BLASTp_Hits and B6_Compound_Reference. A2 also retains top-lead fields despite the freeze's separation requirement. These are implementation/reconciliation holds; do not rename or rewrite archived data merely to satisfy this documentation. A successful current checker run cannot prove append-only compatibility with every archived schema or the frozen provenance gate.

## Assembly and upstream coverage warnings

The per-strain workbook's cover and `Strain_Summary` show the BGC-boundary `Assembly tier`, counts and selected assembly metrics; this writer does not export `run.issues`. Keep the full manifest and issue log with that workbook. The displayed tier is not the independent contigs/N50 contiguity tier, a record-limit probe result or a certificate that all eligible records were analyzed.

The master writer retains issue text in `A3_Run_Manifest.issues`, uses it in gap-action fields, and appends Issue rows to its per-strain master summary. These are textual projections, not typed, hash-bound assembly/record-limit coverage receipts. A3 accumulates run-history records, so bind the intended run and package before treating one issue cell as current. Reconcile the expected record universe independently; neither sheet presence nor structural PASS confirms that warning text is present, current or scientifically resolved.

Retain failed/unavailable probe states and the actual FASTA/whole-record/region-only scope when exporting a comparison or caption. Resolve full `strain / full node-or-contig / region / BGC alias` from the same admitted inventory for individual-locus claims. Sources: `mamey/workbook.py:115–124,209–217`, `mamey/master_workbook.py:201,412–438,925–926` and `mamey/cli.py:3905–3921`.

## Exported-table provenance headers are a separate check

For CSV/TSV exports, `python tools/check_provenance_columns.py /path/to/table.csv` checks recognized provenance **column names**. It is not the workbook validator and does not establish row-level identity. A recognized BGC-ID header or a cell matching `BGC` plus at least three digits selects a per-BGC table. It then requires a recognized strain header and contig/region headers, or an accepted locator header satisfying both. `locus`, `locus_label` and `exact_locus` are accepted locator names without validation of their contents. Blank or arbitrary locator/strain values can therefore pass; independently bind every row to `strain / full node-or-contig / region / BGC alias` and its source/hash.

The reader skips consecutive leading `#` comment lines and normally chooses comma/tab from the suffix. It retries the other delimiter only when parsing yields one header containing that delimiter. This is a narrow header heuristic, not complete schema/dialect admission. Empty/headerless or unrecognized tables produce no anchor finding; a familiar alias column such as `bgc_alias` is selected only if its cells satisfy the BGC pattern. Missing/unsupported explicit paths are filtered out by the CLI, and a successful remaining target can conceal their omission. Preserve the intended versus admitted table roster; no admitted targets returns 2, but an admitted empty file can still produce exit 0 (`tools/check_provenance_columns.py:42–157`).

Normal exit 1 reports unreadability or anchor problems, and exit 0 means no such finding for admitted targets. The failure heading's count is the number of problem strings, not distinct failing tables; one table missing all three anchors can be reported as three “tables”. There is no hash-bound JSON receipt or row/duplicate/coordinate/source-value validation. Save the command, selected file hashes and full diagnostics, and review omitted, blank and unbound rows separately before merge or manuscript use (`tools/check_provenance_columns.py:126–175`).

## Bounded acceptance and recovery

Record the expected workbook type, schema/build, exact roster and source hashes before checking. Review unique keys and the complete `strain / full node-or-contig / region / BGC alias` wherever an individual locus is shown. Read `validation_path`, warnings, missing/extra sheets, column and consistency errors; select `--full` explicitly when orphan/value checking is required, and `--v12` only for the requested additions. Confirm filled data and provenance separately. Preserve original workbooks; any repair/merge uses one named working candidate with row/source bindings and a fresh output destination.

`tools/schema_deployed_audit.py WORKBOOK SCHEMA_MD [OUT_MD]` is a historical sheet-name comparison utility, not this validator. Its regex reads only single-digit A–H codes in a particular Markdown table style; B10–B12 and other formatting may be missed. It compares sheet presence, not headers, rows, hashes or scientific facts; historical MAPPED/DEFER descriptions are hard-coded. It directly writes Markdown and `out.replace('.md', '.json')` without a transactional pair or parent creation; if OUT_MD has no `.md`, the JSON write can overwrite the same path. Use an explicit fresh `.md` name in an existing directory and inspect both outputs. Do not treat its historical PASS-like narrative as current deployment acceptance.

See [handoff protocol](CLAUDE_CHATGPT_HANDOFF_PROTOCOL.md), [reading results](READING_YOUR_RESULTS.md) and [claim-safe request template](../deliverables/DELIVERABLE_INSTRUCTION_TEMPLATE.md) for the wider evidence contract.

## Updating a master is a separate contract

The validator reads one resulting master; it does not compare a before/after pair or an independent expected roster. The current writer replaces rows for the incoming strain on selected sheets. Extra sheets and extra headers can survive while annotations on replaced rows are lost. Three append-history sheets accumulate records, so re-ingest is not identical-output replay. Review [master-writer scope](reference/06_CURRENT_SOURCE_SCOPE.md#plumbing-part-2-master-writer-and-retained-values) and preserve the independently identified before state before a deliberate update. H1's producer-stamped PASS does not prove this validator ran.
