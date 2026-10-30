# Make several views of an existing tree

Tree Catalog plans and renders display variants of a completed 16S placement
run. You need that run, query metadata, reference metadata and a verified
tree/sequence roster. It reuses the selected tree.
For an externally prepared tree, use [prepared display series](#prepared-display-series).

## Choose the output views

Select reference quotas such as 1:1, 1:2 and 1:3, then choose concise,
detailed-source, no-geography or internal views. Quotas apply before shared
reference deduplication, so they do not guarantee that many unique references
per query. A five-level series can use 1, 2, 3, 4 and `all`.

The no-geography view still requires resolved geography; it hides the strip.
Internal views can show recorded experiment/sample identifiers. Keep both
identifiers when reviewing sampling units; similar sequences alone cannot
justify merging isolates.

## Plan a catalog

Start from the [catalog example](../examples/tree_catalog.example.json), replacing
its paths and scopes with your completed run. Save it as `inputs/EXAMPLE-catalog.json`.
Relative paths resolve from that file. The example supports planning; it lacks
the complete render declarations described below.

```bash
python tools/tree_catalog.py plan inputs/EXAMPLE-catalog.json \
  --out reviews/EXAMPLE-tree-plan.json
```

The declared run and metadata paths must exist. Choose a fresh output file:
planning can replace an existing one. Check job count, query scope, reference
policy and paths. Three ratios times three views propose nine displays.

Each entry needs its run directory, group, cohort/taxonomic scope, reference-panel
choice and metadata sources. Optional required-reference species must already
belong to the backbone and count within each query's quota.

For a spotlight, prepare a separate reviewed query-subset run. The renderer
refuses any nonempty `spotlight_queries` field, even if the named run is already
subsetted; use that run's actual roster with the field empty or omitted.

## Required series contract and verified completion

Before rendering, add `series_requirements` with nonempty lists of
`taxonomic_scopes`, `reference_panels`, `reference_ratios` and `views`.
Their Cartesian product defines the requested series; missing, duplicate or extra
variants fail preflight.

Each entry also needs `reference_manifest`: a roster `path`/`sha256` plus `tree`
and `sequences` objects, each with relative `path`/`sha256`. The TSV roster has
`tip`, `role`, `type_status`, `accession`, `sequence_sha256`, `evidence` and
`admission`. Roles are query/reference/outgroup; admitted records use `admitted`.
Sequence hashes use uppercase ungapped strings. Tree, FASTA and roster must
have exactly the same unique tip identities.

Choose the panel that matches those records:

- `type_only`: all ingroup references have affirmative type status.
- `type_plus_selected_non_type`: both verified type and non-type references.
- `type_plus_selected_additional`: provisional context may include unverified status.

Compact views can contain fewer reference classes; receipts record actual counts.
Reconcile the manifest with the placement run and metadata consumed by the child
commands, because those are checked separately.

## Render after the inputs pass review

```bash
python tools/tree_catalog.py render inputs/EXAMPLE-catalog.json \
  --outdir reviews/EXAMPLE-tree-series
```

Rendering refuses an existing directory. `placement_display.py` supplies Newick
and metadata to `tools/ggtree_rect_heatmap.R`. Each child output includes tree,
metadata, reference-selection records, methods, PNG/PDF and receipts.
The catalog stops at the first failed job.

Completion checks nonempty outputs, tree/metadata tip joins, all query/outgroup
tips, full roster for `all`, and agreement with the pruned parent tree's unrooted
split lengths. The 0.0001 substitutions/site tolerance accommodates legacy
decimal serialization. Inspect the rendered pages and upstream evidence as well.

## Prepared display series

For an existing externally inferred tree with prepared display inputs, use:

```bash
python tools/render_tree_reference_series.py --config inputs/EXAMPLE-series.json \
  --outdir reviews/EXAMPLE-prepared-series
```

This config uses the same series and reference-manifest requirements, plus
`display_jobs`. Each job supplies `job_id`, `tree_id`, taxonomic scope, reference
panel/ratio, view, relative `input_dir`, and hashes for exactly `tree.newick`,
`metadata.tsv`, `provenance.tsv`, `palette.tsv`, `settings.tsv` and `caption.txt`.
Use unique job IDs, contiguous `series_index` values starting at 1 and descriptive
unique `output_stem` values. Review resolved job/group paths; dot-only components
can pass the character check.

Metadata includes tip/role/type status, taxon and concise/experiment labels,
raw and categorized source/geography, assay states/provenance and experiment/sample
IDs. Query assay states are positive, negative, not_tested or missing; reference
and outgroup assay/experiment fields are blank. Keep the exact schema in
[`tree_series_contract.py`](../tools/tree_series_contract.py) when preparing these files.

Provenance rows bind each field's raw value, source, hash and status. Palette rows
use field/value/color; each category keeps one color across the series, and two
categories within a field cannot share a color. Every displayed tip needs resolved
source and geography, even in no-geography views. Hold a panel with missing query
metadata; do not remove queries or invent values to pass.

Settings record the view, title, layout, tree fraction, outgroup and inference/model/
support/rooting details. The layout is `full_genus_single_line_v1`; tree fraction
is at least 0.39 and below 1. Reconcile `outgroup_tip` with roster roles and the
rooting decision, since the renderer reroots from that setting.

Prepared rendering freezes its R/geometry/palette inputs and binds output hashes.
Keep `tree_annotation_geometry.R` and the full bundle dependencies when exporting
the workflow. Query text uses `GG_FOCAL_COLOUR`, default black; record the actual
display setting. Inspect all requested variants before treating the series as done.

<a id="what-this-tool-does"></a>
<a id="recommended-project-matrix"></a>
