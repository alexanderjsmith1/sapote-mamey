# cluster_gene_compare — gene-by-gene BGC comparison as a real deliverable

Turns a set of cluster GenBank files into a substantial, self-documenting deliverable rather
than a floating CSV: a gene-pair table, an annotated ortholog-identity **figure**, a **PDF**
with computational **methods** and auto-generated **interpretation**, and GenBank files whose
`/gene` qualifiers are filled in so **clinker shows real gene names automatically**.

## Usage

    python tools/cluster_gene_compare.py \
        --gbk "AS-XXX_BGC008:AS-XXX_BGC008.gbk" \
        --gbk "NPDC08785:NPDC08785_nuc.gbk" \
        --gbk "x-80:x80_nuc.gbk" \
        --gbk "polyoxin:polyoxin.gbk" \
        --gbk "nikkomycin:nikkomycin.gbk" \
        --title "Nucleoside BGC comparison" --outdir OUT --pdf

`LABEL:path` sets each cluster's column name. `--min-id` is the confident-ortholog global
identity cutoff (default 30). `--engine pyswrd` prefilters candidate pairs for large inputs.

## Outputs (in `--outdir`)

| file | contents |
|---|---|
| `annotated_gbks/*.gbk` | inputs with `/gene` labels — **feed these to clinker** for named genes |
| `gene_pairs.csv` | every cross-cluster gene pair: global identity, coverage, tier |
| `ortholog_matrix.csv` | ortholog group x cluster, resolved label + member locus tags |
| `comparison_heatmap.png` | annotated presence/identity heatmap (RGB, viewer-safe) |
| `comparison.pdf` | heatmap + **methods** + **interpretation** (with `--pdf`) |

## How gene names get into clinker (the annotation step)

clinker labels genes from the GenBank `/gene` (or `/locus_tag`) qualifier, so ab-initio
(pyrodigal) clusters show only `ctgN_M`. This tool resolves a functional label for every gene:

1. from the gene's own `sec_met_domain` / `gene_functions` / `product` qualifiers (antiSMASH), then
2. by **homology propagation** — a gene with no annotation inherits the label of an annotated
   ortholog (same ortholog group).

The resolved label is written to `/gene` in `annotated_gbks/`. Annotate one cluster well
(or run antiSMASH on one), and the labels flow to the orthologs in every other cluster,
including ab-initio ones — then `clinker annotated_gbks/*.gbk` is automatically labelled.

## The identity metric (why global, not local)

Percent identity is computed on a **global** Needleman-Wunsch alignment (BLOSUM62, gap -11/-1)
as `matches / (alignment length - gap/gap columns)` — the same metric clinker uses. Local
%identity over a partial aligned region overcounts distant/partial homologs (a short high-identity
block in an otherwise-dissimilar protein passes a naive local test); global identity does not.
This is the same correctness lesson as the reference-align patch.

## Scope / limitations (stated in every PDF)

Identity is homology (shared ancestry), never proof of the same product. Ab-initio gene
boundaries are approximate. Truncated/edge clusters under-report shared genes. Capacity-level.

Engine: `Bio.Align` global (BLOSUM62). Optional `pyswrd` prefilter. No BLAST+ binary required
(pairwise protein alignment is ms-scale); BLAST+ could be wired as an alternative engine.
