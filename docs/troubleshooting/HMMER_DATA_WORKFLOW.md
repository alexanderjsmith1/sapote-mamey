# HMMER evidence and integration limits

HMMER profile matches support domain or protein-family evidence. They do not establish compound identity, activity or production. Keep the query sequences, profile library version/hash, tool version, match coordinates and original output together.

## Inputs and assets

A protein query and a compatible HMM profile library are separate required inputs to an external HMMER search. Do not assume the historical filename `mamey_markers.hmm` identifies an available or validated bundled asset. Check the configured tool and local asset inventory first. antiSMASH annotations and another independently generated profile search are distinct provenance channels; one is not automatically equivalent to the other.

## Current workbook limitation

`mamey/cell_provenance.py` emits `NEEDS_HMMER_DOMTBLOUT` placeholders; it does not import an arbitrary `domtblout` file into those workbook cells. The main extraction CLI has no general `--hmmer-domtblout` import option. Specialized domain tools have their own input contracts and outputs; do not confuse them with this missing-data worklist.

Review independently generated output in a separate workspace and reconcile its sequence IDs and coordinates with source records. Keep the pending worklist state until the exact integration/review step has a receipt. A profile hit is supporting evidence, while an unrun search or missing library remains unavailable evidence.

## Generated package copies

Package `Troubleshooting/HMMER_Data_Workflow.md` is emitted from Python literals in `mamey/cell_provenance.py`, not copied from this guide. Older generated text may mention `mamey_markers.hmm` and “fill workbook evidence cells” without an implemented import contract. This guide clarifies that limitation; correcting the generator requires a separately reviewed code change.
