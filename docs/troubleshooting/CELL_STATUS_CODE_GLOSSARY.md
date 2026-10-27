# Cell status codes

Scope: the cell-provenance status codes defined in `mamey/cell_provenance.py`. For general terms see
the [canonical glossary](../GLOSSARY.md). A completed cell is not a completed analysis. It is not an
accepted scientific interpretation either. The glossary-sync test checks that this table lists exactly the codes in the code.

The cell-provenance table's `release_handling` column uses the labels Release 1 and Release 2. These are
workflow labels. They make no promise about the current bundle release or about a hosted service.

| Status code | Meaning | Next action |
|---|---|---|
| COMPLETE_NATIVE | Filled from Mamey/antiSMASH extraction evidence. | Keep the source provenance. |
| COMPLETE_USER_METADATA | Filled from user-supplied metadata. | Keep the user-supplied provenance. Leave missing locality or host unresolved. |
| COMPLETE_EXTERNAL_EVIDENCE | Filled from a provided HMMER, DIAMOND, BLAST or other evidence file. | Keep the supplied evidence and its source receipt. |
| COMPLETE_INFERRED_LOW_CONFIDENCE | Filled by cautious inference. Needs review. | Flag for review. |
| NEEDS_ANTISMASH_OUTPUT | The assembled FASTA alone is not enough for this BGC-level value. | Provide the antiSMASH output ZIP or folder. |
| NEEDS_PROTEIN_FASTA | HMMER and DIAMOND cannot run on nucleotide contigs directly. | Make proteins from the antiSMASH GenBank, Prodigal, Bakta, PGAP or another annotation route. |
| NEEDS_HMMER_DOMTBLOUT | Placeholder for domain, marker or cassette evidence. It does not check whether a search finished. | Review HMMER output tied to its source files separately. The generic worklist cannot import an arbitrary domtblout file. Keep the cell pending until the chosen integration or review step has a receipt. |
| NEEDS_DIAMOND_TSV | Placeholder for homolog evidence. Supplying a TSV alone does not fill the cell. | Review DIAMOND results under the input rules of the tool that will use them. There is no general workbook TSV importer. Keep the integration receipt before you mark the cell complete. |
| MANUAL_BLASTP_OPTIONAL | NCBI BLASTP is useful for a small number of top proteins only. | Optional spot-check of top leads. |
| LOW_CONFIDENCE_REVIEW | Filled, but below threshold or possibly fragmented. | Review by hand before any claim. |
| UNRESOLVED_METADATA | Metadata not supplied. | Ask the user, or keep it unresolved. |
| NOT_APPLICABLE | The field does not apply to this strain, BGC or class. | No action. |
| DEFER_SERVER_R2 | The standalone package flags the need. A server could automate it later. | Keep it deferred until a workflow for it exists and is configured. |
