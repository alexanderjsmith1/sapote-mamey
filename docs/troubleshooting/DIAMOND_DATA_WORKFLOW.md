# DIAMOND evidence and integration limits

DIAMOND reports protein sequence alignments against a selected reference set. Record the query source, reference roster/hash, search settings and raw output; database choice changes the comparison scope. Similarity is not product identity or measured activity.

## Available implementation

The optional `mamey/diamond_align.py` alignment helper accepts query and reference protein FASTAs. Its `align_fasta` path can use a working `diamond4py` binding or a `diamond` executable on PATH and returns explicit availability/input failure reasons. This is an alignment helper, not a general workbook TSV importer. Consult the caller's user guide before choosing a workflow.

The helper's structured alignment fields include query and subject identifiers, percent identity, aligned length, mismatch/gap counts, coordinates, e-value, bitscore and query/subject coverage. A manually generated seven-column TSV is not automatically interchangeable with that contract.

## Current workbook limitation

`mamey/cell_provenance.py` unconditionally emits generic `NEEDS_DIAMOND_TSV` placeholders and per-locus empty homolog fields. Supplying a TSV does not automatically fill these cells. The main extraction CLI has no general `--diamond-tsv` importer. Preserve independent results and reconcile identifiers in a review workspace; do not mark a field completed without evidence of the selected integration step.

Do not treat historical “Release 1 / Release 2” wording as a promise that a universal reference FASTA, hosted service or automatic importer exists. Inspect configured local assets and the chosen tool contract. Package `Troubleshooting/DIAMOND_Data_Workflow.md` is generated separately from Python literals; older copies can imply an import path absent from the current worklist implementation.
