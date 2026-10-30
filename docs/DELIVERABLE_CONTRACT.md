# Check a strain or project delivery

Use this checklist to assemble the outputs requested for a strain or project.
You need an [extracted working package](reader/03_READ_RESULTS.md), the requested
output list and the evidence behind each result. A figure delivery can be complete without a separate Mode B card
or report; include those when they are part of the task. After a strain analysis,
offer the available full-strain report set below.

<a id="sapote-mamey-deliverable-contract"></a>

<a id="deliverable-selection-within-the-authorized-task"></a>

<a id="part-a--per-strain-deliverables"></a>

<a id="a1--mamey-extraction-outputs-code_backed"></a>

## Check the package

For a delivery that requires the workbook:

```bash
python mamey_run.py validate runs/EXAMPLE/package --workbook-strict
```

`--workbook-strict` makes a missing or failed workbook fail this check. Read the
individual gate results and `WORKBOOK_CONTENT`. Validation updates the working
copy's `package_status.json`; keep the original Complete_Package ZIP.

Open `OPEN_ME_FIRST.html`, the workbook and `issue_log.md`. The main reading files are:

- `AS-40_2_inventory.csv`: regions and their evidence fields.
- `AS-40_2b_bgc_crosswalk.csv`: source-locus and alias mappings.
- `AS-40_3_scan_states.json`: scan/channel states and reasons.
- `AS-40_4_triage_board.csv`: ranked regions and treatment fields.
- `AS-40_5_workbook.xlsx`: the per-strain workbook.
- `manifest.json`, `checksums_sha256.txt` and `commit_receipt.json`: evidence pointers,
  tracked-file hashes and run records.

The validator's required-file list is defined in
[`mamey/validate.py`](../mamey/validate.py). Reporting and enrichment checks apply
when enabled. Briefs and locus maps can be deferred by a capped run; record their
state and use [Make and review figures](FIGURES_START_HERE.md) when they are requested.
For each selected figure, keep its plotted data, source identities/hashes,
calculations/parameters, caption, methods, execution status and visual-review
record. List omitted or held requested figures and their reasons. Use completed
companion outputs; EPA-ng, GToTree and BiG-SLiCE have separate input/resource
contracts in the [companion guide](companion_tools.md).

A Project Memory Snapshot with `alias_of: manifest.json` points to that manifest;
resolve the target before reading findings from it.

## Keep each locus identifiable

Use **strain / full node-or-contig / region / BGC alias**, bound to the package
and source record. The strain is in `manifest.json`; the inventory supplies
`Contig`/`Node_ID`, `antiSMASH_Region` and `BGC_ID`. `User_Label` alone can omit
the strain. Keep unknown identity
fields unresolved rather than joining records on an alias alone.

Tie every number and locus attribution to its source; preserve the user's edits
and scientific decisions. Use the selected privacy/release profile and recorded
project/affiliation fields.
Leave missing metadata explicit. Check private identifiers before a public export.
[AGENTS.md](../AGENTS.md) and [scope rules](ASSISTANT_GOVERNANCE.md) govern which
work and exports are authorized.

<a id="a2--selected-sapote-interpretation-documents-prompt_backed"></a>

## Select the written reports

For a full-strain report set, account for the applicable items below:

- **Layperson-Ranked BGC Guide:** strain header, a short narrative, a five-BGC ranked
  table with plain-language headlines, assembly context and the next action.
- **Technical Full-Analysis Report:** summarize intake, assembly and all ten scan
  results. Show every region on the ranked triage board, separate antibacterial
  and antifungal DAPR, and the selected card depth for each region. Include the
  decision matrix, metabolomics/fermentation planning, ecology, cohort context
  and method limits. Finish with reviewer critique, figures, a literature-search
  list and PNAS-style references.
- **Compound Detection and Isolation Bench Guide:** the selected HIGH/MEDIUM
  regions' detection, extraction, LC-MS and isolation plans, explained plainly
  and tied to the evidence used to propose them.

Use full cards for HIGH/HIGH* regions, candidate cards for MEDIUM and minimum
candidate entries for remaining regions in the selected full-strain workflow.
For a focused locus task, author only the requested cards and keep the other
regions visible on the triage board. Choose the [Mode B profile](MODEB_PROFILE_MATRIX.md)
before writing; its emitted titles and evidence requirements control the card.

