# Understand a region and its evidence

Use a saved Mamey package to choose a region, understand its scores and write a
short interpretation. You need its workbook or CSV tables and the original
antiSMASH ZIP for sequence-level checks. For the first opening and validation
steps, use [Read one saved package](reader/03_READ_RESULTS.md).

## Open these in order

Every package has an entry page, `OPEN_ME_FIRST.html`. It links the triage board, the
lead boards, the workbook, the issue log and the validation gate. The inventory CSV and
`manifest.json` sit in the same folder. Replace
`EXAMPLE` with your run label.

1. `issue_log.md`. Read it before any ranking.
2. `EXAMPLE_4_triage_board.csv`, the triage board: every region, ranked. It carries the
   node name, boundary, products and reference columns.
3. `EXAMPLE_2_inventory.csv`, the inventory: coordinates, annotations and reference
   columns for each region.
4. `EXAMPLE_5_workbook.xlsx`, the workbook. Its `BGC_Inventory` sheet matches the
   inventory CSV. Its `Triage_Board` sheet is shorter than the CSV. It has only
   `BGC_ID`, `Assembly_Locator`, the AB, AF and novelty scores, `Lead_tier`,
   `Standing_rule`, `Corrected_rank`, `Claim_confidence` and `Rationale`. Use the CSV
   for node, boundary and products.
5. `EXAMPLE_ANALYSIS_FORWARD.md`, a worklist of the leads to judge first.

Keep annotations in a review copy. `manifest.json` records the input hash, versions,
settings and detailed issues. `gate_validation.json` is the validation result saved at
run time. `package_status.json` is a later status record that validation can refresh.
`manifest_short.json` and the brief hold selected summaries.

## Four different questions about completion

The execution log tells you whether the command finished. Validation checks the
package structure and workbook. Channel statuses describe the evidence read.
Written cards and their review records show whether interpretation is complete.
These states can differ in one package.

`MAMEY_COMPLETE_WITH_ISSUES` directs you to the issue log. `JUDGMENT_PENDING` means
the saved interpretation state is pending. Look for separately authored work
before assuming that state describes everything done since the run.

`MAIN_JSON_PARSE_HELD` means the main walker encountered errors or skipped
members. `MAIN_JSON_WALKER_TRUNCATED` means it reached a limit. Read the affected
channel and source details when deciding whether coverage answers your question.

## Read one row

