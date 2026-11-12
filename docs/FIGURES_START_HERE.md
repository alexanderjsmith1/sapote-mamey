# Make and review figures

This page routes you from the figure you want to the command or tool that draws it. For what every
finished figure must meet (format, caption, labels), see the [house rules](FIGURE_HOUSE_RULES.md).
For what may appear on a plot, see [figure style](FIGURE_STYLE.md). This page does not repeat either.

Run commands from the program folder. First install and first run: [first run](reader/01_FIRST_RUN.md).
Replace `EXAMPLE` with your strain name.

## Make a working copy first

Figure commands refresh checksums inside the package they are given, and `locus-maps` must write
inside it. Copy the package once and run the figure examples below on the copy:

```bash
mkdir runs/EXAMPLE/package_work && cp -R runs/EXAMPLE/package/. runs/EXAMPLE/package_work/
```

Use a fresh destination: `mkdir` refuses an existing folder. If copying fails, stop and inspect the partial folder before retrying elsewhere. The examples use `runs/EXAMPLE/package_work`. Your original stays unchanged. `cohort-figures` and the profile check below read the original.

## Terms

- **Package**: the folder `runs/EXAMPLE/package/` that `run` writes for one strain.
- **Sealed package**: a package that passed the integrity checks. Several figure commands refresh
  checksums inside it, even when images go elsewhere. [Post-seal write boundaries](POSTSEAL_READERS.md#commands-that-write-into-the-package)
  lists which.
- **Triage board**: `*_4_triage_board.csv` in the package, the ranked table of BGCs (biosynthetic
  gene clusters). `AB_auto` and `AF_auto` are its antibacterial and antifungal routing priors; the
  lead charts label their axes "Antibacterial routing prior (AB_auto)" and "Antifungal routing
  prior (AF_auto)". Triage rows can include BGCs excluded from leads: those downgraded by a
  [standing rule](GLOSSARY.md), or flagged as primary metabolism or a mobile element. Lead outputs,
  such as the top-lead charts and `manifest_short.json`, leave those out. Compare complete locus
  identities against the inventory and inspect the scoring-coverage receipt before claiming every
  region is represented; a coverage warning does not establish completeness.
- **F, G and D series**: three sets of cohort panels. F is heatmaps, G is complementary panels, D is
  dot and bubble plots.
- **dDDH**: digital DNA-DNA hybridization, a genome similarity score against a type strain.
- **GCF**: gene cluster family, a group of BGCs under one clustering setting. Membership does not
  prove a shared compound. See the [glossary](GLOSSARY.md).

## Choose a route

| I want | Run or open | Needs |
|---|---|---|
| Plots already made for one strain | `runs/EXAMPLE/package/gold_figures/` and `locus_maps/` if present | A finished `run` |
| Top ten antibacterial and antifungal leads | `python mamey_run.py render-figures --package runs/EXAMPLE/package_work --outdir reviews/EXAMPLE/standard` | Package with a triage board |
| Gene maps of each BGC | `python mamey_run.py render-figures --package runs/EXAMPLE/package_work --figure-set locus-maps` | Package; see below |
| Several post-run sets at once | `python mamey_run.py render-all-figures --package runs/EXAMPLE/package_work --dry-run`, then without `--dry-run` | Working package |
| Domain-level panels | `render-figures --figure-set domain-level` | Package |
| Strain-by-class heatmap, or the master-workbook set | `render-figures --figure-set cohort-class` or `mamey-native`, with `--workbook <file.xlsx>` | Cohort or master workbook |
| Panels across several strains | `python mamey_run.py cohort-figures --runs-dir runs --strains EXAMPLE --out reviews/EXAMPLE/cohort` | One package per strain |
| Evidence-coverage bar chart | `python mamey_run.py figure-factory --config <config.json>` | A hash-bound config; see [Figure Factory](FIGURE_FACTORY_NEXT.md) |
| Tidy tables for ggplot or matplotlib | `python tools/export_figure_ready.py <master.xlsx> <new-folder>` | Master workbook; see below |
| Gene BLASTp similarity | `python tools/blastp_identity_figures.py --help` | Per-gene results and a genome table |
| HPLC trace panels | `python tools/hplc_trace_panels.py --help` | Detector arrays; one material per figure |
| Novel-and-active tile table | `python tools/novel_and_active_figure.py --help` | Table; `--material` is `crude_extract`, `fraction` or `side_by_side` |
| dDDH against the closest type strain | `python tools/taxonomy_T05_figures.py --cohort <tsv> --data <tsv> --out reviews/EXAMPLE/T05_ddh` | Two TSVs; `--out` is a file stem without a suffix; `--help` lists columns |
| Tree with at most four references per isolate | `python tools/max4_tree_figure.py --help` | Finished IQ-TREE run with a `.contree` |
| Tree, ANI, GCF or clinker panel | [Tree grammar](TREE_FIGURE_GRAMMAR.md), [BiG-SCAPE](BIGSCAPE_COHORT_WALKTHROUGH.md), [BGC figures](BGC_FIGURES.md) | Matching outputs |
| Assay tracks on a tree | [Tree assay tracks](TREE_ASSAY_TRACK_RENDERING.md) | Tip crosswalk |
| Interactive HTML widgets for one strain | `python mamey_run.py render-widgets runs/EXAMPLE/package_work --outdir reviews/EXAMPLE/widgets` | Package; see [widget deliverables](WIDGET_DELIVERABLES.md) |
| Slide decks for one strain | `python tools/strain_slides.py build --sources EXAMPLE_sources.json --out decks/EXAMPLE/` | The `slides` extra and a sources file; see [strain slides](STRAIN_SLIDES.md) |
| Bioassay plate summaries | [Bioassay figure factory](BIOASSAY_FIGURE_FACTORY.md) | Plate tables and a plate-map profile |
| Protein-space viewer for a cohort | [Standalone protein space](PROTEIN_SPACE_STANDALONE.md) | A viewer and catalogue made outside the bundle |
| A figure in R | [R workflows](R_FIGURE_WORKFLOWS.md) | Saved sidecar data |
| Panel list and IDs | [Figure catalog](FIGURE_CATALOG.md) | None |
| A workbook recipe written by hand | [Prompt recipes](../prompts/figure_prompts/_INDEX.md) | They guide an implementation; they do not render |

Every tool listed takes `--help`. Keep untested assay cells separate from blank cells.

## Lead charts

```bash
python mamey_run.py render-figures --package runs/EXAMPLE/package_work \
  --outdir reviews/EXAMPLE/standard
```

Use a new folder so earlier images stay. Without `--outdir`, output goes to `<package>/figures_rendered/`.

Success: the folder holds `top_antibacterial_leads.png` and `.svg`, `top_antifungal_leads.png` and
`.svg`, `figure_manifest.csv` and `FIGURE_QA.md`. Exit code 0 alone does not prove both charts
exist, so check the files and read `FIGURE_QA.md`.

Failure: `NO_FIGURES_RENDERED.md` appears. Causes are a missing triage board (exit 1), a missing
plotting library, a render error, or no eligible rows. The command uses the first
`*_4_triage_board.csv` in sorted order. Run `ls runs/EXAMPLE/package_work/*_4_triage_board.csv`; one file
should match.

## Locus maps

```bash
python mamey_run.py render-figures --package runs/EXAMPLE/package_work --figure-set locus-maps
```

Omit `--outdir` to write to `<package>/locus_maps/`. If you set it, give an absolute path inside the
package. A relative path is refused with "must resolve inside the sealed package", even when it
points inside the package. A capped run skips locus maps by default; an explicit
`--locus-maps on` requests them during the run. If the maps are missing, use this command
to render them from the working package (see [first run](reader/01_FIRST_RUN.md)).

## Several packages at once

`render-all-figures` writes inside the package and has no output option. The default sets are
`smoke,brief,locus-maps,figure-suite,domain-level`. Add `--all --workbook <file.xlsx>` for the
workbook sets. Its [source contract](reference/06_CURRENT_SOURCE_SCOPE.md#aggregate-figure-rendering-selection-writes-and-completion)
covers selection, skips and writes. Read each set's own result.

## Cohort panels

```bash
python mamey_run.py cohort-figures --runs-dir runs --strains EXAMPLE \
  --out reviews/EXAMPLE/cohort
```

`--series F` is the default. `G`, `D` and `all` select the other sets. An 11-figure extended suite is
added unless you pass `--no-extended`. For Interior, Edge and Full-contig counts, use G's
`bgc_boundary_status` or the extended `fig8_boundary_profile`.

Panel `F13_bgc_domain_pca_2d` needs `--f13-cohort-manifest`, `--f13-cohort-manifest-sha256`,
`--f13-denominator-registry` and `--f13-denominator-registry-sha256` (also `--f13-profile`).
Without them the run writes a HOLD receipt instead.

Before combining packages, use one assembly per strain label and the same antiSMASH detection
strictness. Check one package, or a folder holding only the selected packages:

```bash
python tools/check_antismash_profile.py runs/EXAMPLE/package
```

Exit 0 means one known profile across all strains. Exit 1 means mixed or unknown profiles, which
includes a duplicate strain ID, so a broad runs folder with retry copies will fail. Only `strict`,
`relaxed` and `loose` count as known. If a run recorded `unknown`, re-run the strain with
`--antismash-profile` set to the strictness you used in antiSMASH.

For a region table straight from ZIPs, run `python tools/region_table_one_setting.py --help`. It
needs `--strictness` and refuses mixed strictness, unreadable ZIPs and duplicate region filenames.
`--drop-contigs` takes a list of contigs you actually removed. Zero matching dropped regions is
refused unless you pass `--allow-zero-drop STRAIN` for that strain after review.

For host or geography comparisons, join each strain to checked metadata. Keep unknown sources
unknown and state whether rows count strains or BGCs. The
[ecological recipe](../prompts/figure_prompts/deliverable_maps/map_hymenoptera_crossstrain.md)
shows the possible panels.

## Export a master workbook

A master workbook is the cumulative Excel file that `run --master` creates and updates (not the
Strain Master data home). The exporter needs one with sheets `A2_Strain_Registry` and `B1_BGC_Master`;
`A3_Run_Manifest` supplies corrected counts. A per-strain workbook has a different schema. To get a
master, add `--master` to a fresh extraction. It re-extracts the strain, so it takes as long as a
full run. With `--outdir runs/master`, its package lands in `runs/master/EXAMPLE/`, not
`runs/EXAMPLE/`. Give `--taxonomy` and `--source` if you know them, and leave them off if you do not:

```bash
python mamey_run.py run --strain EXAMPLE --input-zip ~/Downloads/EXAMPLE.zip \
  --master ../EXAMPLE-master.xlsx --outdir runs/master
```

Check the workbook, then export into a new or empty folder:

```bash
python -m mamey.workbook_schema_check ../EXAMPLE-master.xlsx
python tools/export_figure_ready.py ../EXAMPLE-master.xlsx reviews/EXAMPLE/figure_ready
```

A pass prints `"status": "PASS"`. Any other status stops here. Recalculate and save formula-based
workbooks first, because the export reads saved formula values.

Read `DATA_DICTIONARY.md` in the output, plus `strain_summary.csv` and `bgc_inventory.csv`. In
`bgc_inventory.csv` the BGC's region is the column `region`. Key a join on strain, full contig,
region and BGC alias. Leave missing correction values uncomputed; do not fill them with zero.
Hold any nonnumeric, negative or fractional TIGRFAM cell for correction, since the exporter can
turn invalid text into zero or truncate counts. Check the registry against your strain roster, or
duplicate rows will distort class-prevalence percentages. If an export fails, keep the partial
output and retry in a new folder.

`python tools/plot_examples.py <figure_ready_dir>` draws reference plots from the export. It needs
nonempty class tables, a unique isolate roster and positive finite N50 values. Follow
[prompt usage](../prompts/figure_prompts/HOW_TO_USE.md) for a workbook recipe.

## Check the images

Before drawing, read [figure style](FIGURE_STYLE.md). To package a finished figure with its caption
band and `_CAPTION.md` sidecar, run `python tools/caption_band.py <plot.png> <caption.md> --outdir <dir>`
(see [tools/caption_band.py](../tools/caption_band.py) and house rule 2).

Run the render check on a folder of figures. The width is the size at which you will embed them:

```bash
python tools/figure_render_qc.py reviews/EXAMPLE/standard \
  --out reviews/EXAMPLE/standard-qa --ocr require --print-width-in 6 --dpi 300
```

`--ocr require` needs the macOS text reader, which compiles on first use; without it the command
exits 2. Use `--ocr auto` on a machine that lacks it. It prints `checked N; errors E, warnings W, text not checked T, notes I` and writes `RENDER_QC.md`
and `RENDER_QC.tsv` in `--out`. Exit codes:

- 0: no error findings (warnings do not fail).
- 1: a path was not found, or no figures were found. It skips `*_plot_only.png`.
- 2: an error finding, unless you pass `--warn-only`; or `--ocr require` with text that could not be
  checked; or a refused completed-packet receipt.

Without `--print-width-in`, effective DPI and minimum text size read `NOT_CHECKED`. Minimum text is
8 pt (`--min-text-pt`). Add `--bioassay` for assay figures; the file name must say crude, fraction
or pooled. The checker does not judge layout, and its TSV lists findings rather than every image
checked. Look at every image yourself for clipped labels, overlaps, wrong units and the intended
rows.

To queue a Figure Factory set for review, use [review queue](FIGURE_REVIEW_WORKFLOW.md); to record
the chosen outputs, use [review decisions](FIGURE_OWNER_REVIEW_WORKFLOW.md). Writing that follows:
[Evidence to report](EVIDENCE_TO_REPORT.md).

## Captions and checks

- `tools/figure_methods.py` drafts method text from fixed descriptions and your metadata. Check every
  statement against the actual run.
- `tools/caption_guard.py` checks caption wording. Run it on the finished caption.
- `tools/ani_caption_check.py --input <caption-or-table> --receipt <receipt>` checks that text uses
  ANI or AAI correctly. The receipt must declare `nucleotide_ANI` or `core_SCG_AAI`. It checks labels
  and values, not the analysis.
- For R figures, use `save_pub()` as described in [R workflows](R_FIGURE_WORKFLOWS.md).
- For a tree figure, check the IQ-TREE log and `.contree` first. Use deposited organism, strain,
  accession and type-material status on the tips.

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

Sapote–Mamey v9.7.465 · Mamey engine 1.9.181
