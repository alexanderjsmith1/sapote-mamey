# cluster_completeness — assembly truncation vs biological absence

For a BGC on a short or edge contig, the question behind every downstream claim is: are the
genes it lacks missing because the assembly ran off the contig (artifact) or because the strain
genuinely lacks them (biology)? This assesses a query cluster against one or more complete
references and answers that — and unlike a raw ortholog matrix it is **truncation-aware**.

## What it does

1. **Consensus cluster genes.** A gene counts as a cluster gene only if it recurs in a strict
   majority of the references (both, when there are two), so flanking / genome-context singletons
   present in just one reference don't inflate the picture.
2. **Completeness.** = cluster genes with a query ortholog / cluster genes (global-identity,
   clinker-consistent). Reported with a tier (near-complete / substantial / partial / fragment).
3. **Truncation-awareness by contiguity.** The cluster genes are ordered in the frame of the
   reference that contains the most of them; if the query's present genes form a contiguous block
   and the missing genes fall OUTSIDE that block (at the ends), that reads as truncation. Missing
   genes BETWEEN present genes can't be explained by truncation and read as real loss / divergence.

## Usage

    python tools/cluster_completeness.py \
        --query "AS-XXX_BGC008:query.gbk" --query-boundary full-contig \
        --reference "x-80:x80.gbk" --reference "NPDC08785:npdc.gbk" \
        --outdir OUT

`--query-boundary` takes the triage value (interior | edge | full-contig). Outputs
`<query>_completeness.json` (score, tier, present/missing genes, interior-vs-end counts,
interpretation) and `<query>_missing_genes.csv`.

## Fits the pipeline

    scope_cluster -> (extract_cluster / fetch_reference_cluster) -> cluster_gene_compare
                                                                 -> cluster_completeness

## Validated

A cohort BGC (12 genes, full-contig) vs its complete public reference cluster: 75% complete (9/12 cluster
genes); missing carbamoyltransferase + O-methyltransferase + one unannotated gene, ALL at the
cluster ends -> read as truncation (assembly artifact), with the complete cluster carrying
carbamoyl + methyl decoration capacity the truncated contig can't show. Capacity-level: homology,
not product identity.
