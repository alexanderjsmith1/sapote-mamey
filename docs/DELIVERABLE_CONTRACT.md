# Check a strain or project delivery

Use this page to check a finished strain or project delivery before you hand it over. Work through the sections in order: check the package, check the written reports, record completion, check the files to send.

This is a checklist scoped to the task. Which outputs are required comes from the list of outputs the task asked for, not from this page. You need an [extracted working package](reader/03_READ_RESULTS.md), that list, the evidence behind each result, and any holds the run recorded. A figure delivery can be complete without a Mode B card or a report. Include those only when the task asks for them. Terms such as Mode B, card, DAPR and KCB are defined in the [glossary](GLOSSARY.md).

## Check the package

Run this when the delivery requires the workbook:

```bash
python mamey_run.py validate runs/EXAMPLE/package --workbook-strict
```

`--workbook-strict` makes a missing or failed workbook fail the check. If more than one matching workbook exists, it reports `FAIL_WORKBOOK_AMBIGUOUS`. Keep exactly one.

Read the individual gate results and `WORKBOOK_CONTENT`. The result also carries a `package_status_receipt_write` field, but only when the status file could not be written. If you see it with `"state": "FAILED"`, the package status receipt was not written, whatever the main status says. Fix the write problem and validate again. Validation rewrites the working copy's `package_status.json`. Keep the original Complete_Package ZIP untouched. The main first-run recipe is in [first run](reader/01_FIRST_RUN.md).

Then open `OPEN_ME_FIRST.html`, the workbook and `issue_log.md`. The main reading files are:

- `EXAMPLE_2_inventory.csv`: regions and their evidence fields.
- `EXAMPLE_2b_bgc_crosswalk.csv`: source-locus and alias mappings.
- `EXAMPLE_3_scan_states.json`: scan and channel states, with reasons.
- `EXAMPLE_4_triage_board.csv`: ranked regions and treatment fields.
- `EXAMPLE_5_workbook.xlsx`: the per-strain workbook.
- `manifest.json`, `checksums_sha256.txt` and `commit_receipt.json`: evidence pointers, file hashes and run records.

The validator's required-file list is in [`mamey/validate.py`](../mamey/validate.py). A capped run can defer briefs and locus maps. Record their state, and use [Make and review figures](FIGURES_START_HERE.md) when they are requested.

For each figure you deliver, keep its plotted data, source identities and hashes, parameters, caption, methods, run status and visual-review record. List every requested figure you omitted or held, with the reason. EPA-ng, GToTree and BiG-SLiCE outputs come from separate runs with their own input and resource rules; see the [companion guide](companion_tools.md).

## Keep each locus identifiable

Write every locus as **strain / full node-or-contig / region / BGC alias**, copied from the package. The strain is in `manifest.json`. The inventory supplies `Contig` or `Node_ID`, `antiSMASH_Region` and `BGC_ID`. `User_Label` alone can omit the strain. If an identity field is unknown, leave it unresolved. Do not join records on an alias alone.

Tie every number and locus claim to its source, and keep the user's edits and scientific decisions. Leave missing metadata explicit. Check for private identifiers before a public export. [AGENTS.md](../AGENTS.md) and the [scope rules](ASSISTANT_GOVERNANCE.md) say which work and exports are authorized.

## Select the written reports

For a full-strain report set, account for each item:

- **Layperson-Ranked BGC Guide:** strain header, a short narrative, a five-BGC ranked table with plain-language headlines, assembly context and the next action.
- **Technical Full-Analysis Report:** intake, assembly and all ten scan results. Show every region on the ranked triage board, with separate antibacterial and antifungal [DAPR](GLOSSARY.md) lists and the card depth chosen for each region. Add the decision matrix, metabolomics and fermentation planning, ecology, cohort context and method limits. Finish with a reviewer critique, figures, a literature-search list and PNAS-style references.
- **Compound Detection and Isolation Bench Guide:** detection, extraction, LC-MS and isolation plans for the HIGH and MEDIUM regions, tied to the evidence behind each plan.

