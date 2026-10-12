# Evidence to report

Start with a question, a selected figure set and the evidence already available.
The handoff is the figures, plotted data, captions, short findings and Methods
facts that the user can review and write from. A Mode B card or white paper is
an additional selected format; neither is required for this workflow.

## 1. Select the question and sources

Write one sentence stating what the report should answer. Identify the selected
strains or loci, the unit of analysis and the intended comparison. Bind the
actual package, original antiSMASH input and any external metadata by checksum.
For a locus, retain `strain / full node-or-contig / region / BGC alias` from one
source record. Keep biological observations distinct from repeated files or
multiple views of the same region.

For public examples, select public genomes explicitly and retain their
accessions and source metadata. Establish type-material status from the
deposited record before using a type label. A public genome does not make
private comparison rows, comments or workstation paths public. A type-strain
walkthrough needs no private isolate data.

Read an existing package's manifest, issue log, inventory and retained validation
before deciding to rerun extraction. [Read your results](READING_YOUR_RESULTS.md)
and [First analysis](MASTER_WALKTHROUGH.md) cover these two starting points.
Preserve original inputs. Some post-seal figure commands refresh package files,
so use an identified working copy when the original must remain unchanged.

## 2. Choose the figure roster

Give every intended figure a stable ID, a question, its source table or channel,
the calculation and its inclusion rule. Record omitted and held panels alongside
the completed panels. State whether a panel covers all regions, a selected
subset, one representative per group or only rows with available evidence.

Use [Make and review figures](FIGURES_START_HERE.md) to select an existing
renderer or recipe. Standard package figures, native domain panels, cross-strain
plots and external tree/family panels have different input contracts. A figure
recipe describes how to make a figure; it does not establish that the analysis
ran. EPA-ng, GToTree and BiG-SLiCE require their own admitted inputs, actual
execution evidence and result checks.

## 3. Keep an evidence note for each finding

Use a short Markdown note or table alongside the figure. This is authored
analysis, not a new engine output or an automatically validated schema.

| Record | What to retain |
|---|---|
| Observation | The measured count, value, pattern or disagreement, with units. |
| Source | Exact file/table/field or source record, its checksum and any full locus identity. |
| Calculation | Numerator and denominator where relevant; ordering, filtering, thresholds and transformations. |
| Evidence state | Observed value, observed zero, missing, unrun, failed, excluded or held. |
| Interpretation | The inference supported by those observations and any unresolved alternative. |
| Figure link | Actual figure, plotted data, script/configuration and caption used for this finding. |

Keep annotation, sequence similarity, domain calls, family membership,
phylogenetic evidence, literature and experimental context as named channels.
If they disagree, describe the disagreement before proposing an explanation.
An absent input cannot supply a zero. For a comparison, show the denominator
after exclusions and account for unavailable rows.

## 4. Draft concise text from those records

The assistant can connect evidence, explain calculations, identify missing
information and propose the next informative panel. Ask for **Power statements**
and factual two-to-four-sentence descriptions when you want writing material
rather than a finished manuscript. Each numerical assertion must lead back to
its observation and calculation. A useful paragraph states what was measured,
how it was measured and the scope of the result.

Draft the reader caption from the actual plotted values and selected run.
Draft Methods facts from the actual script, input selection, software versions,
parameters and execution record. A current executable's version probe does not
establish the version used in an earlier analysis. Leave an unrecorded version
or unrun channel explicitly unresolved. Preserve the user's wording and
decisions; proposed text does not replace their manuscript.

Record the existing caption-method fields described in
[Figure house rules](FIGURE_HOUSE_RULES.md) and the
[figure preflight manual](../wiki/Figure-Factory-Preflight-and-Methods-Manual.md).
Keep operational review notes with the analysis evidence; write the public
caption in terms of the material, measurements and comparison shown.

## 5. Check the actual figures and statements

Check plotted values against the selected source rows, including order,
denominators and typed missingness. Inspect each rendered page at its delivery
size for clipping, labels, legends, units and the intended subset. Run the
applicable caption/render checks from the figure guide and retain their complete
results. Those checks cover particular text or file properties; they do not
replace checking the calculation or looking at the page.

If a panel fails, retain the failed attempt and its reason. Correct it in a
fresh review destination and identify which output supersedes it. Do not
substitute an earlier image because its filename matches the desired figure.

## 6. Hand over the selected evidence and writing material

Return an index linking each intended figure to its actual state and files.
For completed figures, keep the plot-only/vector image, captioned delivery
image, authored caption/Methods, plotted table and executable script/config
together, following the figure house rules. Include source/output checksums,
execution and visual-review evidence, plus the short findings and unresolved
questions. A replay script should identify its environment requirements and
what it reproduces; do not imply it reruns an external analysis when it only
redraws saved tables.

For a public package, review the exact archive contents and selected source
closure before disclosure. Keep private data out of the package. File integrity,
successful rendering and scientific review are separate recorded results.
The [deliverable contract](DELIVERABLE_CONTRACT.md) defines the selected
handoff; [portable evidence roots](PORTABLE_EVIDENCE_WORKSPACE.md) cover
larger projects without moving their original evidence into the application.

Example request: “Use these reviewed public-genome packages to answer this
question. Make the selected figures with their data and scripts, and give me
Power statements, Methods facts and the unresolved evidence gaps.”
