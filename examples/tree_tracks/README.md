# Synthetic exact-tip track example

All observations, query/reference names and tree distances here are synthetic test fixtures.
No experimental finding, taxonomic assignment or activity claim is represented.

From the bundle root, run the adapter with `single.json` or `grouped.json` as described in
`docs/TREE_ASSAY_TRACK_RENDERING.md`. Output must be a new external directory.

The two `factory_*.json` configs reproduce the supplied factory data from `observations.csv`.
For reproduction, copy this example to a disposable directory, remove the copied factory output
directories, run from that disposable directory with `external_data_root` set to `.`, and invoke
the bundle's Figure Factory on each config. Refresh the receipt hashes in adapter configs if
regeneration changes any receipt bytes. Never overwrite an authoritative experimental receipt.

The fixture covers positive, zero, negative and unmeasured values, plus explicit reference and
outgroup labels. Every series is separately selected; no cross-platform maximum is calculated.
