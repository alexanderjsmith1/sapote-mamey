# Cell status codes

Scope: cell-provenance status vocabulary from `mamey/cell_provenance.py`. For general terms see
the [canonical glossary](../GLOSSARY.md). A completed cell is not a completed analysis or a
scientifically accepted interpretation. The exact code set is checked by the glossary-sync test.

The historical Release 1 / Release 2 labels in older outputs are workflow labels, not promises
about the current bundle release or an available hosted service.

| Status code | Meaning | Next action |
|---|---|---|
| COMPLETE_NATIVE | Filled from Mamey/antiSMASH extraction evidence. | Retain source provenance. |
| COMPLETE_USER_METADATA | Filled from user-supplied metadata. | Retain user-supplied provenance; leave missing locality or host unresolved. |
| COMPLETE_EXTERNAL_EVIDENCE | Filled from a provided HMMER, DIAMOND, BLAST, or other evidence file. | Retain the supplied evidence and its source receipt. |
| COMPLETE_INFERRED_LOW_CONFIDENCE | Filled by conservative inference, but should be reviewed. | Flag for review. |
| NEEDS_ANTISMASH_OUTPUT | The assembled FASTA alone is not enough for this BGC-level value. | User should provide antiSMASH output ZIP/folder. |
| NEEDS_PROTEIN_FASTA | HMMER/DIAMOND cannot run on nucleotide contigs directly. | Generate proteins from antiSMASH GenBank, Prodigal/Bakta/PGAP, or another annotation path. |
| NEEDS_HMMER_DOMTBLOUT | Domain/marker/cassette cell requires HMMER structured output. | Run `hmmscan --domtblout`. |
| NEEDS_DIAMOND_TSV | Homolog or BLASTP-like cell requires scalable local similarity output. | Run DIAMOND and import TSV. |
| MANUAL_BLASTP_OPTIONAL | NCBI BLASTP is useful for a small number of top proteins only. | Optional top-lead spot-check. |
| LOW_CONFIDENCE_REVIEW | Filled, but below threshold or potentially fragmented. | Manual review before claims. |
| UNRESOLVED_METADATA | Metadata not supplied. | Ask user or keep unresolved. |
| NOT_APPLICABLE | Field does not apply to this strain/BGC/class. | No action. |
| DEFER_SERVER_R2 | Standalone package flags the need; server can automate later. | Keep deferred until an implemented, configured workflow is available. |
