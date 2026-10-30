# Understand a region and its evidence

Use a saved Mamey package to choose a region, understand its scores and write a
short interpretation. You need its workbook or CSV tables and the original
antiSMASH ZIP for sequence-level checks. For the first opening and validation
steps, use [Read one saved package](reader/03_READ_RESULTS.md).

## Open these in order

Read the issue log before the rankings. Then open `AS-40_5_workbook.xlsx` or the
inventory and triage CSVs. Replace `EXAMPLE` with your run label. Keep annotations
in a review copy.

`manifest.json` records the input hash, versions, settings and detailed issues.
`gate_validation.json` is the saved validation result from the run;
`package_status.json` is a later status record that validation can refresh.
`manifest_short.json` and the brief contain selected summaries.

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

## Practice reading a recorded row

Choose one row from your own triage table. Copy its full identity:
**strain / full node-or-contig / region / BGC alias**. Match it to exactly one
inventory row and locate its source region GenBank file.

Read the product annotations, boundary, architecture grade, AB/AF scores,
reference matches and evidence statuses. AB and AF prioritize antibacterial and
antifungal follow-up; their scores are not activity measurements or probabilities.
A product label or reference match points to a possible biosynthetic capacity.
Check shared genes and coverage before naming a compound in an interpretation.

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

## Analysis-forward completion hints

`ANALYSIS_FORWARD` is a saved worklist. Its completion hint tests two nonempty
manifest fields, while its JSON sidecar can still report `mode_b_complete=0`.
Use the actual cards, register and checks to establish what was written. See
[the source reference](reference/06_CURRENT_SOURCE_SCOPE.md#plumbing-part-6-analysis-forward-and-package-entry-snapshots)
for the exact behavior.

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

The ordinary list hides rows with a nonempty `Primary_metab_flag` or `Standing_rule`.
Any nonempty text counts, even a hand-edited `NO` or `False`; keep the native table
and investigate unexpected exclusions. Use a positive `--top` value or omit it
for no limit. Identity checks run before filtering, so a malformed hidden row
can stop the command too.
