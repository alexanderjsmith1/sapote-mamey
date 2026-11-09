# Single-region and comparison figures for one BGC

A BGC is a biosynthetic gene cluster. This page covers the small figure tools you run by hand
on one region GenBank file (GBK) or one antiSMASH ZIP. For the standard gene maps of a whole
package, use `render-figures --figure-set locus-maps` ([figures router](FIGURES_START_HERE.md)).

Use this page when you want one of these:

| I want | Run | Needs |
|---|---|---|
| Gene arrows for one region | `python mamey_run.py figures diagram <region.gbk> <out.png>` | A region GBK |
| A region against its closest MIBiG clusters | `python mamey_run.py figures kcb-locusmap` | The antiSMASH ZIP, or one KnownClusterBlast text file |
| Locus map, GCF novelty and BLASTp identity for one region | `python tools/bgc_figures.py --gbk <region.gbk>` | A region GBK; the database and BLASTp table are optional |
| A circular map of one strain | `python mamey_run.py figures atlas <antismash_dir> <out.png>` | An antiSMASH output folder |
| A GCF network from a BiG-SCAPE database | `python mamey_run.py figures gcf-network` | See `--help` and the [BiG-SCAPE walkthrough](BIGSCAPE_COHORT_WALKTHROUGH.md) |
| A gene-cluster alignment as HTML | `python mamey_run.py figures clinker <gbk> <gbk> ... --out <out.html>` | Two or more region GBKs |

Terms. **KnownClusterBlast (KCB)** is the antiSMASH comparison of a region with characterized
clusters in **MIBiG**, the database of known clusters. A **GCF** is a gene cluster family from
BiG-SCAPE. See the [glossary](GLOSSARY.md). Every figure here shows similarity, not product
identity. Treat each one as a supporting view, not evidence for a finished card.

## Install the plotting libraries

From the bundle root, inside your virtual environment:

```bash
python -m pip install -e '.[figures]'
```

This adds DNA Features Viewer, pyCirclize and Biopython. It does not add the ANI scanner or any
reference data. For offline wheels, see [Install](INSTALL.md#3-add-the-features-you-need).
A successful install does not show that your input is valid or that a figure will render.

## KCB comparative locus map

This map is offline. It needs only matplotlib and the files inside the raw antiSMASH ZIP. Query
gene arrows sit on top, colored by role from the region GBK. The top MIBiG reference clusters
stack below, each reference gene under the query gene it pairs with. Ribbons join paired genes
and are shaded by BLAST percent identity.

```bash
python mamey_run.py figures kcb-locusmap --zip inputs/EXAMPLE_antismash.zip \
  --contig NODE_106 --region region002 --out-dir reviews/EXAMPLE/kcb_map
```

Give the full contig name and the region together. A contig alone does not name one region, and
a region number alone can match the same region on a different contig. If the ZIP is ambiguous,
extract the one `knownclusterblast/*.txt` file you mean and pass it with `--kcb-txt`.

You should see a line such as `[kcb-locusmap] reviews/EXAMPLE/kcb_map/<stem>_kcb_locusmap.png`
and three files in the output folder:

- `<stem>_kcb_locusmap.png`
- `<stem>_kcb_locusmap.svg`
- `<stem>_kcb_locusmap_data.csv`, one row per paired gene

How to read it:

- The tool reads `knownclusterblast/*.txt`. If the ZIP has none, it reads `clusterblast/*.txt`
  instead. ClusterBlast compares against other genomes, not MIBiG, so that figure is not a MIBiG
  comparison. Check the ZIP before you rely on the title.
- An empty KnownClusterBlast file still draws a figure, with no reference clusters and zero pairs.
  That is "no hits", not proof that nothing similar exists. The package reports it as
  `KNOWNCLUSTERBLAST_NO_HITS_UNVALIDATED`.
- The CSV lists only query genes that pair with a reference. It does not carry the strain,
  contig and region as separate columns. Record the four-part identity
  (**strain / full contig / region / BGC alias**) beside the figure yourself.
- The figure prints the claim-ceiling sentence in small type at the bottom. The
  [figure house rules](FIGURE_HOUSE_RULES.md) put that wording in the caption, not on the plot.
  Cut the sentence from the figure and put it in your caption before you publish.
- Output names come from the stem, and a repeat run with the same stem overwrites. Use a new
  `--out-dir` each time.

## Gene arrow diagram

```bash
python mamey_run.py figures diagram inputs/EXAMPLE_region001.gbk reviews/EXAMPLE/region001.png
```

The command writes the PNG you name. Arrow labels use the first domain word of each gene, so
the labels do not list every locus tag. Use the locus-map package figure when you need the
full gene roster.

## Region figure set

```bash
python tools/bgc_figures.py --gbk inputs/EXAMPLE_region001.gbk --bgc BGC001 --strain EXAMPLE \
  --blastp inputs/EXAMPLE_blastp.csv --outdir reviews/EXAMPLE/region_figs
```

`--gbk` is the only required flag. Without `--db` the GCF novelty plot is skipped, and without
`--blastp` the BLASTp plot is skipped. Before it writes anything, the tool checks every output it
plans: if any of those files already exists, or an output path is one of the inputs, it prints
`refused:` and exits 2. Use a new `--outdir` for each run. The tool prints each file it wrote. Each
figure is a 150-dpi PNG with a matching `_data.csv`:

- `<tag>_fig1_locus.png`: gene arrows, labeled by function
- `<tag>_fig2_gcf_novelty.png`: the records with the smallest BiG-SCAPE distance to this region,
  from `--db`. Distance 0 is the closest value in that run, not sequence or product identity.
- `<tag>_fig3_blastp.png`: per-gene BLASTp identity, from `--blastp`

Limits to check:

- The GCF plot reads every distance row for the strain in the database and takes the first
  matching record. It does not pick a BiG-SCAPE run or a cutoff. Use a database from one run.
- The BLASTp plot draws a bar only for a gene with a recorded identity. The CSV lists every gene
  of the region with `identity_state`: `MEASURED`, `NO_IDENTITY_RECORDED` (the gene has a row in
  `--blastp` but no readable identity; that can be a no-hit search or a missing value) or
  `NOT_IN_BLASTP_TABLE` (the gene has no row). Neither of the last two is 0 percent identity.
- The tool writes no receipt with input hashes. Save the inputs and a hash of each output
  yourself.

## Circular map and ANI

`figures atlas` draws the top 20 regions of one strain as a circular map. Two regions with the
same contig name overwrite each other, so do not read it as a whole-genome atlas.

`figures ani` compares two or more strain folders and needs `pyskani` from the `addons` extra.
It uses the first FASTA it finds in each folder and does not check that the FASTA belongs to
the strain. A missing direction is not zero. The matrix shows the measured value, the average
of two measured values, or `no hit`. The fixed species-boundary title is not a taxonomy
verdict. With fewer than two usable folders it writes no figure and exits 1.

## Related pages

- [Locus map v8](LOCUS_MAP_V8.md): the package's default gene map, with the full gene roster
- [Locus-map review contract](LOCUS_MAP_REVIEW_CONTRACT.md): the maintainer contract those maps follow
