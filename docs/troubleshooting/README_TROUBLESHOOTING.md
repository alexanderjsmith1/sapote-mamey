# Sapote-Mamey Troubleshooting Folder

This folder is part of the standalone product package. Its purpose is to make missing worksheet values transparent instead of silent.

Every major output field should have one of three things:

1. a value derived from native antiSMASH/Mamey evidence;
2. a status code explaining why the value is missing or low-confidence; or
3. a workflow telling the user how to generate the needed evidence.

Release 1 is intentionally standalone. It flags missing inputs and tells the user what to provide. Release 2 can automate some of those recovery steps with a server.

## Key files

- `CELL_STATUS_CODE_GLOSSARY.md` - controlled terms used in provenance and worklist tables.
- `ANTISMASH_INPUT_WORKFLOW.md` - what Mamey can read from antiSMASH outputs.
- `PROTEIN_FASTA_WORKFLOW.md` - how protein FASTA relates to assembled FASTA and antiSMASH/annotation outputs.
- `HMMER_DATA_WORKFLOW.md` - how to generate HMMER `domtblout` evidence.
- `DIAMOND_DATA_WORKFLOW.md` - how to generate scalable BLASTP-like homolog tables.
- `MANUAL_BLASTP_SPOTCHECK_WORKFLOW.md` - when NCBI BLASTP is appropriate.

## Rule

No silent blanks. Every empty or low-confidence field should receive a status code, reason, and next action.

## Single-region accession antiSMASH ZIPs

For one-accession / one-region antiSMASH outputs such as `KY089035.1.zip`, see `SINGLE_REGION_ACCESSION_INPUTS.md`. These are valid raw antiSMASH intake targets after `inspect`, but they are not full genomes or sealed Mamey packages.