Use full cards for HIGH and HIGH* regions, candidate cards for MEDIUM regions, and minimum candidate entries for the rest. For a focused locus task, write only the requested cards and keep the other regions visible on the triage board. Choose the [Mode B profile](MODEB_PROFILE_MATRIX.md) before writing. The template it emits sets the titles and evidence requirements.

### Report modules

Use the module that fits the report you are writing:

- Mode B or a synopsis: [Wet-Lab Decision Matrix](modules/DELIVERABLE_WetLabMatrix.md), with four action scores.
- Contestable claims: [Reviewer Attack Simulation](modules/DELIVERABLE_ReviewerAttack.md), with all required categories.
- Class calls: [Diagnostic Domain Combos](modules/KNOWLEDGE_DiagnosticDomainCombos.md), with supporting evidence.
- The section 42.2 trigger: [LMPKS Rescue](modules/DELIVERABLE_LMPKSRescue.md), including its explicit null case.
- Full report: [Metabolomics Readiness](modules/DELIVERABLE_MetabolomicsReadiness.md).
- End of a full report with host metadata: [Ecological Synthesis](modules/DELIVERABLE_EcologicalSynthesis.md), with source-linked hypotheses and nulls.
- Complete strain report: [Figure Suggestion](modules/DELIVERABLE_FigureSuggestion.md).
- After the inventory: [Cross-Strain Family Seeds](modules/DELIVERABLE_FamilySeeds.md).

### POOR/VERY_POOR equal-visibility rule

In POOR and VERY_POOR assemblies, all detected BGCs must remain visible. Sort by `Corrected_rank` when present, or by the selected priority axis. Keep the boundary labels. Do not put every edge or full-contig region below every interior region.

Each requested locus gets its selected card depth or an explicit status. A minimum candidate card holds the full identity, class hypothesis, boundary, source KCB metric and state, one supported interpretation and the next action. Separate a completed search with no hits from a search that was not run, unavailable, unread or unbound. If a required identity field is missing, keep an identity hold.

Boundary context belongs in sections 3 and 19. It does not reduce the reasoning in sections 4, 5 and 11. The edge and full-contig DAPR penalty is zero in POOR and VERY_POOR assemblies, unless a documented non-assembly reason makes the fragment uninterpretable.

### Map and card layout

