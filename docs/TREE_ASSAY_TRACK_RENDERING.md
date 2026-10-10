# Selected assay tracks beside an existing tree

`tools/build_tree_tracks.py` adapts one or more **explicitly selected** Figure Factory BIOASSAY tracks. It does not pool assays, calculate a maximum, resolve taxonomy, or infer a tree-tip identifier. The two R renderers draw the resulting selected values against a supplied Newick tree.

First emit `bioassay_tree_track.tsv` using the [Figure Factory selection contract](BIOASSAY_FIGURE_FACTORY.md#tree-and-mode-b-boundary). Every series retains its own target, material, time point, dose, aggregation and named material selection. The factory receipt and track hashes must match. An unresolved growth-control or other upstream admission hold must be resolved in that channel before a track is emitted; drawing a figure cannot clear that hold.

Create an exact metadata TSV with `tip`, `strain`, `label`, `role`. `tip` is the literal Newick tip ID. Query strains must map one-to-one; reference and outgroup roles are explicit and carry no query assay values. Labels are supplied as deposited/reviewed; the renderer does not manufacture species names or type status. All tree tips must appear exactly once in this table.

The adapter config uses `schema: sapote.tree-tracks.v1`, a configurable `input_root`, a SHA-256-bound `metadata` object (`path`, `sha256`), and a `tracks` list. Each entry names a unique output `column`, display `label`, hex `colour`, and a SHA-256-bound Figure Factory `receipt`. `input_root` resolves relative to the config file's parent (or names an absolute root); file locators are relative to that root and cannot escape it. Metadata roles must be exactly `query`, `reference` or `outgroup`. Tips/query strains are literal strings with no whitespace normalization; nonempty labels and unique tips are required, but display labels need not be unique. Formula-leading tip/strain/label text is refused, so do not silently edit an exact identifier to bypass that hold. Track columns must begin with a letter and use letters/digits/underscores, avoid reserved `tip`/`label`/`role`, and be unique; display series labels must also be unique and colours use six-digit hex syntax. See the runnable synthetic configs in `examples/tree_tracks/`.

```bash
python3 tools/build_tree_tracks.py --config examples/tree_tracks/grouped.json --out /path/to/new-track-output
Rscript tools/render_tree_bar_groups.R examples/tree_tracks/tree.newick \
  /path/to/new-track-output/tracks.tsv /path/to/new-track-output/series.tsv \
  /path/to/new-figure "Selected assay tracks" none none
```

The last two optional arguments are a numeric display threshold (or `none`) and a numeric internal-node support threshold (or `none`). Neither has an assay-specific default. A node label is shown only when it is numeric and meets the supplied threshold; the renderer does not determine which support method produced that label.

`render_tree_one_bar_row.R` accepts the same arguments and requires exactly one series. PDF output uses the native Quartz device on macOS and the standard R PDF device elsewhere. Both renderers emit PDF, PNG and an exact tip-order TSV. They preserve the supplied topology and branch lengths; ladderizing only orders the display. They refuse existing figure outputs and mismatched or duplicate tip IDs. Dynamic axes preserve negative values; no value is clipped to a presumed 0–100 range. A recorded zero is marked with a dot; an admitted `NOT_MEASURED` is blank. Reference/outgroup bars are refused. Large trees still require visual review for label legibility.

The adapter records original receipt hashes, the full selection metadata and output hashes in `track_adapter_receipt.json`. Keep this receipt with the figures. Multi-series juxtaposition does not assert that different material or assay scopes are interchangeable. These are strain-level readouts, with no attribution to a biosynthetic locus. A 16S tree remains placement context, not a species-identification claim.

The external bee/wasp prototype inspired the layout. Its personal-path helper and assay-maximizing producers are not shipped; the bundled implementation consumes the existing admitted-track contract instead. The generated `FIGURE_R_MANIFEST.tsv` describes cohort figure schemas and is not a registry for these standalone renderers.

## Adapter publication and recovery

Choose a new output directory outside source evidence and the code bundle; even an existing empty resolved directory is refused. The adapter creates its parent only after input admission, stages `tracks.tsv`, `series.tsv` and `track_adapter_receipt.json` in a unique sibling, then publishes by ordinary directory rename. Caught errors remove the stage, but interruption can leave it and a concurrent empty destination can be replaced on POSIX. Use one output writer, preserve any partial/staged attempt and diagnostics, and choose a fresh destination after resolving the cause. There is no resume option or source/code output-root guard. The CLI returns 0 without printing a success receipt; read the saved receipt and expected three-file roster. Handled refusals print `TREE_TRACK_REFUSED` and return 2; unexpected config shapes can still produce an uncaught traceback.

Keep config, metadata, producer receipts, tracks and caption/selection sidecars stable throughout adaptation. Their hashes are checked before separate parsing reads and are not all rechecked at publication. The adapter receipt records the config hash and relative metadata/producer receipt specs but does not embed the config or record the resolved `input_root`. Retain the selected config path/hash, resolved input root and original pinned sources with the adapter receipt so its relative locators can be resolved after a handoff. Do not reconstruct a moved source root by filename guesses.

## Verification boundary and actual render artifacts

`PASS_EXACT_ADMITTED_VALUES` is the **adapter** status. The adapter has no Newick input. It binds metadata and producer-receipt hashes, rechecks the track/caption artifact hashes, accepts producer states `PASS_DATA_READY_R_NOT_REQUESTED` or `PASS_FIGURE_FACTORY_RENDERED`, and requires exact query-strain rosters and finite observed values or blank `NOT_MEASURED`. It checks required selection keys, not all scientific selector semantics. It does not revalidate every producer artifact, raw assay asset, tree topology or branch-length policy. Final `tracks.tsv` omits the strain column; retain the pinned metadata that owns the strain-to-tip mapping.

Actual Newick tip-set equality is checked later by the shared R renderer. The R code validates duplicate/exact tip membership, roles, series columns and finite track values, but does not certify branch lengths, rooting, taxonomic admission, support-method identity or prior source governance. Standalone blank numeric cells are displayed as unmeasured without consulting a missingness-state column; use the adapter's bound output rather than an unaudited hand-edited TSV.

The R renderer emits a 10-inch-high PDF, a 160-dpi PNG and `<stem>.tip_order.tsv`; width varies with tip/series count (large trees cap at 40 inches). It refuses existing output files by `file.exists`, then writes PDF, checks its existence/nonzero size, writes PNG and finally tip order. These files are sequential, not a transaction. A later failure can leave earlier outputs; do not reuse the same stem after a partial failure. Quarantine that attempt and use an unused stem for recovery.

The adapter receipt hashes adapter TSVs, not its own receipt, Newick, R code, final PDF/PNG or tip-order file. It is emitted before rendering and does not become a rendered-figure receipt afterward. Preserve an external inventory with hashes of the receipt itself, supplied Newick, renderer code, renderer arguments and final artifacts, along with the original metadata/producer receipt. A successful R exit is not visual QA. Check rendered labels and missingness before a figure is adopted.

Source: `tools/build_tree_tracks.py:53–165`; `tools/tree_track_render.R:3–59`; both `tools/render_tree_*` wrappers use that shared implementation.
