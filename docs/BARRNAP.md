# Find rRNA genes with Barrnap

Find predicted rRNA features in a bacterial genome and save their coordinates
and sequences. You need the genome FASTA plus Barrnap, nhmmer and bedtools available in
your terminal. Barrnap is a [separate installation](https://github.com/tseemann/barrnap).

## Check the installation

```bash
barrnap --version
barrnap --help
```

The recipe below was checked with Barrnap 0.9, whose defaults use the bacterial
model and one thread. For fungal inputs, follow the
[fungal workflow](PHYLO_FUNGAL_WORKFLOW.md).

## Scan the genome

[Recover the submitted genome](COMPANION_FILES.md#recover-a-genome-from-an-antismash-zip)
from your antiSMASH ZIP if needed. This example uses
`../EXAMPLE-genome/EXAMPLE.fasta`; run from the bundle folder.

`--outseq` saves the called sequences as FASTA; the redirected output saves their
GFF coordinates. The output folder must be new: `mkdir` stops the scan if it
already exists. The genome folder must be writable because bedtools can add a
`.fai` index beside the input.

```bash
mkdir ../EXAMPLE-rRNA &&
  barrnap --outseq ../EXAMPLE-rRNA/rRNA.fasta \
    ../EXAMPLE-genome/EXAMPLE.fasta > ../EXAMPLE-rRNA/rRNA.gff
```

## Read the result

Barrnap prints its model, progress and feature count. Open `rRNA.gff` for the
contig, coordinates, strand and rRNA type; `rRNA.fasta` holds the called sequences.
Keep the FASTA headers and save both files with the input hash, tool versions
and model hash.

Check partial predictions in the GFF and log before using them as marker queries.
The FASTA includes all called rRNA types, so select only 16S records for a 16S tree.

`tools/marker_candidate_search.py` prints a separate 16S plan; it leaves sequence
extraction for you to complete. Use the [tree workflow](GTOTREE_WORKFLOW.md) to
choose references and prepare the comparison.