<a id="a5--ported-deliverable-modules"></a>

### Report modules

Within a selected full-strain interpretation workflow, use the applicable format:

- For Mode B or a synopsis: [Wet-Lab Decision Matrix](modules/DELIVERABLE_WetLabMatrix.md), including four action scores.
- For contestable claims: [Reviewer Attack Simulation](modules/DELIVERABLE_ReviewerAttack.md), with all required categories.
- For class calls: [Diagnostic Domain Combos](modules/KNOWLEDGE_DiagnosticDomainCombos.md), with supporting evidence.
- For the section 42.2 trigger: [LMPKS Rescue](modules/DELIVERABLE_LMPKSRescue.md), including its explicit null case.
- For the full report: [Metabolomics Readiness](modules/DELIVERABLE_MetabolomicsReadiness.md).
- At the end of the full report with host metadata: [Ecological Synthesis](modules/DELIVERABLE_EcologicalSynthesis.md), with source-linked hypotheses and nulls.
- For a complete strain report: [Figure Suggestion](modules/DELIVERABLE_FigureSuggestion.md).
- After the inventory: [Cross-Strain Family Seeds](modules/DELIVERABLE_FamilySeeds.md).

<a id="a26--poorvery_poor-equal-visibility-rule"></a>

### POOR/VERY_POOR equal-visibility rule

In these assemblies, all detected BGCs must remain visible. Sort by
`Corrected_rank` when present or the selected priority axis. Keep boundary labels;
do not put every edge/full-contig region below every interior region.

Each requested locus gets its selected card depth or an explicit status. A
minimum candidate card includes the full identity, class hypothesis, boundary,
source KCB metric/state, one supported interpretation and the next action.
Distinguish a completed no-hit search from not run, unavailable, unread or unbound
evidence. Keep an identity hold when the required fields are missing.

Boundary context belongs in sections 3 and 19; it does not reduce interpretable
reasoning in sections 4, 5 and 11. The edge/full-contig DAPR penalty is zero for
POOR/VERY_POOR assemblies unless a documented non-assembly reason makes the
fragment uninterpretable.

<a id="a25--per-bgc-page-layout-in-the-mode-b--gene-by-gene-compilation-co-location-mandate"></a>

### Map and card layout

Keep the locus map, predicted-class line and card together. The map takes about
45% of the page, with the class line and analysis below it. If the card overflows,
keep the map with sections 1–4 and continue the remaining text with a continuation
marker. Follow the [page layout specification](PER_BGC_PAGE_LAYOUT_SPEC.md)
with the selected card profile.

<a id="a21--cross-strain-cohort-context-block-for-a-selected-full-strain-interpretation-report"></a>

<a id="a22--method-caveats-block-for-a-selected-interpretation-report"></a>

<a id="a27--cross-strain-gcf-network-big-scape--a-series-cohort-deliverable"></a>

<a id="a28--reference-anchored-versus-unanchored-cross-strain-gcf-status--a-series-cohort-deliverable"></a>

<a id="part-b--project-bundle-deliverables"></a>

## Read comparisons in their source scope

For cohort context, report the selected roster and denominator, corrected-count
rank, assembly tier, shared/strain-unique class calls, reference-dark footprint
and diagnostics. The `Strain_Cohort_Context`, `Cross_Strain_Class_Prevalence` and
`Cross_Strain_Findings` overlays are separate from the frozen master schema;
use the outputs built for the selected cohort. See [workbook schema](WORKBOOK_SCHEMA.md).

The overlay's `zero_KCB_share_of_cohort` reports this strain's rows lacking a
`kcb_top` value against all such banked rows. Check their search states before
calling these completed no-hit results.

Use source quantities accurately: label KCB values as cumulative scores. RG-GMCI
HIGH-pair statistics measure reference-anchored homologous-pair richness with
BGC-content gates; report assembly fragmentation separately; the four common
classes saccharide, fatty_acid, other and terpene are excluded from shared/novel
arguments; `hglE-KS-PREV-001` prevalence belongs to its measured collection.
Keep class calls separate from measured chemistry.

