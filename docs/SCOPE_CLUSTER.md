# Scope an antiSMASH region using annotated boundaries

`tools/scope_cluster.py` creates a candidate subregion from antiSMASH annotations. The selected span is an annotation-derived scope, not a proven true biosynthetic boundary or gene-to-product assignment.

## Prerequisites and output selection

This writer requires Biopython in the selected Python environment. Although the source falls back to the bundled read shim when `Bio` cannot be imported, that shim supplies neither record slicing nor `SeqIO.write`; it cannot complete this command. Install the add-ons with `bundle_support/install_sapote_addons.sh` (see [prerequisites](PREREQUISITES.md)) before an authorized build. A shim-related exception is an unavailable writer, not an empty or accepted scoped result.

Select a fresh explicit `--outdir` outside the code bundle and source evidence. The default `scope_out` is relative to the process working directory, and this tool has no code-bundle output-root guard. Preserve the input and any earlier derived outputs. A portable command shape is:

```bash
python tools/scope_cluster.py --gbk /absolute/inputs/region.gbk \
  --category CATEGORY --label candidate \
  --outdir /absolute/derived/new_scope
```

Replace `CATEGORY` with an annotation category from the region file, for example `nucleoside`. The tool matches it against the `/category` qualifier of the `protocluster` and `cand_cluster` features (or `/product` when `/category` is absent). If nothing matches, the error lists the categories that are available. Add `--core` only when the narrower core span is intended. A successful run prints no error and writes the two files named under Output identity.

## Selection contract

The CLI reads the **first** GenBank record from `--gbk`, selects `--category`, and writes under `--outdir` with `--label` (default `cluster`). `--core` requests a parseable protocluster `core_location` span. The selector reads `protocluster` and `cand_cluster` features; it does not independently interpret standalone `proto_core` features. Category matching is case-insensitive substring matching against the first category/product qualifier value. Inspect all matching candidates, especially multi-category annotations. Require a nonblank selected category and a single intended GenBank record before running: the parser does not reject an empty category, and later GenBank records are ignored. Equal-width matching candidates are not refused as ambiguous; `min` selects the first in the source feature order. The sidecar's `chosen` and `all_protoclusters` fields identify the actual choice for review.

Without `--core`, the narrowest matching candidate-cluster extent is preferred over a protocluster. A merged candidate can still span multiple neighboring protoclusters. With `--core`, the narrowest matching parseable protocluster core is selected; absence of such a core raises an error rather than silently widening. Resolve that hold with the owner; dropping the flag changes the scope and requires a new recorded rationale. Core parsing extracts the first `[start:end]` integer span; it does not reconstruct a compound core location or validate `0 <= start < end <= record length`, containment in the selected protocluster, or a consistent coordinate frame. The JSON boundary stays in the original record's zero-based half-open coordinate system; the sliced GBK has coordinates relative to that subrecord. Confirm the selected span against the authoritative annotation before using it. A malformed, compound, reversed or out-of-record span remains a hold even if the tool produces files.

The JSON inventory counts translated CDS whose **midpoints** lie in the selected interval, and flags midpoint overlap with the first other-category core found. It does not demonstrate exclusive pathway membership. `excluded` means outside the selected midpoint interval, not proof that a gene belongs to a neighboring pathway. The JSON says so in `kept_basis` and `excluded_basis`, and the printed summary uses the same position-only wording. The tool's help and module description call the span an annotation-derived candidate span, as this page does.

## Output identity and consistency

Outputs are `LABEL_CATEGORY_scoped.gbk` and `LABEL_CATEGORY_scope.json`. The GBK is built by slicing the original record; the `kept` feature list is not explicitly installed into the output record. A translated CDS crossing a boundary may be counted by its midpoint but omitted by record slicing, while other contained features may remain. The JSON therefore also lists `kept` (midpoint inventory), `exported_cds` and `n_exported_cds` (the translated CDS in the written slice), and the differences `kept_not_exported` and `exported_not_kept`. `export_inventory_state` is `MATCHES_MIDPOINT_INVENTORY` when the two agree and `HOLD_EXPORT_DIFFERS_FROM_MIDPOINT_INVENTORY` otherwise; a hold also prints a `HOLD:` line. Resolve a hold before using the slice for comparison. Do not treat `n_kept` as the exported inventory count.

The new record ID is truncated to 16 characters and is not a complete locus identity. Keep the source strain, full contig/node, region, BGC alias, source path/hash, selected annotation, original coordinates and output hashes in an accompanying candidate receipt. The JSON alone does not bind input/output hashes or the full identity.

Output-label containment checks reject unsafe paths and escaping symlinks; they are not a no-clobber policy. Existing safe destinations can be overwritten, and GBK/JSON publication is sequential rather than atomic as a pair. Use a fresh candidate destination. Zero exit records production, not biological acceptance; after interruption, retain and inspect partial outputs before recovery.

See [cluster comparison](CLUSTER_RELATE.md) for its separate inventory contract.
