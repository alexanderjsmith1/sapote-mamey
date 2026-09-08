# antiSMASH Input Workflow

The best standalone input is the antiSMASH ZIP/folder generated from the assembled genome FASTA.

## Minimum input

- assembled genome FASTA: allows genome-level intake and can be handed to antiSMASH, but does not by itself provide BGC region GenBank files.

## Preferred input

- antiSMASH ZIP/folder with `region*.gbk`, JSON or TXT evidence files, knownclusterblast/clusterblast outputs, and the index/report files.

## Best input

- antiSMASH ZIP/folder;
- extracted or predicted protein FASTA;
- optional HMMER `domtblout`;
- optional DIAMOND TSV.

Mamey should flag missing evidence explicitly instead of silently leaving workbook cells blank.