To pick a row and copy its identity, follow [Read one saved package](reader/03_READ_RESULTS.md#follow-a-region).
This page explains the columns you meet next.

### Row identity

A region is named by **strain / full node-or-contig / region / BGC alias**. In the
inventory CSV the columns are `Strain`, `Node_ID`, `antiSMASH_Region` and `BGC_ID`.
`Node_ID` is the full contig name from the antiSMASH record, not a shortened number.
In the workbook sheet `BGC_Inventory` the headers are `Node/contig ID` and
`antiSMASH region` (the first two columns), `Assembly locator` (third) and `BGC` (fourth). Copy all four parts together. Match the row to exactly
one inventory row and find the GenBank file named in `Source_GBK`. That is the region file, or for
a whole-record input, the record file that held the region.

### Scores and labels

Read the product annotations, boundary, architecture grade, AB and AF scores,
reference matches and evidence states. AB and AF prioritize antibacterial and
antifungal follow-up. They are not activity measurements or probabilities. A product
label or reference match points to a possible biosynthetic capacity. Check shared
genes and coverage before you name a compound.

### Reference-match columns

The inventory records what KnownClusterBlast gave for the region. KnownClusterBlast is
antiSMASH's comparison against characterized clusters in the MIBiG database.

`KCB_evidence_state` (the workbook header is `KCB evidence state`) says which source the match columns come from:

| Value | What it means for you |
|---|---|
| `KNOWNCLUSTERBLAST_OBSERVED` | A KnownClusterBlast file had hits. The reference columns are filled from it. |
| `KNOWNCLUSTERBLAST_NO_HITS_UNVALIDATED` | The KnownClusterBlast file was present and had no hits. The reference columns stay empty. This is not a validated negative. It does not show that no similar cluster exists. |
| `CLUSTERBLAST_FALLBACK_OBSERVED` | No KnownClusterBlast file was usable, so ClusterBlast results were read. These are hits against genomes, not curated MIBiG clusters. Check them by hand. |
| `UNKNOWN_KCB` | Nothing was read. This is missing evidence, not a low similarity. |

`KCB_similarity_pct` is a column of the triage board CSV. It is antiSMASH's own
similarity percent for the top KnownClusterBlast hit. It is blank when no percent was
read. A blank is not zero. The percent comes from the antiSMASH JSON in the ZIP, and
`run` reads it in every evidence mode, including the capped first run. It is blank when the
ZIP has no antiSMASH JSON, or when the JSON's top hit and the KnownClusterBlast TXT top hit
name different MIBiG clusters. The package turns the percent into a band: high at 70 or
above, moderate at 40 or above, low above 0, and `none` for exactly 0. A blank, or a
value outside 0 to 100, gives `unresolved`. The band appears in `verdicts.json` and in
the analysis-forward worklist. The bands are coarse on purpose. A high band is similarity, not compound identity.
`KCB_score` is a different number, the cumulative BLAST score, and it is not a percent.

### Why a region may be missing from the lead list

Three triage-board columns can withhold a region from the lead list:
- `Standing_rule`: a fixed rule always downgrades this kind of region. The rules are in
  `mamey/data/rules_registry.json`.
- `Primary_metab_flag`: the region looks like primary (housekeeping) metabolism.
- `Mobile_element_flag`: the region looks like a mobile genetic element.

The lead filter withholds a region when one of these cells holds a real flag. An empty cell, `NO`, `N`, `FALSE`, `0` and
`NONE` (any case) are not flags. Anything else is. Excluded rows stay in the triage
board; they are only left out of lead lists.

## Counts, boundaries and assembly are different things

Raw region count comes from parsed region records. The boundary-weighted count
uses one per interior region, one-half per edge region and one-quarter per
full-contig region. Report it as a heuristic alongside the raw count and boundary
categories; those weights do not measure recovered fractions of pathways.

Assembly contig count and N50 describe contiguity. The region-boundary tier uses
different evidence. Compare those fields separately and use comparable antiSMASH
settings when comparing strains. [The glossary](GLOSSARY.md) defines the grades and metrics.

## Decide what to investigate next

Choose the question raised by the row: missing genes at an edge, a reference
match, conflicting annotations or an unexplained score. Inspect the existing
source evidence before requesting another search.

For a figure, start with the available `gold_figures/` and `locus_maps/`, then
use [Figures](FIGURES_START_HERE.md). For a written card, choose a profile in
[the Mode B guide](MODE_B_USER_WALKTHROUGH.md).

## Keep and transfer the result

Use [Save and move a result](FILES_STORAGE_AND_HANDOFF.md). Later authored work
may sit outside the original package ZIP. Inspect rendered pages before sharing
them, and use the source tables for exact identifiers.

## Work through one biological question

Ask what supports the selected region, what is missing, and which alternative
explanation also fits. For an edge region, inspect the contig boundary and nearby
gene context. For a reference hit, compare coverage and architecture. Strain or
extract assay observations need a demonstrated link before being assigned to a locus.

### Read a zero in its recorded scope

A zero is meaningful when the named operation ran on the stated inputs.
`NOT_MEASURED`, `UNBOUND`, invalid data and truncated evidence describe other
states. Keep the database and tested scope with a completed search that found no hits.

### A short interpretation template

Record the exact identity; the file, field and observed value; your interpretation;
a competing explanation; missing evidence; and one next check that would separate
the alternatives. Save that note beside the package. If you need a full card,
use the [authoring walkthrough](MODE_B_USER_WALKTHROUGH.md).

## Saved summaries and current validation

`explain` reads saved summaries. It prints at most five warnings, shortened to
100 characters each, so use `issue_log.md` and `manifest.json` for coverage questions.
Carry record-limit and assembly-probe failures into any reported count, and state
whether the input was FASTA, whole-record or region-only.

An `IDENTITY_HOLD` needs resolution in the source records before reusing a lead.
For a fresh validation, follow [Read one saved package](reader/03_READ_RESULTS.md#run-a-fresh-check-if-needed).

## The analysis-forward worklist

`EXAMPLE_ANALYSIS_FORWARD.md` lists the leads to judge first, ordered by lead tier. It
marks its status `COMPLETE` when the manifest has top-target or wet-lab-priority entries,
and `PENDING` otherwise. Its JSON sidecar, `EXAMPLE_analysis_forward.json`, always writes
`mode_b_complete` as 0. Neither tells you that a card was written. Use the cards
themselves and their checks for that.

<a id="quick-list-selection-and-full-inventory"></a>

## Use the CLI to browse the triage board

From the program folder with its environment active, show five rows sorted by AB
score. Use your own run label:

```bash
python mamey_run.py list-bgcs runs/EXAMPLE/package --axis ab --top 5
```

`--axis ab` changes the default board order; `--top 5` limits the display.
To see every board row, including recorded exclusions, as JSON:

```bash
python mamey_run.py list-bgcs runs/EXAMPLE/package --json --include-dropped
```

The ordinary list leaves out rows the lead filter excludes (see
[Why a region may be missing from the lead list](#why-a-region-may-be-missing-from-the-lead-list)).
`--include-dropped` shows them. The native table keeps every row.

Use a positive `--top` value, or omit it for no limit. Identity checks run before
filtering, so a malformed hidden row can stop the command too.
