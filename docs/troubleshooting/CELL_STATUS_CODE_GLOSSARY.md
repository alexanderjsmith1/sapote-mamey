# Cell status codes

A cell is one value in the workbook. The cell-provenance CSV gives a status code, saying where the value came from, for a selected set of fields: the intake fields, the BGC inventory and triage summary, per-BGC product and boundary fields, and the external-evidence placeholders. It does not list every workbook coordinate. A field with no row was not evaluated by this table; that is not a complete or a negative state. The missing-data worklist CSV is the subset of those rows that need action. The codes appear in the `status_code` column of both files. The codes are defined in `mamey/cell_provenance.py`. For general terms see the [canonical glossary](../GLOSSARY.md). A completed cell is not a completed analysis. It is not an
accepted scientific interpretation either.

The `release_handling` column uses the labels Release 1 and Release 2. `R2` means a future server feature. Ignore it.

| Status code | Meaning | Next action |
|---|---|---|
| COMPLETE_NATIVE | Filled from Mamey/antiSMASH extraction evidence. | Keep the source provenance. |
| COMPLETE_USER_METADATA | Filled from metadata given to the run. For `strain_id` that can be the `--strain` argument, the organism name read from the archive, or the ZIP filename; the row does not record which. Not verified against a source record. | Keep the provenance. Bind a filename-derived strain ID to its source record before citing it. Leave missing locality or host unresolved. |
| COMPLETE_EXTERNAL_EVIDENCE | Filled from a provided HMMER, DIAMOND, BLAST or other evidence file. | Keep the supplied evidence and its source receipt. |
| COMPLETE_INFERRED_LOW_CONFIDENCE | Filled by cautious inference. Needs review. | Open the cell's source column and confirm the value by hand. |
| NEEDS_ANTISMASH_OUTPUT | The assembled FASTA alone is not enough for this BGC-level value. | Provide the antiSMASH output ZIP or folder. |
| NEEDS_PROTEIN_FASTA | HMMER and DIAMOND cannot run on nucleotide contigs directly. | Make proteins from the antiSMASH GenBank, Prodigal, Bakta, PGAP or another annotation route. |
| NEEDS_HMMER_DOMTBLOUT | Placeholder for domain, marker or cassette evidence. It does not check whether a search finished. | Review HMMER output tied to its source files separately. There is no general workbook importer for an arbitrary domtblout file. Keep the cell pending until the chosen integration or review step has a receipt. |
| NEEDS_DIAMOND_TSV | Placeholder for homolog evidence. Supplying a TSV alone does not fill the cell. | Review DIAMOND results under the input rules of the tool that will use them. There is no general workbook TSV importer. Keep the integration receipt before you mark the cell complete. |
| MANUAL_BLASTP_OPTIONAL | NCBI BLASTP is useful for a small number of top proteins only. | Optional spot-check of top leads. |
| LOW_CONFIDENCE_REVIEW | Filled, but below threshold or possibly fragmented. | Review by hand before any claim. |
| UNRESOLVED_METADATA | Metadata not supplied. | Ask the user, or keep it unresolved. |
| NOT_APPLICABLE | The field does not apply to this strain, BGC or class. | No action. |
| DEFER_SERVER_R2 | The standalone package flags the need. A server could automate it later. | Keep it deferred until a workflow for it exists and is configured. |
