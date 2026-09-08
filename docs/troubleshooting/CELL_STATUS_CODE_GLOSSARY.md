> **ADDENDUM (scoped).** Supplements the canonical `docs/GLOSSARY.md`; entries are scope-specific and must not redefine canonical terms.

# Cell Status Code Glossary

| Status code | Meaning | Release handling |
|---|---|---|
| COMPLETE_NATIVE | Filled from Mamey/antiSMASH extraction evidence. | Release 1 complete. |
| COMPLETE_USER_METADATA | Filled from user-supplied metadata. | Release 1 complete; do not infer missing locality or host. |
| COMPLETE_EXTERNAL_EVIDENCE | Filled from a provided HMMER, DIAMOND, BLAST, or other evidence file. | Release 1 complete if file is packaged. |
| COMPLETE_INFERRED_LOW_CONFIDENCE | Filled by conservative inference, but should be reviewed. | Flag for review. |
| NEEDS_ANTISMASH_OUTPUT | The assembled FASTA alone is not enough for this BGC-level value. | User should provide antiSMASH output ZIP/folder. |
| NEEDS_PROTEIN_FASTA | HMMER/DIAMOND cannot run on nucleotide contigs directly. | Generate proteins from antiSMASH GenBank, Prodigal/Bakta/PGAP, or another annotation path. |
| NEEDS_HMMER_DOMTBLOUT | Domain/marker/cassette cell requires HMMER structured output. | Run `hmmscan --domtblout`. |
| NEEDS_DIAMOND_TSV | Homolog or BLASTP-like cell requires scalable local similarity output. | Run DIAMOND and import TSV. |
| MANUAL_BLASTP_OPTIONAL | NCBI BLASTP is useful for a small number of top proteins only. | Optional top-lead spot-check. |
| LOW_CONFIDENCE_REVIEW | Filled, but below threshold or potentially fragmented. | Manual review before claims. |
| UNRESOLVED_METADATA | Metadata not supplied. | Ask user or keep unresolved. |
| NOT_APPLICABLE | Field does not apply to this strain/BGC/class. | No action. |
| DEFER_SERVER_R2 | Standalone package flags the need; server can automate later. | Release 2 automation candidate. |
