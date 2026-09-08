# DIAMOND Data Workflow

> **Release 1 limitation:** `reference_proteins.faa` (the MIBiG/Mamey reference protein set) and the prebuilt `mamey_ref` DIAMOND database are not included in this release. These are Release 2 deliverables. To use DIAMOND in Release 1, supply your own reference protein FASTA (e.g., download MIBiG proteins from mibig.secondarymetabolites.org) and build a database with `diamond makedb`. Until the reference set is bundled, DIAMOND-dependent cells receive `NEEDS_DIAMOND_TSV` status.

DIAMOND is the preferred standalone path for large BLASTP-like protein homolog searches. Use it when users have thousands of antiSMASH or genome proteins.

## Example commands

```bash
diamond makedb --in reference_proteins.faa -d mamey_ref

diamond blastp \
  -d mamey_ref \
  -q STRAIN_proteins.faa \
  -o STRAIN_diamond_hits.tsv \
  --outfmt 6 qseqid sseqid pident length evalue bitscore stitle \
  --max-target-seqs 5 \
  --threads 8
```

## Cells this fills

- best homolog;
- percent identity;
- e-value;
- bitscore;
- homolog description;
- known enzyme or product-family support.

## Release 1 rule

DIAMOND is optional evidence. Missing DIAMOND data should be flagged as `NEEDS_DIAMOND_TSV`, not guessed.
