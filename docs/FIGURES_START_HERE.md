# Make and review figures

Open the plots from a Mamey package, draw another set, or choose a renderer for
an existing comparison. You need the package or the source tables for the
figure you want. Start with `runs/EXAMPLE/package/gold_figures/` and `locus_maps/`;
use existing images when they answer the question.

Run commands from the program folder. Replace `EXAMPLE` with your strain name.
The examples use a working package: some commands update package data or
integrity records even when images go elsewhere. Keep a sealed original unchanged.
See [post-seal write boundaries](POSTSEAL_READERS.md#commands-that-still-author-package-data-in-447).

## Draw the standard lead charts

This reads `*_4_triage_board.csv` and draws up to ten eligible rows by `AB_auto`
and `AF_auto` score, after standing-rule and primary-metabolism exclusions.
Choose a new review folder so the earlier images stay available:

```bash
python mamey_run.py render-figures --package runs/EXAMPLE/package \
  --outdir reviews/EXAMPLE/standard
```

`standard` is the default set. Open `top_antibacterial_leads.png` and
`top_antifungal_leads.png`, then read `figure_manifest.csv` and `FIGURE_QA.md`.
If the triage board is missing, read `NO_FIGURES_RENDERED.md`.
The catalog's gold panels are already in `gold_figures/`; this command draws
the two lead charts rather than rebuilding that collection.

Choose `--figure-set locus-maps` for gene maps; its output must be inside the
working package. `domain-level` can create metric tables in the package.
`cohort-class` and `mamey-native` require `--workbook` with suitable sheets.
Use `render-figures --help` for their arguments and the
[figure catalog](FIGURE_CATALOG.md) for the panels.

For several post-run sets together, use `render-all-figures --package` with the
working package. It writes there and has no external-output option. Its
[source contract](reference/06_CURRENT_SOURCE_SCOPE.md#aggregate-figure-rendering-selection-writes-and-completion)
explains selection, skips and writes, including dry-run integrity updates.
Read the individual set results: `CURRENT_GATHER` can refer to an older file.

## Choose another view

| Result | Inputs | Where to start |
|---|---|---|
| Several strains | One strain/package folder per selected strain | Cohort command below; figure catalog |
| Master-workbook comparison | Checked strain registry and BGC master sheets | Export below, then a [named recipe](../prompts/figure_prompts/_INDEX.md) |
| Evidence-coverage bar chart | Counted metrics TSV and cohort manifest | [Aggregate evidence guide](FIGURE_FACTORY_NEXT.md) |
| Gene BLASTp similarity | Per-gene results and genome/context table | `tools/blastp_identity_figures.py`; choose top1/top10 and best/nr/clustered for the question |
| HPLC trace panels/pages | Native detector arrays, channel proof, metadata and run table | `tools/hplc_trace_panels.py`; keep one material per figure, without smoothing |
| Novel-and-active tile table | Isolate rows with 16S identity, GenBank counts, dDDH and separate crude/fraction inhibition | `tools/novel_and_active_figure.py`; choose crude, fraction or separate side-by-side columns |
| Tree, ANI, GCF or clinker panel | Matching tree/comparison outputs and metadata | [Tree grammar](TREE_FIGURE_GRAMMAR.md), [BiG-SCAPE](BIGSCAPE_COHORT_WALKTHROUGH.md), [BGC figures](BGC_FIGURES.md) |
| R view of saved data | Sidecars matching the selected schema | [R workflows](R_FIGURE_WORKFLOWS.md) |
| Assay tracks on a tree | Exact tip crosswalk and selected assay tracks | [Tree assay tracks](TREE_ASSAY_TRACK_RENDERING.md) |

Use each tool's `--help` and the [house rules](FIGURE_HOUSE_RULES.md) for its
inputs and output formats. The [optional galleries](OPTIONAL_FIGURE_FACTORY_TOOLS.md)
use example data. Prompt recipes need implementation; they are not an automatic
renderer. Keep untested assay cells separate from blank cells.

## Draw cohort panels

The runs directory contains one `strain/package/` folder per strain. This example
selects `EXAMPLE`; add comma-separated strain names only after checking their inputs:

```bash
python mamey_run.py cohort-figures --runs-dir runs --strains EXAMPLE \
  --out reviews/EXAMPLE/cohort
```

The default F series covers domain, class, tailoring and resistance views;
extended panels are included. Choose `--series G`, `D` or `all` for another set.
For Interior/Edge/Full-contig counts, use G's `bgc_boundary_status` or extended
`fig8_boundary_profile`. Check the sidecar data for each image you select.

Use one assembly per strain label. Compare versions, input hashes and full locus
identities before combining packages. For region/class counts, check that the
antiSMASH detection strictness matches. Inspect one selected package with:

```bash
python tools/check_antismash_profile.py runs/EXAMPLE/package
```

For a comparison, point the checker at a folder containing only the selected
packages. It refuses duplicate strain IDs; a broad runs folder can include retry
copies and saved report snapshots.

For a count table made directly from ZIPs, use
`tools/region_table_one_setting.py` with the recorded strictness. Its `--drop-contigs`
option accepts a decontamination list; choose it only for contigs actually removed.
The tool refuses mixed strictness, unreadable ZIPs and duplicate region filenames.
It also refuses zero matching dropped regions unless you explicitly confirm that
case with `--allow-zero-drop`. Keep the receipt and input hashes.

The separately named `F13_bgc_domain_pca_2d` requires a hash-bound cohort manifest
and an independent denominator registry. Read its HOLD receipt when those are
missing. `F13_strain_ordination_2d` is a different panel.

For host or geography comparisons, join each strain and assembly to checked
metadata. Keep unknown sources unknown and state the groups, exclusions and
whether rows count strains or BGCs. The [ecological recipe](../prompts/figure_prompts/deliverable_maps/map_hymenoptera_crossstrain.md)
shows the possible panels.

## Export a master workbook

The exporter needs a coded master with `A2_Strain_Registry` and `B1_BGC_Master`;
`A3_Run_Manifest` supplies corrected counts. The per-strain workbook is a different
schema. If you need a master, create one during a fresh extraction:

```bash
python mamey_run.py run --strain EXAMPLE --input-zip ~/Downloads/EXAMPLE.zip \
  --master ../EXAMPLE-master.xlsx --outdir runs/master
```

`--master` requests the cumulative workbook; `--outdir` keeps this extraction
separate from the first run. Then export into a new or empty folder:

```bash
python -m mamey.workbook_schema_check ../EXAMPLE-master.xlsx
python tools/export_figure_ready.py ../EXAMPLE-master.xlsx \
  reviews/EXAMPLE/figure_ready
```

Read `DATA_DICTIONARY.md`, `strain_summary.csv`, `bgc_inventory.csv` and the
chosen recipe's required columns. Join the export's `region` to the inventory's
`antiSMASH_Region` tag, keeping strain, full contig and BGC alias in the key;
the inventory's numeric `Region` is a different column. Leave missing correction values uncomputed;
do not fill them with zero. `tools/plot_examples.py` also needs nonempty
class-prevalence/class-by-strain tables, a unique isolate roster and positive
finite N50 values. Follow [prompt usage](../prompts/figure_prompts/HOW_TO_USE.md)
when implementing a workbook recipe.

Check the master registry against the selected strain roster. Class-prevalence
percentages use its row count, so duplicate registry rows or unregistered BGC
strains distort the denominator. Recalculate and save formula-based workbooks
before export: this adapter reads saved formula caches.

Keep missing diagnostic counts uncomputed. Hold nonnumeric, negative or fractional
TIGRFAM cells for correction; the exporter can turn invalid text into zero or
truncate counts. Optional diagnostic/finding CSVs are absent when their source
rows are absent, even though the dictionary lists them with zero rows.

Save the workbook/output hashes and keep `release_policy.json` with the tables.
If an export fails, keep the partial output and choose a new folder for retry.

## Check the actual images

Keep each image with its source table and checksum, renderer/version, calculation,
caption and Methods facts. Follow the [house rules](FIGURE_HOUSE_RULES.md) for
plot-only/vector and captioned formats. Captions name the unit, group sizes,
exclusions, thresholds and tested material. Keep work-status notes off the figure.

Run this check for a figure intended to be embedded **6 inches wide**; change the
width to your actual layout. `--ocr require` refuses unchecked text. Use a fresh
QA folder:

```bash
python tools/figure_render_qc.py reviews/EXAMPLE/standard \
  --out reviews/EXAMPLE/standard-qa --ocr require --print-width-in 6
```

Read both `RENDER_QC.md` and `RENDER_QC.tsv`, then look at every selected image
for clipped labels, overlaps, correct units and the intended rows. The checker
reads neighboring SVG text or uses macOS OCR; it does not judge layout.
Without a declared width, effective DPI and minimum text size are `NOT_CHECKED`.
Raster-only text can remain unmeasurable. The default text minimum is 8 points.

Add `--bioassay` for assay figures: the filename must identify crude, fraction
or pooled material. Check the actual material against the experiment.
The checker can warn about missing captions or companion files without failing;
resolve those against your requested deliverables. Its TSV lists findings,
not every successfully checked image, so keep the intended figure roster too.
It excludes plot-only PNGs and designated cache/withdrawn paths during discovery.
No discovered figures exits 1; unchecked required text exits 2. A report does not
independently bind a neighboring caption/SVG to the image: check those matches.

Use the [review queue](FIGURE_REVIEW_WORKFLOW.md) for a Figure Factory set and
[review decisions](FIGURE_OWNER_REVIEW_WORKFLOW.md) to record the selected outputs.
[Evidence to report](EVIDENCE_TO_REPORT.md) covers the writing that follows.

## Caption and specialist tools

`tools/figure_methods.py` drafts method text from fixed descriptions and your
metadata. Check every statement against the actual run, then apply
`tools/caption_guard.py` to the finished caption. The guard checks wording;
verify that the file contains the intended caption and was readable.
Keep `operator_notes()` separate from publication captions. For R figures, use
`save_pub()` as described in the R workflow instead of inventing an export method.

`tools/ani_caption_check.py` reads already-computed text/table values plus a
matching receipt declaring `nucleotide_ANI` or `core_SCG_AAI`. Use metric-specific
text with the correct ANI/AAI label and percentage units. In prose, it extracts
all percentages; in tables it reads the selected numeric column and skips blanks.
It does not convert a fraction to a percentage. This is a label/value check,
so keep the underlying analysis receipt too.

For an existing IQ-TREE result, `tools/max4_tree_figure.py` builds metadata and
calls `tools/render_max4_tree.R`. First check the completed log and `.contree`.
Use deposited organism, strain, accession, source/country and type-material status;
log corrections and their evidence. Its JSON spec or `--set` options control
rooting, labels and layout. The PDF text-size check refuses text below 8 points.
`--max-refs-per-query 4` checks that limit when an anchor column assigns references.

`tools/taxonomy_T05_figures.py` draws dDDH rows from supplied results. Reference
name/strain/accession columns give the reference label; `label_md` can replace an
isolate label. Choose panel dimensions, legend and genus colors through its
arguments and the bundle palette. Check the input labels before rendering.

<a id="choose-the-route"></a>
<a id="a-single-mamey-package"></a>
<a id="aggregate-rendering-and-recovery"></a>
<a id="compare-several-mamey-packages-cross-strain-comparison"></a>
<a id="ecological-synthesis-needs-another-join"></a>
<a id="master-workbook-and-prompt-figures"></a>
<a id="review-before-manuscript-use"></a>
<a id="publication-layout-for-r-figures"></a>
<a id="selected-assay-values-on-an-existing-tree"></a>
<a id="genome-tree-with-at-most-four-references-per-isolate"></a>
<a id="dddh-with-the-closest-type-strain"></a>
<a id="numeric-completeness-for-the-reference-plot-set"></a>

Sapote–Mamey v9.7.461 · Mamey engine 1.9.177
