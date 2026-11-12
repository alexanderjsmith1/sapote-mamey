# Generic deliverable prompts

Give one of these requests to your assistant. Each names the tool it should run and what to check afterward. They are request patterns, not readiness certificates. Supply real inputs, check the output, and keep the run's command and output hashes. G7 and G8 are writing tasks, not tools.

A **bank** is a folder of per-strain results that a tool reads with `--banked-dir`. It holds `bgc_data.json`, and sometimes `strains.json` and `modeb_verdicts.csv`. A run tries to write `bgc_data.json` into each package, but a failed write is logged as `BGC_BANK_WRITE_FAILED` in the issues and does not stop the seal. Check that the file exists and parses in the package you select. A **working copy** is a copy of a file you can lose. Several tools below change a workbook or write into the bank, so point them at a copy. Terms such as Mode B, RG-GMCI and DAPR are in the [glossary](../docs/GLOSSARY.md).

Use the [request template](DELIVERABLE_INSTRUCTION_TEMPLATE.md) for input hashes, version, privacy, what may be changed and how you will accept the result. Every locus keeps `strain / full node-or-contig / region / BGC alias`. Keep predictions, similarity, missing data and measured evidence apart. A missing anchor cannot support a novelty ranking. Do not rank activity without typed assay data.

Run commands from the bundle root, in a working copy, with fresh output paths.

## G1 — BGC atlas

Request a browsable inventory for one strain from a bank. Interface:

```bash
python tools/generate_bgc_atlas.py --strain STRAIN_ID --banked-dir /absolute/path/to/bank --out /absolute/path/to/new-atlas.html
```

Supply the bank's `bgc_data.json`; `modeb_verdicts.csv` is optional. This HTML is a filtered view: pure-saccharide regions are omitted, and its region count and corrected count use the displayed rows. Cards show strain, BGC alias and region but omit the full contig, so keep a source-bound full-identity mapping beside the atlas and verify every card against it. Read `Confirmed` and `Candidate-novel` as the helper's labels, not measured activity or demonstrated novelty. See [rescue atlas scope](../docs/RGGMCI_RESCUE_ATLAS.md).

## G2 — Cross-cohort subset panel

Request the exact product-tag filter and cohort roster, preserving distinct anchors and metadata missingness:

```bash
python tools/build_subset_panel.py --banked-dir /absolute/path/to/bank --tag PRODUCT_TAG --out-dir /absolute/path/to/new-panel-directory
```

The bank must contain `bgc_data.json` and `strains.json`; verdict and coupling files are optional. `--tag` is a case-insensitive substring match on the product text. `--strain-set` takes exact comma-separated strain IDs without inserted spaces; when both filters are supplied, both must match. Pure-saccharide rows are omitted. Check the filtered source roster and denominator before using the panel: its CSV keeps strain and region but drops BGC alias and contig, so it cannot supply full locus identity by itself. Shared machinery is not a shared compound.

## G3 — Strain lead summary

**Work on a copy of the workbook.** Request a source-grounded summary of the specified rows, with the ranking rule and limitations visible. The helper consumes a workbook with `Lead_Board`, **not** a bank-only input:

```bash
python tools/build_priority_leads.py --workbook /absolute/path/to/working-copy.xlsx --out-dir /absolute/path/to/new-leads-directory
```

It rewrites the workbook's `Priority_Leads` sheet and saves that workbook before writing `Priority_Scores_All.csv`, `Priority_Leads.csv` and `Priority_Leads.md`. If a later export fails, inspect the working workbook and partial sidecars before retrying; the earlier workbook save is not rolled back. A/B/C classes and scores are heuristic workflow categories, not experimental confirmation. Verify each retained locator against the source before drafting the narrative.

## G4 — Individual-locus Mode B

For current native authoring, use the [Mode B walkthrough](../docs/MODE_B_USER_WALKTHROUGH.md), stating the exact profile and full locus identity. The historical `tools/build_modeb_deepdive.py --targets STRAIN:ALIAS` emits a legacy eight-section banked report. A missing verdict reads `NO_VERDICT`, never `CONFIRM`. The report can still emit expressed-pathway wording from the template. Check the actual verdict source and underlying evidence before reusing its prose; the printed label does not establish current review or expression. Verify the alias-to-full-identity mapping. Pick the profile (`full48` or `current50_v2`) as the walkthrough's first step, and author it separately.

## G5 — Cross-strain comparison table

**Work on a copy of the workbook, and expect a write into the bank.** Request a fixed strain roster, axis definition, schema/version and inclusion/missingness rules. Check whether `tools/add_xstrain_sheets.py` covers that axis before proposing a command. Its `--out` names an existing workbook to update: it replaces generated cross-strain sheets, writes `cohort_context.json` into the selected bank, and can refresh the DAPR rescue sheets (the antibacterial and antifungal top-lead tracks) when the required workbook sheets exist. Use a working workbook and explicitly include the bank write in the mutation scope. Unsupported axes remain held; any alternate tally needs a reproducible transformation. State strictness and denominator differences before comparisons.

## G6 — Priority-lead subset figure

`tools/build_subset_panel.py --strain-set` selects every eligible bank row from the named strains, optionally narrowed by a product substring; it does not read G3's `Priority_Leads` sheet or accept an exact lead-locus roster. Use it only when that strain/product scope answers the question. For a figure of particular priority leads, keep rendering held until a documented route accepts the admitted exact loci and preserves their full identities. There is no generic `--subset` fallback. Keep G3's workbook update separate and retain its reviewed rows as the requested roster.

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

Before sharing `Pangenome_Summary.md`, compare its prose with the CSV. The summary gives counts at 1, half and all strains, each read from the CSV row with that `n_strains`, and the gain over the last ten strains (over the whole cohort when it has ten or fewer). A summary built by an older bundle read the half-cohort value one row late and measured the last-ten gain over nine additions; rebuild it before quoting those two values. The summary calls novelty a distance from characterized clusters, a candidate signal. Check those counts against the CSV. A strain with no BGC rows in the bank gets a blank `novel_pct`, not 0. It sorts after every measured strain, is left out of the "Most novel strains" list, and is named on its own line in the summary. Keep "novelty pool" and the novelty wording as a signal, not a finding. Add the unresolved-reference fraction if the reader needs it.

## Add a request pattern

Name the goal, supplied input contract, exact declared interface (or bounded authoring step), mutation/output contract and acceptance evidence. Link its current workflow guide. Readiness must be demonstrated for the actual input/run; do not add a blanket READY badge merely because a script exists.