Include RG-GMCI for every multi-contig genome. Its outputs cover candidate
pairs, related loci and groups. Keep interior-region or same-contig pairs as
related loci. Group files keep the members' source region records separate. Use the
[fragmented-locus guide](MODEB_GAP_RESCUE_READER.md) for their evidence requirements.

BiG-SCAPE requires its actual analysis outputs and Pfam data. Keep
`cross_strain_GCFs.tsv`, the browsable HTML and the full member-identity crosswalk.
In `known_vs_novel_GCFs.tsv`, KNOWN marks a family with a MIBiG member; NOVEL
marks a family without one in that run's loaded panel. Record the panel, cutoff
and member denominator. Follow [BiG-SCAPE](BIGSCAPE_GCF_WORKFLOW.md) before
joining families to triage or card records.

Build a requested project comparison from completed per-strain results and the
actual source roster. State denominators and what each success/failure count measures.
Include the selected outputs:

- Antibacterial and antifungal top-ten rankings, with class, WL score, assembly
  tier and bioactivity evidence.
- RG-GMCI success rate, failure reasons and provisional-rescue counts by habitat;
  cassette-family frequencies and habitat enrichment; hallucination-trap PASS/FLAG/DISQUALIFY counts
  and domain types.
- Habitat/class composition, novelty-gradient and known-bioactive distributions,
  plus proposed induction strategies and targets. Label reference annotations
  and measured activity by their actual evidence basis.
- Deduplicated PNAS-style literature index; expected-but-absent families by habitat
  and positive-control recoveries; per-BGC completion audit; file/size/SHA-256 manifest.

For absence claims, record the executed search and its coverage.

<a id="a24--figure-ready-tidy-export-standardized-portable-for-downstream-figure-workflows"></a>

<a id="a3--workbook-sheets-schema_backed"></a>

## Export a coded master

