# Synthetic exact-tip track example

All observations, query/reference names and tree distances are synthetic fixtures. They represent no experimental finding, taxonomic assignment or activity claim. The supplied 48-hour and 72-hour selections are distinct; do not pool them or transfer their scopes into production evidence.

The adapter configs `single.json` and `grouped.json` pin `metadata.tsv` and the supplied Figure Factory receipt bytes. The factory configs `factory_48.json` and `factory_72.json` use `observations.csv`, fixed synthetic selection rosters and `render_with_r: false`. A data-ready factory receipt is not a rendered-figure receipt. See [the tree-track guide](../../docs/TREE_ASSAY_TRACK_RENDERING.md) for adapter versus R validation and output scopes.

## Minimal reproduction preparation

Use the existing fixture files in place as read-only sources; do not copy the entire example or bundle. Create a new external work/output directory and copy only the JSON config files that must change. Record the reason, expected small size and source path/SHA-256 before copying. In copied adapter configs set `input_root` to the original fixture directory when using the supplied receipts; config-relative `.` otherwise points to the copied directory and will not find those inputs. Give the adapter a new external output directory.

If independently rebuilding fixture outputs is authorized, create a separate external input/output arrangement with only the required config edits and small input files or verified references, using unused factory output paths. The factory's root/path rules differ from the adapter's config-relative `input_root`: resolve the [Figure Factory contract](../../docs/BIOASSAY_FIGURE_FACTORY.md) before invoking it. Keep original fixture observations and receipts unchanged. Update receipt paths and hashes in copied adapter configs only after the newly produced bytes are inventoried and verified. Do not delete existing factory directories to make a run succeed, or overwrite an authoritative experimental receipt.

Adapter preparation and R rendering are separate steps. The adapter does not read `tree.newick`; the R renderer later requires an exact tip set. Positive, recorded zero, negative and unmeasured fixture values remain distinct, and reference/outgroup roles receive no query assay values. Retain metadata, adapter receipt and a final artifact/hash inventory. Synthetic display success is not assay, phylogeny or scientific approval; this documentation audit did not execute or render the example.
