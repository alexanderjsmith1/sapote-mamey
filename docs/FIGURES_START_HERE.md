# Make and review Mamey figures

Sapote–Mamey v9.7.449 · Mamey engine 1.9.174

Whatever route you take, the figure must meet the [figure house rules](FIGURE_HOUSE_RULES.md).

Sapote-Mamey has several figure routes with **different input contracts**. Start with
the question you want to show, then choose a route below. A finished image is
not a validated biological interpretation: keep the plotted values, source
identity, denominator, methods, and any missingness or assembly warning with it.

## Aggregate rendering and recovery

Use `python3 mamey_run.py render-all-figures --package <working-package-copy>` for selected post-run sets. Default output is inside that working package; the current aggregate has no external-output flag. Read [aggregate source contract](reference/06_CURRENT_SOURCE_SCOPE.md#aggregate-figure-rendering-selection-writes-and-completion) for defaults/optional sets, dry-run integrity writes, skips, child failures, gathered old files and completion limits. A zero exit or CURRENT_GATHER row does not establish newly rendered or visually reviewed outputs.

## Choose the route

| You want to see | Starting input | Command or guide |
| --- | --- | --- |
| One strain's BGC inventory or locus maps | A sealed gold package | Open the Mamey Zip and inspect `package/gold_figures/` and `package/locus_maps/`; regenerate a selected set with `render-figures` below. |
| The same Mamey feature across several strains | One `<strain>/package/` per strain in a runs directory | `cohort-figures` below; [figure catalog](FIGURE_CATALOG.md) explains F, G, D and extended panels. |
| A manuscript comparison from a master workbook | A checked workbook with strain registry and BGC master sheets | Export `figure_ready/` tables, then follow a [named figure recipe](../prompts/figure_prompts/_INDEX.md). The recipes are specifications, not an automatic renderer. |
| A custom aggregate evidence-coverage bar chart | Counted metrics TSV plus an explicit cohort manifest | [Aggregate evidence guide](FIGURE_FACTORY_NEXT.md). This specialized route does not read BLASTp databases itself. |
| A tree or BiG-SCAPE gene-cluster-family panel | Bound tree/database, tips or regions, and matching metadata | [Tree figure grammar](TREE_FIGURE_GRAMMAR.md) or [BiG-SCAPE walkthrough](BIGSCAPE_COHORT_WALKTHROUGH.md). Do not derive host metadata from a strain ID. |

Use the bundle's `mamey_run.py` entry point from the extracted code root so the
local bundled engine is selected. Commands below are templates: replace each
path with your real input and choose a **new output directory** for review. For .447 figure commands, supply a separately identified working package copy if the original sealed package must remain unchanged; [post-seal write boundaries](POSTSEAL_READERS.md#commands-that-still-author-package-data-in-447) explain the integrity-refresh wrapper and package-native sets.

## A single Mamey package

First inspect the package's `manifest.json`, `*_1_intake.json`, existing
`gold_figures/`, and `locus_maps/`. Record the engine/bundle version,
antiSMASH source, assembly, strain, region identities, and any figure holds.
Gold runs may already contain many images; you do not need to rerun extraction
to view them.

To regenerate the standard figure set from the package:

```bash
python mamey_run.py render-figures --package /path/to/strain/package \
  --outdir /path/to/new_review/standard --figure-set standard
```

The standard image destination can be external, but the .447 CLI still refreshes integrity records in the supplied package. Keep that package as a working copy.

Other supported sets include `domain-level`, `locus-maps`, `cohort-class`,
and `mamey-native`. `locus-maps` requires an output inside the supplied working package; `domain-level` can create package data even with external image output. The last two require `--workbook`; check
`python mamey_run.py render-figures --help` and the workbook's actual
sheets before using them. An empty Sapote judgment sheet is not an observed
negative finding.

## Compare several Mamey packages (cross-strain comparison)

The Mamey package outputs are standardized to enable comparative figure generation across the figure suite. 

The cohort command expects a directory containing `<strain>/package/`
subdirectories. Specify the strains deliberately; do not let an unrelated
reference package enter the denominator.

```bash
python mamey_run.py cohort-figures --runs-dir /path/to/checked_runs \
  --strains STRAIN_A,STRAIN_B,STRAIN_C \
  --out /path/to/new_review/cohort --series F --no-extended
```

The standard F series contains domain, class, tailoring, resistance, and
boundary-related panels; `--series G`, `D`, or `all` changes the set.
Omit `--no-extended` to request the extended panels too. Some panels have
extra admission requirements: the separately named `F13_bgc_domain_pca_2d`
needs a hash-bound cohort manifest and an independent denominator registry;
without these, read its HOLD receipt rather than treating it as an admitted
BGC PCA. The rendered `F13_strain_ordination_2d` is a different panel and
still needs visual review. The [catalog](FIGURE_CATALOG.md)
describes what each panel counts. Verify output sidecar data and captions for
every figure you use.

Do not combine two assemblies under one strain label. Reconcile package
input hashes, locus identities and bundle versions before comparing counts.
Edge and full-contig BGCs can inflate apparent class counts relative to
interior clusters. A heatmap of predicted biosynthetic capacity does not
establish expressed chemistry or antimicrobial activity.

Compare region or class counts only within one antiSMASH detection
strictness. Loose runs call more regions than default runs, saccharide above
all, so a table that mixes them makes the loose genomes look richer. For
packages, run `python tools/check_antismash_profile.py <runs_dir>`. For a
count table built from antiSMASH zips, build it with the tool that refuses
mixed input, and name the strictness in the caption:

```bash
python tools/region_table_one_setting.py --zips /path/to/zips --strictness loose \
  --out /path/to/new_review/regions_loose.tsv \
  --drop-contigs STRAIN=/path/to/STRAIN_removed_contigs.tsv
```

`--drop-contigs` removes regions on contigs that a decontamination took out.
Its receipt records each zip's sha256 and how many listed contigs matched.
The first TSV column may be headed `contig`, `record`, or `record_id`; that header is not counted.
Empty or duplicate strain drop-list options are refused. Zero matching regions are refused by default. After confirming the list and assembly IDs,
pass `--allow-zero-drop STRAIN` for an expected zero and retain the receipt. Duplicate
region filenames within one ZIP are refused because they would count the same region twice.
Unreadable ZIPs also cause a reported refusal rather than a partial table.

## Ecological synthesis needs another join

A Mamey package can have a generic source string such as a rebuild label.
For a bee/wasp, host or geography comparison, join each exact strain and
assembly to an independently checked metadata table with an explicit source
and missingness state. State which strains were included and excluded,
whether the unit is a strain or BGC, and the denominator for each group.
Keep an unknown source unknown. The figure prompt library includes an
[ecological synthesis recipe](../prompts/figure_prompts/deliverable_maps/map_hymenoptera_crossstrain.md);
it describes a proposed combination of panels, not proof that the metadata
are bound or the panels are ready for publication.

## Master-workbook and prompt figures

Only the workbook-driven prompt route requires the tidy `figure_ready/*.csv`
export:

```bash
python tools/export_figure_ready.py /path/to/master.xlsx /path/to/new_review/figure_ready
```

The exporter reads `A2_Strain_Registry` and `B1_BGC_Master`;
`A3_Run_Manifest` supplies corrected counts when present. Inspect the
exported `DATA_DICTIONARY.md`, `strain_summary.csv`,
`bgc_inventory.csv`, and the individual recipe's required columns.
Optional diagnostics or cross-strain findings files depend on workbook
sheets actually present. Do not manufacture missing fields to satisfy a
plot recipe. [Prompt usage](../prompts/figure_prompts/HOW_TO_USE.md)
explains how a human or LLM implements a named figure.

## Review before manuscript use

For each candidate figure, preserve the input paths and hashes, plotted
CSV/TSV, code and package version, caption/methods, and a visual proof at
the intended size. The caption should state the unit, group sizes,
exclusions, calculation, source of host labels, thresholds, and which
material was tested (crude extracts, fractions, or pooled). State limits as
what was measured. Do not print governance wording ("judgment deferred",
"not identity", "not production", "query strain", "class-level only") on the
figure, its footer, its key or its notes band; that belongs in the analysis
record. `mamey/figure_policy.py` owns the shared phrase list and the context rule for “class-level”; `tools/caption_guard.py` imports them.

Run the render check on every folder of finished figures before anyone uses
them:

```bash
python tools/figure_render_qc.py /path/to/figures --out /path/to/new_qa_directory --ocr require [--bioassay]
```

The checker uses neighboring SVG text first and falls back to macOS OCR of the PNG. It flags matched wording, markup, literal `\n`, NA labels and near-blank images; it does not judge overlaps, clipping, layout or scientific accuracy. `--ocr require` makes any `not_checked` text state exit 2, even when no ordinary error was found; readable SVG text satisfies this check without requiring OCR. In default `auto` mode, unchecked text can coexist with exit 0. `--warn-only` also permits exit 0 despite error findings, although `--ocr require` still refuses unchecked text. Inspect the report levels and keep unresolved text or artifact requirements held; exit 0 is not figure acceptance.

Wording on the figure is an error; matched wording in a readable caption is a warning. Missing `_plot_only.png`/PDF companions are **info**, and a missing caption is **warn**, so these omissions do not by themselves produce exit 2. An unreadable selected caption is an error. Caption selection tries several names, including generic `CAPTION.md`/`CAPTIONS.md`, and accepts the first existing file; it does not verify caption-to-figure identity or require nonempty caption text. DPI is warned only when metadata exists and differs from the requested value by more than five; missing DPI is not a refused state. Resolve required companions and caption/provenance bindings independently (`tools/figure_render_qc.py:206–211, 239–287`).

Folder discovery selects lowercase `*.png` and excludes `_plot_only` images, AppleDouble names, designated old/cache directories and `_withdrawn*` paths; it is not every image in the folder. An explicitly supplied `.PNG` file is accepted, and overlapping input paths can repeat figures. No discovered figures exits 1. For review copies, `--manifest MANIFEST.tsv` checks PNG review/source equality and any supplied `sha256`; companion files are sought beside the source. Its case-sensitive `DO NOT USE` note is an error. A neighboring SVG is not separately hash-bound to that PNG by this check. Keep the intended figure roster and verify the selected text source belongs to the same figure (`tools/figure_render_qc.py:81–109, 290–342`). `--bioassay` checks crude/fraction/pooled in the filename and warns when readable figure text lacks such a term; it does not establish what material was tested.

`RENDER_QC.tsv` contains finding rows, so a figure with no findings has no row; summary error/warning counts count findings rather than distinct figures. Preserve the intended input roster with both reports. The command writes fixed report names in `--out`, replacing existing reports, and may create an OCR cache there. Use a fresh QA directory for each retained review and archive the command, source/configuration and input hashes. Unexpected file/parser/image failures are not all converted into structured report findings; if the command fails, keep that review incomplete (`tools/figure_render_qc.py:345–405`).

### Methods-caption helpers: drafts and checks

`tools/figure_methods.py` provides Python `blurb(workflow)` and `caption(workflow, versions=..., params=..., result=..., extra=...)` helpers. The workflow key must exist in `WORKFLOWS`; an unknown key raises `KeyError`. Treat the resulting prose as a draft: the helper inserts fixed method descriptions and citations, formats caller-supplied metadata, and does not verify that the stated methods, parameters or results describe the selected figure. Match each statement to its actual source and execution receipts. Version discovery is a separate best-effort probe, not an automatic part of `caption()` or proof of the software used for an earlier result. See [external-tool provenance](EXTERNAL_TOOL_INVENTORY.md).

The current `caption()` always appends a claim-safety paragraph containing wording refused by the shared caption guard. Rewrite that operator-facing paragraph into appropriate analysis notes and retain the scientific limits as concrete statements of what was measured. Check the finished reader caption before use; do not assume the helper's draft already passes publication wording checks (`tools/figure_methods.py:131–165`; `tools/caption_guard.py:53–64`).

For Python callers, `check_caption(text)` raises `CaptionGovernanceError` on matched wording; `raises=False` returns `(phrase, reason)` findings. It collapses whitespace, ignores letter case and keeps only the longest overlapping phrase match. It does not validate methods, references, units, denominators, provenance or accuracy, and an empty string returns no findings. `scan_paths(paths)` reads UTF-8 files and returns only paths with findings. By default an unreadable input raises `CaptionUnreadableError`; with `strict=False`, such inputs are reported under `__unreadable__`. An empty path list or readable empty file also returns `{}`. Retain the intended input roster and confirm every file was readable and substantive before interpreting an empty report; it is not a checked-file inventory or scientific approval (`tools/caption_guard.py:49–91`). These helpers inspect text, not the rendered page.

### ANI/AAI label and displayed-value check

`python tools/ani_caption_check.py --input /path/to/caption.md --receipt /path/to/metric_receipt.json` checks already-computed caption/table text; it runs no ANI/AAI calculation. The receipt must be a JSON object declaring exactly `metric: "nucleotide_ANI"` or `metric: "core_SCG_AAI"` and `input_sha256` for the input bytes. For CSV/TSV, supply `value_column` or use a header named `value`, `percent` or `identity_pct`. Both files must be readable UTF-8. Keep the input, receipt and output together; the declared metric and matching hash bind text, not the underlying analytical run.

Use a metric-specific input. The checker requires the corresponding standalone `ANI` or `AAI` label and refuses the other label anywhere in the text, even in an explanatory comparison. Underscores/hyphens are treated as spaces for that label check. In ordinary text it extracts every matched number followed by `%`, without identifying which sentence or quantity it describes; an unrelated percentage can affect the result, and a minus sign is not retained by that extractor. In tables it reads only the chosen numeric column and skips blank cells. An empty/header-only input or no extracted value is refused, but a partly blank table can return a status without reporting skipped rows. Resolve units and missing cells independently; a fraction such as `0.95` is not converted to a percentage (`tools/ani_caption_check.py:19–22, 35–100`).

Exit 0 writes JSON `BOUNDARY` when any extracted value falls in the helper's fixed inclusive 94–96 range; otherwise it writes `NON_BOUNDARY`. That same software interval is applied to either declared metric. These labels do not establish taxonomy, analytical completeness or scientific acceptance, and `BOUNDARY` is not a failing exit status. Handled input/receipt/label/value errors exit 2. Preserve the displayed `values_pct`, `boundary_values_pct` and input hash, check the intended row/value roster, and report the actual analytical method and source receipts separately (`tools/ani_caption_check.py:75–126`). This checker does not require a particular boundary-warning sentence in the caption and does not inspect a rendered figure.

Inspect small text and legends for overlap. Use [Figure style](FIGURE_STYLE.md)
and [preflight and methods](../wiki/Figure-Factory-Preflight-and-Methods-Manual.md)
for the corresponding figure family. Keep visual QA, mechanical PASS, and
scientific acceptance distinct.

## Publication layout for R figures

`tools/sapote_pub_layout.R` gives every R figure the house page: the figure, white space, the public
caption, a thin rule, then small grey internal notes. `save_pub()` writes the captioned PNG and PDF, a
`_plot_only.png` for slides, and the caption file. `theme_pub()` renders markdown in titles, axes and
legends, so genus names can be italic.

```r
source("tools/sapote_pub_layout.R")
p <- ggplot(d, aes(genus, n)) + geom_col() + theme_pub()
save_pub(p, "FIG_035c_bgc_count_by_genus", "caption_public.md", "caption_internal.md",
         w = 7.5, h_body = 5, outdir = "FIG_035c_bgc_count_by_genus")
```

The public caption is plain scientific English. Tool versions, cutoffs, rulings, exclusions and paths go
in the internal notes. Neither carries governance wording. `save_pub()` refuses to overwrite a caption
file that belongs to another figure. Run `tools/figure_render_qc.py` on the folder afterwards.

## Selected assay values on an existing tree

Use [Tree assay track rendering](TREE_ASSAY_TRACK_RENDERING.md) for exact tip crosswalks and hash-bound, explicitly selected Figure Factory BIOASSAY tracks. The synthetic example runs without project data.

## Numeric completeness for the reference plot set
`tools/plot_examples.py` needs nonempty strain_summary.csv, class_prevalence.csv and class_by_strain.csv with their actual headers and a bound, unique isolate roster. Every plotted N50 must be finite and positive for the log axis, and the loss/count fields must be finite source-derived values. A workbook header/structural PASS does not establish that these values exist. A missing A3 correction value leaves corrected count and fragmentation loss uncomputed; do not substitute zero. Resolve those holds before this three-figure reference run. Other recipes may handle missingness explicitly, but must report any admitted subset and its denominator.
