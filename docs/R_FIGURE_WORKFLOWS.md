# Render existing figure data with R

These R scripts redraw a figure from data a Python tool has already produced. A **sidecar** is
that data file, a TSV or CSV written beside a figure. Pick the script for your data type below.
Keep the sidecar and its receipt with the files you render. If you still need to make the data,
start with [Figures start here](FIGURES_START_HERE.md). R and its packages are listed in
[prerequisites](PREREQUISITES.md#r-figure-stack).

## Run one

Run from the program folder. The bioassay heatmap takes a summary table, an output prefix, a size
profile and a title. It writes `<prefix>.svg` and `<prefix>.png`:

```bash
Rscript tools/sapote_bioassay_figure.R reviews/EXAMPLE-bioassay/bioassay_summary.tsv \
  reviews/EXAMPLE-bioassay/EXAMPLE_heatmap DOUBLE_COLUMN "EXAMPLE bioassay observations"
```

The script stops with a named error such as `BIOASSAY_SUMMARY_SCHEMA` when a required column is
missing. For the other scripts, the usage line is in the comment at the top of each file in
`tools/`. Most figures reach these scripts through a Python command, so you rarely call them
directly.

## Current renderer map

| Renderer | Accepted data | Present role |
|---|---|---|
| `sapote_bioassay_figure.R` | `bioassay_summary.tsv` | General material/target/time-point bioassay heatmap; SVG and PNG |
| `ggtree_rect_heatmap.R` | Newick plus normalized metadata TSV | Rectangular tree with isolation-source and location strips |
| `cohort_tree_ggtree.R` | GToTree/IQ-TREE tree plus optional annotation | Whole-genome marker tree |
| `ggtree_placement.R` | EPA-ng pruned tree plus exact annotation | Partial/full 16S placement display |
| `ggtree_placement_hostcolour.R` | Placement annotations with query host | Host-colored placement view |
| `ggtree_placement_bioassay.R` | Candida and MRSA activity fields | Narrow binary placement overlay for two fixed assays |
| `sapote_matrix_figure.R` | Registered wide matrix sidecars | Cohort heatmaps and bubble figures |
| `sapote_tidy_figure.R` | Registered tidy sidecars | Ordinations, ranked bars, and rosters |
| `sapote_strain_figure.R` | Per-strain figure sidecars | Per-strain bars, heatmaps, and scatterplots |
| `sapote_locus_map.R` | Exact-locus gene sidecar | BGC gene-arrow maps |
| `figure_factory_next_ggplot.R` | Factory plotted-data sidecar | Alternate rendering of already computed coverage values |

`sapote_figure_theme.R` supplies the shared style. The generated `tools/FIGURE_R_MANIFEST.tsv`
lists cohort schemas and geometry. Some of its entries are inferred, so check a script's own
header for its real arguments.

## Bioassay to tree workflow

1. Prepare measurements with [Bioassay Figure Factory](BIOASSAY_FIGURE_FACTORY.md).
2. Select one material/target/time/dose scope and keep the selection receipt.
3. Bind the resulting track to exact tree-tip IDs.
4. Follow [tree assay track rendering](TREE_ASSAY_TRACK_RENDERING.md) for the
   adapter and R command. Keep its data, mapping, methods and output receipt.

Recorded zero and `NOT_MEASURED` remain distinct. The optional `fraction_set_max`
view selects among pooled material means from a named fraction set; it is not
an experiment-specific maximum. Report experiment and observation counts with it.
The Candida and MRSA placement renderer covers only those two assays.

## Placement and genome-tree displays

`placement_display.py` writes display Newick and metadata for
`ggtree_rect_heatmap.R`; the upstream EPA-ng/gappa result supplies the topology.
Switching concise/detailed metadata views changes display, not tree inference.
Label a 16S placement and a genome-marker tree as their respective channels.

For numeric assay strips, the [tree assay track workflow](TREE_ASSAY_TRACK_RENDERING.md)
uses `build_tree_tracks.py`, `render_tree_one_bar_row.R` and
`render_tree_bar_groups.R`. It preserves selection receipts and exact tip IDs.

## Check the rendered files

Verify the consumed sidecar against its producer hash. Record the R/theme source
hashes, arguments, library versions and new output hashes. Use a new output prefix. A rerun
with the same prefix overwrites the earlier files.
Inspect the final plot at its intended size, including dense columns and labels.

For gene maps, use `render-figures --figure-set locus-maps` first ([locus map v8](LOCUS_MAP_V8.md)).
`sapote_locus_map.R` is an alternate arrow view with two label rows. It reads `label_displayed=YES`
from the map's CSV. It has no comparator or evidence panel and no receipt. It stops when the
`panel` identity does not have four non-blank parts (strain / node / region / BGC alias). It reads
strand `+` or `1` as forward and `-` or `-1` as reverse, and draws any other strand, including
blank, as a box with no arrowhead. It does not check the identity against the package; compare
the `panel` with the v8 receipt yourself.

New raw-plate layouts, in-vivo schemas, categorical assay strips and experiment-level
selection need supported inputs before rendering. Reference structures use the
[NP Atlas/RDKit route](NPATLAS_PROVISIONING.md); label the structure as a comparator
and keep its source identifier and license.
