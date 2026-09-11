# Protein FASTA Workflow

Assembled genome FASTA files contain nucleotide contigs/scaffolds. HMMER and DIAMOND protein searches require protein sequences.

## Accepted protein sources

1. antiSMASH GenBank/CDS translations;
2. antiSMASH protein FASTA export;
3. local gene calling or annotation such as Prodigal/Bakta/PGAP-style workflows;
4. user-provided `.faa` file.

## Status handling

If only assembled FASTA is present:

- genome-level intake can proceed;
- BGC-level antiSMASH parsing requires antiSMASH output;
- HMMER/DIAMOND evidence cells become `NEEDS_PROTEIN_FASTA` unless proteins are supplied or extracted.
