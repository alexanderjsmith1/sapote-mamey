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
model and one thread. For a fungal genome, run `barrnap --help` and choose the eukaryote model it lists with `--kingdom` (0.9 lists `euk`).
See the [fungal workflow](PHYLO_FUNGAL_WORKFLOW.md) for the rest of that route.

## Scan the genome

[Recover the submitted genome](COMPANION_FILES.md#recover-a-genome-from-an-antismash-zip)
from your antiSMASH ZIP if needed. In the commands below, replace
`../EXAMPLE-genome/EXAMPLE.fasta` with the path to your genome FASTA; run from the bundle folder.

`--outseq` saves the called sequences as FASTA; the redirected output saves their
GFF coordinates. The output folder must be new: `mkdir` stops the scan if it
already exists. The genome folder must be writable because bedtools can add a
`.fai` index beside the input.

```bash
mkdir ../EXAMPLE-rRNA &&
  barrnap --outseq ../EXAMPLE-rRNA/rRNA.fasta \
    ../EXAMPLE-genome/EXAMPLE.fasta > ../EXAMPLE-rRNA/rRNA.gff \
    2> ../EXAMPLE-rRNA/barrnap.log
echo "barrnap exit: $?"
```

## Read the result

First read the exit status the last line prints, and `barrnap.log`. The shell creates `rRNA.gff`
before Barrnap starts, so the file exists even when Barrnap failed:

- exit not 0: the scan failed. An empty or short `rRNA.gff` is what was left behind, not a result.
  Keep the folder and its log, fix the cause, and scan again into a new folder;
- exit 0 and `rRNA.gff` has only the `##gff-version 3` header: the scan finished and called no
  features. Check the input FASTA and that you chose the right model;
- exit 0 with feature lines: read them.

For a bacterial genome with the default model, a usable scan has at least one 16S line
(`16S_rRNA`) in `rRNA.gff`. With the eukaryote model, look for `18S_rRNA` and `28S_rRNA` lines
instead; the [fungal workflow](PHYLO_FUNGAL_WORKFLOW.md) uses those markers. Open `rRNA.gff` for the
contig, coordinates, strand and rRNA type; `rRNA.fasta` holds the called sequences.
Keep the FASTA headers and save both files with the input hash and the Barrnap version
(for example, `shasum -a 256 EXAMPLE.fasta`).

Check partial predictions in the GFF and log before using them as marker queries.
The FASTA includes all called rRNA types, so select only 16S records for a 16S tree.

`tools/marker_candidate_search.py` prints a separate 16S plan; it leaves sequence
extraction for you to complete. Use the [tree workflow](GTOTREE_WORKFLOW.md) to
choose references and prepare the comparison.
