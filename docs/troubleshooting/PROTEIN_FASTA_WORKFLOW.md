# Protein FASTA and evidence status

Protein searches (BLASTp, HMMER, DIAMOND) need protein sequences. A genome FASTA holds nucleotides, and renaming it does not make it a protein file. Take proteins from the antiSMASH CDS records or another annotation you can trace. Record where they came from and the exact query names, so every hit maps back to its full locus identity.

## What the program reads

The main extraction reads an antiSMASH result ZIP, not a bare FASTA. Annotating the genome and running antiSMASH happen before this program. A protein FASTA adds outside evidence; it does not replace the antiSMASH region records.

`mamey/cell_provenance.py` writes empty "pending" rows for protein, HMMER and DIAMOND evidence in every package. It writes them even when another tool has already produced results. So a `NEEDS_PROTEIN_FASTA` row does not mean the package or archive has no proteins.

## What to do

1. Look for protein exports and CDS translations you already have before asking for new data. Keep their paths and hashes.
2. Read the input rules of the tool you will use, and work in a new review folder.
3. Match outside results to records by exact sequence and full locus identity.
4. Do not mark a pending cell complete just because a file now exists.

To review saved BLASTp results, use [the result-upload SOP](../SOPs/SOP-05_BLASTP_Result_Upload_Parse_Reprioritize.md). The HMMER and DIAMOND limits are in the neighboring guides. Do not claim a result was imported into the workbook unless the tool does that and a receipt shows it.
