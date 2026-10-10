# Generic deliverable prompts — source-bound requests

These are request patterns, not readiness certificates. Supply actual inputs, verify the chosen parser and record a run receipt. G7 and G8 are bounded authoring steps; they are not deterministic tools. The old v9.5.9 “all nine tool-backed” audit and DLV-008 closure do not establish current artifact readiness.

Use the [request template](DELIVERABLE_INSTRUCTION_TEMPLATE.md) for input hashes, schema/version, privacy, mutation scope and acceptance. Every individual locus must retain `strain / full node-or-contig / region / BGC alias`. Distinguish predictions, similarity, missing data and measured evidence. An absent anchor cannot support a novelty ranking; no activity ranking without supplied typed assay data. Do not assume populated banks, fixed historical cohort counts or a tracking board.

Commands below name source-declared interfaces only. Run from the bundle root in a working copy with the intended environment, after verifying inputs/dependencies and choosing fresh destinations. No command shown here has been run as part of this documentation audit.

## G1 — BGC atlas

Request a browsable inventory for the named strain and explicit bank roster. Interface:

```bash
python tools/generate_bgc_atlas.py --strain STRAIN_ID --banked-dir /absolute/path/to/bank --out /absolute/path/to/new-atlas.html
```

Verify every displayed locus against source rows. Keep machinery/reference categories separate from activity; do not invent bioactivity axes from class names. See [rescue atlas scope](../docs/RGGMCI_RESCUE_ATLAS.md).

## G2 — Cross-cohort subset panel

Request the exact product-tag filter and cohort roster, preserving distinct anchors and metadata missingness:

```bash
python tools/build_subset_panel.py --banked-dir /absolute/path/to/bank --tag PRODUCT_TAG --out-dir /absolute/path/to/new-panel-directory
```

`--strain-set` is also declared. This helper's existence does not prove every requested filter or scientific claim is supported; inspect emitted rows and denominator. Never equate a shared machinery tag with a shared compound.

## G3 — Strain lead summary

Request a source-grounded summary of the specified rows, with the ranking rule and limitations visible. The helper consumes a workbook with `Lead_Board`, **not** a bank-only input:

```bash
python tools/build_priority_leads.py --workbook /absolute/path/to/working-copy.xlsx --out-dir /absolute/path/to/new-leads-directory
```

It rewrites the workbook's `Priority_Leads` sheet. A/B/C classes are heuristic workflow categories, not experimental confirmation. Supply a working copy and inspect row identity before drafting a one-page narrative.

## G4 — Individual-locus Mode B

For current native authoring, use the [Mode B walkthrough](../docs/MODE_B_USER_WALKTHROUGH.md), stating the exact profile and full locus identity. The historical `tools/build_modeb_deepdive.py --targets STRAIN:ALIAS` emits a legacy eight-section banked report; it does not establish completion under full48 or current50_v2. Verify alias-to-full-identity mapping before using any legacy report.

## G5 — Cross-strain comparison table

Request a fixed strain roster, axis definition, schema/version and inclusion/missingness rules. Check whether `tools/add_xstrain_sheets.py` covers that axis before proposing a command. Unsupported axes remain held; any alternate tally needs an explicit reproducible transformation. State strictness and denominator differences before comparisons.

## G6 — Priority-lead subset figure

Bind the requested roster to reviewed lead rows and use `tools/build_subset_panel.py --strain-set` only after checking its selection/output contract. There is no generic `--subset` fallback established here. Separate the workbook-mutating G3 stage from panel rendering; compare selected rows and identities between stages.

## G7 — Plain-language guide

Write a short explanation of the supplied, reviewed rows for the requested reader. Explain source confidence and unknowns in ordinary language. Use an explicit supplied ordering; if no justified rank exists, group neutrally. Do not manufacture novelty, activity or compound assignments. Record fact-to-source links and keep every locus identity recoverable.

## G8 — Manuscript passage

Draft the requested passage from a claim ledger binding each statement/number to input hash, field/row, denominator and evidence level. Hold unsupported causal, functional, novelty, taxonomy or activity claims. Authoring is not scientific adoption or publication approval.

## G9 — Approximate anchor-family rarefaction

The source declares `--out-dir`, not `--out`:

```bash
python tools/build_pangenome.py --banked-dir /absolute/path/to/bank --out-dir /absolute/path/to/new-pangenome-directory
```

Families are approximate nearest-reference anchor groupings. Blank/UNRESOLVED anchors are reference-unresolved, not proven novel; “private” means within this cohort. Default core threshold is `max(2, n_strains // 2)`; record any explicit `--core-min`. Empty bank content can exit successfully without a report. Output figure is `fig_pangenome_rarefaction.png`, with data CSV and summary outputs on a normal non-replot run. Optional `--workbook` rewrites `Pangenome_Novelty`; use a copy. `--replot` can reuse an existing CSV without checking its cohort/source binding and returns before summary/workbook refresh. Validate cached CSV identity and the expected artifact set, rather than relying on exit zero or a plot's existence.

## Add a request pattern

Name the goal, supplied input contract, exact declared interface (or bounded authoring step), mutation/output contract and acceptance evidence. Link its current workflow guide. Readiness must be demonstrated for the actual input/run; do not add a blanket READY badge merely because a script exists.
