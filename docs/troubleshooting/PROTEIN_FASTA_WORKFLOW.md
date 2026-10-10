# Protein FASTA and evidence status

Genome FASTA contains nucleotide sequence. Protein searches need translated protein sequences from a bound annotation or antiSMASH CDS record; a renamed nucleotide FASTA is not a protein input. Record the sequence source and exact query identifiers so downstream hits can be mapped back to the complete locus identity.

## Supported interpretation

The primary extraction workflow consumes an antiSMASH ZIP, not an assembled FASTA alone. Genome annotation and antiSMASH generation are separate prerequisites. A protein FASTA is useful external evidence input; it does not replace the antiSMASH region records.

The current `mamey/cell_provenance.py` emits generic pending protein, HMMER and DIAMOND rows with empty values. Those rows are workflow placeholders, including when another tool has produced external evidence. A `NEEDS_PROTEIN_FASTA` row alone does not establish that no proteins exist anywhere in the package or source archive.

## Recovery

Inventory existing protein exports and bound CDS translations before requesting new data. Preserve their source paths and hashes. Read the intended search or comparison tool's actual input contract and use a new review workspace. Reconcile external results by exact sequence and locus identity; do not change pending cells to completed solely because a file was supplied.

For saved BLASTP result review use [the result-upload SOP](../SOPs/SOP-05_BLASTP_Result_Upload_Parse_Reprioritize.md). HMMER and DIAMOND integration limits are in their neighboring workflow guides. Do not claim automatic workbook import unless the selected tool provides it and a receipt confirms the update.
