# Choose the next command

This chapter helps you choose among selected command routes. It is not the full command manual. Examples are source-inspected and have not been run on biological inputs in this documentation review.

## Start with the question

If you already have a result package, begin with the results-reading guide. You may be able to answer your question from the inventory, workbook, issue files and saved evidence without running another command.

- **What did I receive?** `explain` summarizes a saved package; `list-bgcs` lists its selected inventory records. The summary does not rerun validation. The listing excludes dropped records by default, so keep its filter settings with any count you report.
- **Is my input suitable?** `inspect` previews an antiSMASH archive. It does not establish that extraction finished. `start` provides orientation, and `doctor` reports environment diagnostics.
- **Did the encoded package checks pass?** `validate` checks a package and can refresh its status receipt. Preserve the original result and use the deliberately selected review workspace described in the troubleshooting guide.
- **Where is the larger workflow up to?** `workflow` reports stage status and writes a ledger. Its current mandatory W10 close stage always returns N/A, so a strict all-complete result is blocked in this source version. Keep the stage results and the defect separate.

These are different questions. A diagnostic PASS, a written report and an accepted scientific interpretation each need their own evidence.

## Make a view from saved data

The optional figure tools render or reorganize existing evidence. They do not perform the upstream search or establish a biological conclusion. Choose a fresh output directory outside the source package, record the selected input paths and hashes, and inspect the resulting artifacts.

**For a numeric matrix: `codex-heatmaps`.** The CSV starts with a row-label column, followed by numeric data columns. Use unique row and column labels. Missing cells and observed zeros remain different states. The default display selects the top 40 rows by total; `--top-rows 0` keeps all rows. The default log1p setting changes color mapping while labels retain raw values.

From the selected bundle directory, using its compatible Python environment, this source-inspected example keeps every row:

```bash
python mamey_run.py codex-heatmaps \
  --input /path/to/matrix.csv \
  --outdir /path/to/new_heatmap_review \
  --top-rows 0
```

Replace both paths with your selected files and a new destination. The output includes SVG panels, an HTML explorer, caption/method text and receipts. Check source versus displayed row counts, missing cells, observed zeros and any omitted rows. Use a separate job directory for unrelated inputs with the same filename stem. A receipt's render PASS does not replace reading the figure at its intended size.

**For a menu of figure possibilities: `codex-figure-catalog`.** This writes a registry and its readiness information. A catalog entry can still need curated inputs or an implementation. A catalog of 200 sets is not a receipt for 200 rendered figures. Check both the selected count and readiness labels, especially after filtering.

**For implemented figure sets: `codex-figure-sets`.** Start with the exact widget JSON and the tranche you intend to render. Tranche 1 is the default. Later tranches require the source bundle, and tranche 6 also requires a lead ledger. Check the returned implemented IDs and count. SVG output can be available even when a native PNG rendering path is unavailable; inspect the formats actually produced.

**For a saved BiG-SCAPE result: `codex-bigscape-figure-sets`.** This reads an existing table or database result. It does not run clustering. Bind the exact run, cutoffs and source manifest. Use the exact-identity bridge when joining to package loci. Source reconciliation, biological interpretation and publication approval remain separate from the renderer's QA status.

**For a package aggregate: `interactive-figures`.** Compare the requested strains with those included in the JSON. Missing packages can be skipped. If you request figures, read the separate figure status: the command can return success for the aggregate while figure generation fails or is skipped. Host information and structural counts are context, not evidence of a product or measured activity.

## Print per-strain views

`assembly-line-pdf` prints saved assembly-line domain views. `bgc-gene-map` prints saved positioned-gene views. Both accept selected strains and an output directory. Their shared wrapper can return success when some requested strains were skipped, so retain the built/requested count and each skip reason.

Use a narrow, unambiguous package root. The package finder looks for the strain's saved modules table and can otherwise select the first recursive match; a root containing several versions is a poor choice for reproducible review. For gene maps, a missing coordinate or gene-context record limits what can be drawn. A blank or skipped view is not a biological absence result.

These PDF tools use small legend and footer sizes in the inspected source. Treat their pages as review outputs until the actual rendered text is readable at the intended print size. Generating a PDF is only the first step.

## Keep specialist reports in their own route

**`resistance-dossier`** writes marker-selected dossiers from saved domains and comparison evidence. Record the curated domain-reference vocabulary used. Zero dossiers can reflect input or vocabulary availability. A marker is a resistance hypothesis, not a measured phenotype. Use a fresh sibling output directory.

**`af-leadboard`** creates an HTML capacity-prior view from an existing cohort master and optional context. Select the master CSV, workspace root and output explicitly. Keep measured antifungal activity distinct from the capacity prior, and check the displayed software/source labels before sharing.

**`surface-leads`** expects particular dated workspace tables. Changing `--out` does not supply those inputs. This belongs in the workspace-maintenance route until its input locations are explicitly bound. Do not use the overwrite flag simply to make a refusal disappear.

**`triage-raw`** prioritizes regions before extraction. It differs from the post-extraction `explore` route, despite older internal text still using that name. Read the top-N scope and each stage's skipped/error state. A prioritization report is not a complete inventory.

## Review and study tools need explicit status reading

**`dualpass` compares ledgers; it does not decide which claim is true.** By default, normalization writes files beside both input ledgers even when `--out` points elsewhere. In this source, a ledger filename lacking `.tsv` can cause normalization to rewrite that input. Keep preserved ledgers out of this default route until the path behavior is repaired. `--no-normalize` compares raw values and avoids that normalization step, but wording differences can then appear as disagreement. Record that choice.

**`validate-finished-review-request` checks a review packet.** READY_FOR_OWNER_REVIEW means the packet passed internal-consistency routing. It does not mean the card was accepted, scientifically validated or selected as current. Keep the findings, artifact root and owner-controlled provenance with the request; hashes establish byte consistency rather than authorship.

**`directed-pks-study` and `cddr-pks` are specialist study/report routes.** Their input schema, selected groups and active source owner need to be explicit. Figure self-ratings do not establish scientific validity. On the existing-study `cddr-pks` route, an UNKNOWN status can return exit 0—even when the study inputs are missing. Read status, warning count and source-table counts; keep that result on hold rather than treating the report's existence as completion.

**`wise-fragmented-pks` prepares a local queue.** It does not run BLASTp. A queued file is not a completed search or an admitted result. Keep local preparation, any separately scoped external work and result review as distinct steps.

## If a command does not answer your question

Save the command, selected input identities and hashes, output destination, exit status and relevant receipt. Add one sentence explaining what you expected and one explaining what you observed. A useful next action fixes the affected stage or missing prerequisite; it does not automatically rerun the entire pipeline.
