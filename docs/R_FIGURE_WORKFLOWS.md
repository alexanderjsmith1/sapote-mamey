# R figure workflows

Use this page when you already have a tree or plotted-data sidecar and need its
bundled R renderer. Match the **Accepted data** column below to your input, then
follow that figure family's guide. If you still need to produce the data, return to
[Figures start here](FIGURES_START_HERE.md). For quantitative assay values beside
an existing tree, use [Exact selected assay tracks](#exact-selected-assay-tracks).

The Python producer performs joins, validation, aggregation, provenance binding
and typed missingness before rendering. Keep those admitted sidecars with the R
output; do not recover scientific selections from filenames or guess how to
reshape raw assay exports.

The R files under `tools/` are maintained source files; an analysis does not generate them.
For 16S placement trees, `placement_display.py` writes a display-specific Newick plus annotation
TSV, then passes both through `ggtree_rect_heatmap.R`. The Newick topology comes from the upstream
EPA-ng/gappa placement run. R/ggtree handles layout, labels, metadata strips, the scale bar, PNG,
and PDF. Changing a concise, detailed, no-geography, or internal label view reuses the admitted
tree and does not rerun phylogenetic inference.

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

`sapote_figure_theme.R` is shared style policy rather than a standalone renderer. The generic
bioassay Figure Factory now supplies the broader assay path; the legacy binary placement script
must not be applied to other targets, fraction types, or time points.
`tools/FIGURE_R_MANIFEST.tsv` is a generated description of cohort figure schemas,
geometry and source locations. Read its notes: some geometry is inferred from a
sidecar schema where no renderer call was found. Use the maintained renderer map
above and the specific figure guide to choose an R script; the manifest is not a
registry for standalone tree-track renderers. The R scripts remain source files
in the bundle.

## Bioassay to tree workflow

Use [Bioassay Figure Factory](BIOASSAY_FIGURE_FACTORY.md) for the observation and
selection inputs. Once a selected track exists, continue with [tree assay track
rendering](TREE_ASSAY_TRACK_RENDERING.md) for the adapter, exact tip metadata and R
commands. The steps below explain the data path between those guides.

1. Map the original 96- or 384-well export into the canonical observation schema. Keep the source
   plate, well, material lineage, target resolution, time point, replicate type, control state, and
   row disposition.
2. Run `figure-factory` with `bioassay_observation_summary_v1`. The factory verifies the source
   hash and emits admitted rows plus exact-group summaries.
3. For a tree overlay, provide `tree_track_selection` with one target, target state, time point,
   material type, strain roster, and an explicit material ID per strain. The resulting
   `bioassay_tree_track.tsv` preserves a measured zero separately from `NOT_MEASURED`.
4. Bind the track through an exact tree-tip/strain crosswalk. GToTree/IQ-TREE can provide the
   genome tree; EPA-ng can place a strain that has 16S but no genome. These are different tree
   channels and should be labeled as such.
5. Use the linked tree assay track workflow to adapt and render the selected values. Keep its
   data, methods, mapping and adapter receipt with the PDF, PNG and tip-order TSV; bind the
   supplied tree, R sources, arguments and final artifacts in a separate output inventory.

Maximum inhibition is supported only as the explicit `fraction_set_max` view: one target, time
point, final assay concentration, material type, named fraction set per strain, and a declared
activity threshold. Its selection details retain the winning fraction, measured and active fraction
counts, and summed recorded material amount. It is not the default. It never combines different targets, final doses or material types. Matching rows can span several experiments: the grouping key has no experiment ID, rows are weighted equally, and the tree selector cannot filter by experiment. So `fraction_set_max` picks among pooled material means, not per-experiment maxima. Record experiment and observation counts with the selection receipt. Do not read an equal-experiment mean or a no-pooling guarantee from the plot.

## Still needed

- declarative mapping profiles for each raw plate layout and plate-reader export;
- an in-vivo observation schema with outcome type, unit, subject/time structure, and exclusions;
- categorical assay-track rendering beyond the selected numeric BIOASSAY workflow;
- a reviewed policy for experiment-level versus pooled views and biological versus technical
  replication;
- visual regression fixtures for tree/heatmap alignment, long labels, and legends;
- a source-bound structure panel that consumes the existing NP Atlas/RDKit reference structure
  record without implying that a comparator molecule was produced or assayed.

Known class-member structures, including nucleoside or indolocarbazole examples, can already be
resolved and drawn through the NP Atlas/RDKit path described in
[`NPATLAS_PROVISIONING.md`](NPATLAS_PROVISIONING.md). Figure assembly should label the molecule as a
reference or comparator and preserve its structure identifier, source record, and license.

## Exact selected assay tracks

The portable [tree assay track workflow](TREE_ASSAY_TRACK_RENDERING.md) uses `build_tree_tracks.py`, `render_tree_one_bar_row.R` and `render_tree_bar_groups.R`. It preserves the Figure Factory selection receipts and exact tip IDs; it does not aggregate across assay scopes.

## R output binding and locus-map limits

The R templates consume sidecars directly. `figure_factory_next_ggplot.R` checks required columns, nonempty data, and cohort palette entries; it does not verify the Python receipt hashes, re-admit rows, or certify the numeric fields against the source. Verify the consumed sidecar against its producer receipt first, then record the exact R/theme source hashes, arguments, session/library versions and new output hashes. Use a new output prefix: `sapote_save_pair` calls `ggsave` directly and has no existing-output refusal. R outputs do not inherit the Python artifact hashes or receipt status.

`sapote_locus_map.R` draws gene arrows and two alternating label rows. It reads the exact `panel` subtitle but does not render the v8 comparator/evidence panel, enforce collision-free dense labels, or emit a v8 receipt. Its required visibility field is `label_displayed` (YES); a different legacy visibility schema needs an explicit checked adapter. Treat this as an alternate arrow view, with its content gaps recorded. For review-grade v8 maps use [LOCUS_MAP_V8](LOCUS_MAP_V8.md), retain the rich CSV, and inspect dense labels at the intended size. Do not label an R redraw as v8 parity without content and identity verification.
