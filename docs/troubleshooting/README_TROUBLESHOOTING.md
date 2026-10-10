# Sapote-Mamey Troubleshooting Folder

This folder is part of the standalone product package. Its purpose is to make missing worksheet values transparent instead of silent.

Every major output field should have one of three things:

1. a value derived from native antiSMASH/Mamey evidence;
2. a status code explaining why the value is missing or low-confidence; or
3. a workflow telling the user how to generate the needed evidence.

Historical Release 1 / Release 2 wording describes design stages; it is not a current hosted-service promise. See [the current user task router](../USER_TASK_ROUTER.md) for implemented workflows. The cell-provenance table covers selected fields, not a guaranteed audit of every workbook cell. Generic external-evidence rows are pending placeholders and do not automatically change when a search file exists.

## Key files

- `CELL_STATUS_CODE_GLOSSARY.md` - controlled terms used in provenance and worklist tables.
- `ANTISMASH_INPUT_WORKFLOW.md` - what Mamey can read from antiSMASH outputs.
- `PROTEIN_FASTA_WORKFLOW.md` - how protein FASTA relates to assembled FASTA and antiSMASH/annotation outputs.
- `HMMER_DATA_WORKFLOW.md` - how to generate HMMER `domtblout` evidence.
- `DIAMOND_DATA_WORKFLOW.md` - how to generate scalable BLASTP-like homolog tables.
- `MANUAL_BLASTP_SPOTCHECK_WORKFLOW.md` - when NCBI BLASTP is appropriate.
- `BIGSCAPE_TROUBLESHOOTING.md` - cohort-run setup, reference loading, family labels, and figure problems.

## Rule

The intended rule is no unexplained blanks: retain a status, reason and next action for missing or low-confidence evidence. The present provenance builder does not guarantee coverage of every cell or automatically import arbitrary HMMER/DIAMOND files. Confirm each claimed completed field against its source and integration receipt.

Package `Troubleshooting/` files are generated from `mamey/cell_provenance.py` literals and are separate from these source guides. A Markdown-only correction here does not update the generator or previously sealed packages.

## Single-region accession antiSMASH ZIPs

For one-accession / one-region antiSMASH outputs such as `KY089035.1.zip`, see `SINGLE_REGION_ACCESSION_INPUTS.md`. These are valid raw antiSMASH intake targets after `inspect`, but they are not full genomes or sealed Mamey packages.
