# Selected assay tracks beside an existing tree

`tools/build_tree_tracks.py` adapts one or more **explicitly selected** Figure Factory BIOASSAY tracks. It does not pool assays, calculate a maximum, resolve taxonomy, or infer a tree-tip identifier. The two R renderers draw the resulting selected values against a supplied Newick tree.

First emit `bioassay_tree_track.tsv` using the [Figure Factory selection contract](BIOASSAY_FIGURE_FACTORY.md#tree-and-mode-b-boundary). Every series retains its own target, material, time point, dose, aggregation and named material selection. The factory receipt and track hashes must match. An unresolved growth-control or other upstream admission hold must be resolved in that channel before a track is emitted; drawing a figure cannot clear that hold.

Create an exact metadata TSV with `tip`, `strain`, `label`, `role`. `tip` is the literal Newick tip ID. Query strains must map one-to-one; reference and outgroup roles are explicit and carry no query assay values. Labels are supplied as deposited/reviewed; the renderer does not manufacture species names or type status. All tree tips must appear exactly once in this table.

The adapter config uses `schema: sapote.tree-tracks.v1`, a configurable `input_root`, a SHA-256-bound `metadata` object (`path`, `sha256`), and a `tracks` list. Each entry names a unique output `column`, display `label`, hex `colour`, and a SHA-256-bound Figure Factory `receipt`. File locators are relative to `input_root` and cannot escape it. See the runnable synthetic configs in `examples/tree_tracks/`.

```bash
python tools/build_tree_tracks.py --config examples/tree_tracks/grouped.json --out /path/to/new-track-output
Rscript tools/render_tree_bar_groups.R examples/tree_tracks/tree.newick \
  /path/to/new-track-output/tracks.tsv /path/to/new-track-output/series.tsv \
  /path/to/new-figure "Selected assay tracks" none none
```

The last two optional arguments are a numeric display threshold (or `none`) and a numeric internal-node support threshold (or `none`). Neither has an assay-specific default. A node label is shown only when it is numeric and meets the supplied threshold; the renderer does not determine which support method produced that label.

`render_tree_one_bar_row.R` accepts the same arguments and requires exactly one series. PDF output uses the native Quartz device on macOS and the standard R PDF device elsewhere. Both renderers emit PDF, PNG and an exact tip-order TSV. They preserve the supplied topology and branch lengths; ladderizing only orders the display. They refuse existing figure outputs and mismatched or duplicate tip IDs. Dynamic axes preserve negative values; no value is clipped to a presumed 0–100 range. A recorded zero is marked with a dot; an admitted `NOT_MEASURED` is blank. Reference/outgroup bars are refused. Large trees still require visual review for label legibility.

The adapter records original receipt hashes, the full selection metadata and output hashes in `track_adapter_receipt.json`. Keep this receipt with the figures. Multi-series juxtaposition does not assert that different material or assay scopes are interchangeable. These are strain-level readouts, with no attribution to a biosynthetic locus. A 16S tree remains placement context, not a species-identification claim.

The external bee/wasp prototype inspired the layout. Its personal-path helper and assay-maximizing producers are not shipped; the bundled implementation consumes the existing admitted-track contract instead. The generated `FIGURE_R_MANIFEST.tsv` describes cohort figure schemas and is not a registry for these standalone renderers.
