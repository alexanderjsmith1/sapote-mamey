# Render existing figure data with R

Choose the bundled renderer for your tree or data sidecar. Keep the producer's
data and receipt with the rendered files. If you still need to make the data,
start with [Figures start here](FIGURES_START_HERE.md).

## Current renderer map

| Renderer | Accepted data | Present role |
|---|---|---|
| `sapote_bioassay_figure.R` | `bioassay_summary.tsv` | General material/target/time-point bioassay heatmap; SVG and PNG |
| `ggtree_rect_heatmap.R` | Newick plus normalized metadata TSV | Rectangular tree with isolation-source and location strips |
| `cohort_tree_ggtree.R` | GToTree/IQ-TREE tree plus optional annotation | Whole-genome marker tree |
| `ggtree_placement.R` | EPA-ng pruned tree plus exact annotation | Partial/full 16S placement display |
| `ggtree_placement_hostcolour.R` | Placement annotations with query host | Host-colored placement view |
| `ggtree_placement_bioassay.R` | Legacy Candida/MRSA activity fields | Narrow binary placement overlay retained for compatibility |
| `sapote_matrix_figure.R` | Registered wide matrix sidecars | Cohort heatmaps and bubble figures |
| `sapote_tidy_figure.R` | Registered tidy sidecars | Ordinations, ranked bars, and rosters |
| `sapote_strain_figure.R` | Per-strain figure sidecars | Per-strain bars, heatmaps, and scatterplots |
| `sapote_locus_map.R` | Exact-locus gene sidecar | BGC gene-arrow maps |
| `figure_factory_next_ggplot.R` | Factory plotted-data sidecar | Alternate rendering of already computed coverage values |

`sapote_figure_theme.R` supplies the shared style.  The generated `tools/FIGURE_R_MANIFEST.tsv`
describes cohort schemas and geometry; some entries are inferred from schemas,
so use the selected figure's guide for its actual rendering command.

## Bioassay to tree workflow

1. Prepare measurements with [Bioassay Figure Factory](BIOASSAY_FIGURE_FACTORY.md).
2. Select one material/target/time/dose scope and keep the selection receipt.
3. Bind the resulting track to exact tree-tip IDs.
4. Follow [tree assay track rendering](TREE_ASSAY_TRACK_RENDERING.md) for the
   adapter and R command. Keep its data, mapping, methods and output receipt.

Recorded zero and `NOT_MEASURED` remain distinct. The optional `fraction_set_max`
view selects among pooled material means from a named fraction set; it is not
an experiment-specific maximum. Report experiment and observation counts with it.
The legacy binary Candida/MRSA placement renderer is limited to that assay scope.

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
hashes, arguments, library versions and new output hashes. Use a fresh output
prefix: `sapote_save_pair` writes directly and can replace existing files.
Inspect the final plot at its intended size, including dense columns and labels.

`sapote_locus_map.R` draws gene arrows with two label rows and expects
`label_displayed=YES`. It lacks the v8 comparator/evidence panel and v8 receipt.
For that content use [locus-map v8](LOCUS_MAP_V8.md) with its rich CSV and checks.

New raw-plate layouts, in-vivo schemas, categorical assay strips and experiment-level
selection need supported inputs before rendering. Reference structures use the
[NP Atlas/RDKit route](NPATLAS_PROVISIONING.md); label the structure as a comparator
and keep its source identifier and license.

<a id="still-needed"></a>
<a id="exact-selected-assay-tracks"></a>
<a id="r-output-binding-and-locus-map-limits"></a>
