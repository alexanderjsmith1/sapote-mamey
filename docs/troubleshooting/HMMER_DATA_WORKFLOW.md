# HMMER evidence and integration limits

An HMMER profile match is evidence for a domain or protein family. It does not show which compound is made, whether it is made, or whether it is active. Keep together the query sequences, the profile library's version and hash, the HMMER version, the match coordinates and the raw output.

## Inputs

An HMMER search needs two separate inputs: protein queries and an HMM profile library. Do not assume the old file name `mamey_markers.hmm` points to a real, validated bundled file. Check your tool setup and the local asset inventory first.

antiSMASH's own domain calls and a separate profile search are different evidence sources. Do not treat one as a copy of the other.

## What the workbook does not do

`mamey/cell_provenance.py` writes `NEEDS_HMMER_DOMTBLOUT` placeholders. It does not import a `domtblout` file into those cells, and the main command line has no `--hmmer-domtblout` option. The specialist domain tools have their own inputs and outputs; they are not this worklist.

Review HMMER output in a separate folder, and match its sequence IDs and coordinates to the source records. Keep the pending state until a recorded review step fills it. A profile hit is supporting evidence. A search that never ran, or a missing library, is missing evidence, not a negative.

## Copies inside packages

The package file `Troubleshooting/HMMER_Data_Workflow.md` is written from text inside `mamey/cell_provenance.py`, not copied from this page. Current packages state the same limit. Older packages may mention `mamey_markers.hmm` or "fill workbook evidence cells". Keep those files as they are, as a record, but do not read that wording as a working import.