The coded master and the per-strain workbook are different files. Use the
[master export recipe](FIGURES_START_HERE.md#export-a-master-workbook) to create
and check the master and write tidy CSVs. Keep the workbook hash, CSVs,
`DATA_DICTIONARY.md` and `release_policy.json` together. The
[workbook schema](WORKBOOK_SCHEMA.md) defines the coded names; its current builder
is [`mamey/master_workbook.py`](../mamey/master_workbook.py).

## Author a layered BGC guide

Choose a locus from the inventory, keeping its complete identity. This example
uses the package's BGC001 selector:

```bash
python mamey_run.py guide --package runs/EXAMPLE/package --bgc BGC001 \
  --outdir reviews/EXAMPLE-guide
```

`--bgc` selects one locus. Choose a fresh `--outdir` outside the package so
earlier writing stays intact.
Defaults cover both audiences and write Markdown plus Word when python-docx is
installed. The Markdown file is `reviews/EXAMPLE-guide/AS-40_BGC001_Guide.md`.

Keep the generation receipt with the five-Part guide. Fill every
`<!-- LAY: ... -->` slot from the source evidence. The generated `OK`
checks the skeleton. Check the saved writing:

```bash
python mamey_run.py verify-guide reviews/EXAMPLE-guide/AS-40_BGC001_Guide.md
```

Verification fails for missing Parts, unfilled slots, thin prose, short gene
summaries or claim-safety findings. Read its errors and revise the actual file.
Use the same audience for generation and checking if you change that option.

<a id="record-a-bounded-judgment-completeness-result"></a>

## Check written-report completion

Use the reviewed package, explicit judgment-register file and completed
[delivery manifest](DELIVERABLE_MANIFEST_TEMPLATE.md). Create `reviews/EXAMPLE`
first, then choose a new receipt filename:

```bash
python tools/sapote_judgment_receipt.py --package runs/EXAMPLE/package \
  --register runs/EXAMPLE/package/AS-40_judgment_register.json \
  --manifest reviews/EXAMPLE/DELIVERABLE_MANIFEST_AS-40.md \
  --out reviews/EXAMPLE/judgment-receipt-01.json
```

The register filename starts with the strain ID. The helper runs the manifest checker. It reports COMPLETE only when the card
count covers the package's raw count and the checker passes. Missing inputs,
timeouts or inconsistent checker results leave completion pending.
If `modeb_card_source` is `none`, check the register path and JSON; its zero
is unmeasured.

Reconcile the actual package/card/register roster independently: these counts
are not bound to each card's current identity or hash. Save those hashes beside
the receipt. COMPLETE exits zero; JUDGMENT_PENDING exits one. Read the written
JSON and findings, and preserve the earlier receipt on retry.

<a id="a4--provenance-and-packaging-code_backed--prompt_backed"></a>

<a id="handoff-gate--run-before-handing-work-over"></a>

## Check files to send

Choose the matching structural check for a ready output folder, patch set or reply:

```bash
python tools/handoff_gate.py deliverable reviews/EXAMPLE --index OPEN_FIRST.md \
  --receipt reviews/EXAMPLE/file-check-01.json
python tools/handoff_gate.py patches reviews/EXAMPLE-patches \
  --compose reviews/EXAMPLE-patches/compose.sh --receipt reviews/EXAMPLE-patches/check-01.json
python tools/handoff_gate.py reply reviews/EXAMPLE/reply.md --root reviews/EXAMPLE \
  --receipt reviews/EXAMPLE/reply-check-01.json
```

`--index` names the entry page. `--receipt` preserves a separately named check;
change its filename on retry. Add `--figure-dir` for each selected PNG folder.
The patch check reads literal `step`/`copy` file entries in the composition;
adding `--replay` executes its shell script.
Inspect that script and use a disposable destination before selecting replay. For
repeated `card.diff` names, this version reports ambiguous digest findings;
that check remains held until its path matching is fixed.

Read the check counts. Identity scanning covers Markdown and root TSVs; check
CSV identity joins and actual rendered figures separately. Reply mode expects
percent-encoded targets and does not parse angle-wrapped local paths; keep the
application's actual link check separate. Preserve the
selected results, source hashes, captions, methods, checks and unresolved items
with the original package. For a full-strain transfer, include that package,
selected reports, workbook and check records in the delivery ZIP; list the files,
sizes and SHA-256 values.

<a id="part-c--treatment-status-vocabulary"></a>

<a id="part-d--deferred-ledger"></a>

## Treatment labels and missing work

Record one treatment label for every BGC in each selected strain:

| Status | Meaning |
|---|---|
| `full Mode B` | Finished selected-profile card: `FINISHED_FULL48_CURRENT_EVIDENCE` or `FINISHED_FULL50_CURRENT50_V2`. |
| `candidate card` | Abbreviated candidate card for MEDIUM priority. |
| `minimum candidate card` | Minimum-field interpretation for LOW/DEPRIORITIZED or evidence-thin regions. |
| `deferred` | Reason and completion path recorded. |
| `not applicable` | BGC is a known housekeeping cluster (e.g., ectoine, epsilon-PL); explicitly excluded from interpretation |

The existing `not applicable` row needs its rule/source checked before using that
exclusion. For each deferred item, record its name/type, reason, required inputs,
which extraction/writing step completes it and what must happen next. An unlogged
missing item is missing, rather than deferred.

<a id="a23--literature-search-handoff-list-replaces-inline-lit-review-for-a-separate-literature-search-session"></a>

<a id="citation-compact-output"></a>

## Citation-Compact Provenance and Citation Status

For dense citations and a single shared genome-mining caveat, use
[citation-compact output](CITATION_COMPACT_MODE.md). Keep `interpretation_scope`,
`evidence_basis`, `citation_basis`, `uncertainty_flags` and `next_experiment`
with the leads; EXCEPTIONAL/HIGH leads need a citation basis or `citation_needed`.

Method references are antiSMASH 8.0 (`10.1093/nar/gkaf334`) and MIBiG 4.0
(`10.1093/nar/gkae1115`). `operator_supplied` carries existing evidence;
`citation_needed` records a literature gap. `Literature_Search_WorkOrder.md/json`
lists searches still to do. Read the relevant checker for `PASS_STRUCTURE`:
the emitter checks priority-citation/caveat structure, while the separate package
gate checks its required files, schema and tracking. Verify the cited passages
for the report's claims.