Keep the locus map, predicted-class line and card together. The map takes about 45% of the page, with the class line and analysis below it. If the card overflows, keep the map with sections 1 to 4 and continue the text with a continuation marker. Follow the [page layout specification](PER_BGC_PAGE_LAYOUT_SPEC.md) for the selected card profile. To record a finished card in the package, see the [Mode B walkthrough](MODE_B_USER_WALKTHROUGH.md) and [from package to a recorded card](INGEST_AND_PRINCIPLES_WHITEPAPER.md#from-package-to-a-recorded-mode-b-card).

## Read comparisons in their source scope

For cohort context, report the selected roster and denominator, corrected-count rank, assembly tier, shared and strain-unique class calls, reference-dark footprint and diagnostics. The `Strain_Cohort_Context`, `Cross_Strain_Class_Prevalence` and `Cross_Strain_Findings` overlays are separate from the frozen master schema. Use the outputs built for the selected cohort. See the [workbook schema](WORKBOOK_SCHEMA.md).

In that overlay's `Strain_Cohort_Context` sheet, `no_KCB_hit_recorded_regions` is this strain's count of rows with no recorded KnownClusterBlast hit. `no_KCB_hit_recorded_share` shows the same count as "N of M", where M is all such banked rows. Check the search state of those rows before you call them completed no-hit results.

Use each quantity for what it measures:

- Label KCB values as cumulative scores.
- RG-GMCI HIGH-pair statistics measure the richness of reference-anchored homologous pairs, with BGC-content gates.
- Report assembly fragmentation separately.
- Leave the four common classes (saccharide, fatty_acid, other, terpene) out of shared and novel arguments.
- A marker's prevalence belongs to the collection it was measured in.
- Keep class calls separate from measured chemistry.

Run RG-GMCI for every multi-contig genome. Its outputs cover candidate pairs, related loci and groups. Keep interior-region and same-contig pairs as related loci. Group files keep each member's source region record separate. The [fragmented-locus guide](MODEB_GAP_RESCUE_READER.md) lists the evidence each needs.

BiG-SCAPE needs its actual analysis outputs and Pfam data. Keep `cross_strain_GCFs.tsv`, the browsable HTML and the full member-identity crosswalk. In `known_vs_novel_GCFs.tsv`, KNOWN marks a family with a MIBiG member and NOVEL marks a family without one in that run's loaded panel. Record the panel, cutoff and member denominator. Follow [BiG-SCAPE](BIGSCAPE_GCF_WORKFLOW.md) before you join families to triage or card records.

Build a project comparison from completed per-strain results and the actual source roster. State the denominators and what each success or failure count measures. Include the outputs the task selected:

- Antibacterial and antifungal top-ten rankings, with class, WL score, assembly tier and bioactivity evidence. The WL score is defined in the [glossary](GLOSSARY.md).
- RG-GMCI success rate, failure reasons and provisional-rescue counts by habitat; cassette-family frequencies and habitat enrichment; hallucination-trap PASS, FLAG and DISQUALIFY counts and domain types.
- Habitat and class composition, novelty-gradient and known-bioactive distributions, and proposed induction strategies and targets. Label reference annotations and measured activity by their actual evidence basis.
- A deduplicated PNAS-style literature index; expected-but-absent families by habitat and positive-control recoveries; a per-BGC completion audit; a file, size and SHA-256 manifest.

For an absence claim, record the search you ran and its coverage.

## Export a coded master

The coded master and the per-strain workbook are different files. Use the [master export recipe](FIGURES_START_HERE.md#export-a-master-workbook) to create and check the master and write the tidy CSVs. Keep the workbook hash, the CSVs, `DATA_DICTIONARY.md` and `release_policy.json` together. The [workbook schema](WORKBOOK_SCHEMA.md) defines the coded names. The builder is [`mamey/master_workbook.py`](../mamey/master_workbook.py).

## Author a layered BGC guide

A layered guide explains one locus for both a lay and a technical reader. Pick the locus from the inventory and keep its complete identity. This example uses the package's BGC001 selector:

```bash
python mamey_run.py guide --package runs/EXAMPLE/package --bgc BGC001 \
  --outdir ../reviews/EXAMPLE-guide
```

`--bgc` selects one locus. Choose a fresh `--outdir` outside the package so earlier writing stays intact. By default the command writes Markdown for both audiences, plus a Word file when python-docx is installed. The Markdown file is `../reviews/EXAMPLE-guide/EXAMPLE_BGC001_Guide.md`.

Keep the generation receipt with the five-Part guide. Fill every `<!-- LAY: ... -->` slot from the source evidence. The `OK` printed at generation checks the skeleton only. Check your finished writing:

```bash
python mamey_run.py verify-guide ../reviews/EXAMPLE-guide/EXAMPLE_BGC001_Guide.md
```

Verification fails for missing Parts, unfilled slots, thin prose, short gene summaries or claim-safety findings. Read the errors and revise the file. If you change the audience option, use the same one for generation and checking.

<a id="record-a-bounded-judgment-completeness-result"></a>

## Check written-report completion

You need the reviewed package, the judgment-register file and the completed [delivery manifest](DELIVERABLE_MANIFEST_TEMPLATE.md). The register filename starts with the strain ID. Create `../reviews/EXAMPLE` first, then choose a new receipt filename:

```bash
python tools/sapote_judgment_receipt.py --package runs/EXAMPLE/package \
  --register runs/EXAMPLE/package/EXAMPLE_judgment_register.json \
  --manifest ../reviews/EXAMPLE/DELIVERABLE_MANIFEST_EXAMPLE.md \
  --out ../reviews/EXAMPLE/judgment-receipt-01.json
```

The helper runs the manifest checker. It reports COMPLETE only when the card count covers the package's raw count and the checker passes. Missing inputs, timeouts or inconsistent checker results leave completion pending. COMPLETE exits 0. JUDGMENT_PENDING exits 1. Read the written JSON and its findings. Keep the earlier receipt when you retry.

`modeb_card_source` reads `judgment_register_unavailable` when `--register` was given but could not be read and no `--modeb` fallback was given. It reads `none` when neither `--register` nor `--modeb` was given. In both cases `modeb_cards_written` is `null` and `modeb_card_count_status` is `UNKNOWN`: the cards were not counted, which is not zero cards. `judgment_register_status` and `judgment_register_error` say why the register was not read.

The counts are not bound to each card's identity or hash. Reconcile the package, card and register rosters yourself, and save those hashes beside the receipt.

## Check files to send

Pick the structural check that matches what you are sending: an output folder, a patch set or a reply.

The receipt file must live outside the program folder. If you run the tool from the program folder with a
`reviews/` folder inside it, the tool stops with `OUTPUT_INSIDE_BUNDLE`. The examples below put `reviews/`
beside the program folder (`../reviews`).

```bash
python tools/handoff_gate.py deliverable ../reviews/EXAMPLE --index OPEN_FIRST.md \
  --receipt ../reviews/EXAMPLE/file-check-01.json
python tools/handoff_gate.py patches ../reviews/EXAMPLE-patches \
  --compose ../reviews/EXAMPLE-patches/compose.sh --receipt ../reviews/EXAMPLE-patches/check-01.json
python tools/handoff_gate.py reply ../reviews/EXAMPLE/reply.md --root ../reviews/EXAMPLE \
  --receipt ../reviews/EXAMPLE/reply-check-01.json
```

`--index` names the entry page. `--receipt` saves the check result; change its filename on each retry. Add `--figure-dir` for each folder of selected PNGs.

The patch check reads the literal `step` and `copy` entries in the composition file. Adding `--replay` runs its shell script, so inspect the script first and use a disposable destination. If two patch cards share a file name such as `card.diff`, the digest check may report ambiguous findings.

Read the counts the check prints. Identity scanning covers Markdown and root TSVs. Check CSV identity joins and rendered figures yourself. Reply mode expects percent-encoded link targets and does not parse angle-wrapped local paths, so check the links in your application as well.

Keep the selected results, source hashes, captions, methods, checks and unresolved items with the original package. For a full-strain transfer, put the package, selected reports, workbook and check records in the delivery ZIP, and list the files, sizes and SHA-256 values.

## Treatment labels and missing work

Give every BGC in each selected strain one treatment label:

| Status | Meaning |
|---|---|
| `full Mode B` | Finished card under the selected [profile](MODEB_PROFILE_MATRIX.md): `FINISHED_FULL48_CURRENT_EVIDENCE` or `FINISHED_FULL50_CURRENT50_V2`. |
| `candidate card` | Abbreviated card for a MEDIUM region. |
| `minimum candidate card` | Minimum-field interpretation for LOW, DEPRIORITIZED or evidence-thin regions. |
| `deferred` | Reason and completion path recorded. |
| `not applicable` | Known housekeeping cluster (for example ectoine or epsilon-PL), excluded from interpretation. |

Check the rule and source for `not applicable` before you use it. For each deferred item, record its name and type, the reason, the inputs it needs, the step that completes it and the next action. An item with no log entry is missing, not deferred.

## Citation-Compact Provenance and Citation Status

For dense citations and a single shared genome-mining caveat, use [citation-compact output](CITATION_COMPACT_MODE.md). Keep `interpretation_scope`, `evidence_basis`, `citation_basis`, `uncertainty_flags` and `next_experiment` with the leads. EXCEPTIONAL and HIGH leads need a citation basis or `citation_needed`.

Method references are antiSMASH 8.0 (`10.1093/nar/gkaf334`) and MIBiG 4.0 (`10.1093/nar/gkae1115`). `operator_supplied` marks evidence supplied at run time. `citation_needed` marks a literature gap. `Literature_Search_WorkOrder.md/json` lists searches still to do. `PASS_STRUCTURE` is a structure result only: the emitter checks priority-citation and caveat structure, and the package gate checks required files, schema and tracking. Neither verifies the cited passages, so check them against the report's claims.
