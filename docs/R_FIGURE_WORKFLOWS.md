# R figure workflows

Sapote-Mamey uses R as a renderer for already admitted data. Python producers perform joins,
validation, aggregation, provenance binding, and typed missingness first; the R scripts should not
recover those decisions from filenames or reshape raw assay exports by guesswork.

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
| `ggtree_placement_hostcolour.R` | Placement annotations with query host | Host-coloured placement view |
| `ggtree_placement_bioassay.R` | Legacy Candida/MRSA activity fields | Narrow binary placement overlay retained for compatibility |
| `sapote_matrix_figure.R` | Registered wide matrix sidecars | Cohort heatmaps and bubble figures |
| `sapote_tidy_figure.R` | Registered tidy sidecars | Ordinations, ranked bars, and rosters |
| `sapote_strain_figure.R` | Per-strain figure sidecars | Per-strain bars, heatmaps, and scatterplots |
| `sapote_locus_map.R` | Exact-locus gene sidecar | BGC gene-arrow maps |
| `figure_factory_next_ggplot.R` | Factory plotted-data sidecar | Alternate rendering of already computed coverage values |

`sapote_figure_theme.R` is shared style policy rather than a standalone renderer. The generic
bioassay Figure Factory now supplies the broader assay path; the legacy binary placement script
must not be applied to other targets, fraction types, or time points.
`tools/FIGURE_R_MANIFEST.tsv` is generated from the Python figure sources and maps figure IDs to
compatible R renderers. The R scripts themselves remain reviewable source files in the bundle.

## Bioassay to tree workflow

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
   channels and should be labelled as such.
5. Render the selected quantitative track with the Figure Factory tree consumer. Keep its data,
   methods, mapping, and receipt sidecars with the SVG/PNG.

Maximum inhibition is supported only as the explicit `fraction_set_max` view: one target, time
point, final assay concentration, material type, named fraction set per strain, and a declared
activity threshold. Its selection details retain the winning fraction, measured and active fraction
counts, and summed recorded material amount. It is not the default and it does not mix experiments,
targets, doses, or material types. An average is valid only within the exact grouping stated in the
summary and selection receipt.

## Still needed

- declarative mapping profiles for each raw plate layout and plate-reader export;
- an in-vivo observation schema with outcome type, unit, subject/time structure, and exclusions;
- a generalized ggtree renderer for multiple selected quantitative and categorical assay tracks;
- a reviewed policy for experiment-level versus pooled views and biological versus technical
  replication;
- visual regression fixtures for tree/heatmap alignment, long labels, and legends;
- a source-bound structure panel that consumes the existing NP Atlas/RDKit reference structure
  record without implying that a comparator molecule was produced or assayed.

Known class-member structures, including nucleoside or indolocarbazole examples, can already be
resolved and drawn through the NP Atlas/RDKit path described in
[`NPATLAS_PROVISIONING.md`](NPATLAS_PROVISIONING.md). Figure assembly should label the molecule as a
reference or comparator and preserve its structure identifier, source record, and license.
