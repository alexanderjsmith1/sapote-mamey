# cluster_relate — relationship tree + distance matrix from homologous clusters

The comparative tools produce ortholog tables, but the *relationship* between clusters — which
are near-identical, which are diverged, which is the outgroup — was left to eyeball. This turns a
set of cluster GBKs into a distance matrix, a UPGMA dendrogram, a Newick tree, and (with `--pdf`)
a figure + methods + interpretation naming the closest pair and the outgroup.

## Distance metric

    similarity(A,B) = (shared_orthologs / min(|A|,|B|)) x mean_global_identity_over_orthologs
    distance(A,B)   = 1 - similarity(A,B)

Orthologs are confident **global**-identity (clinker-consistent) gene pairs >= `--min-id`. The
metric rewards both gene-content overlap and sequence conservation, so a shared 3-gene warhead at
40% ranks far from a 14-gene near-identical cluster at 79%.

## Usage

    python tools/cluster_relate.py \
        --gbk "AS-XXX_BGC008:BGC008.gbk" \
        --gbk "NPDC08785:NPDC.gbk" --gbk "x-80:x80.gbk" \
        --gbk "polyoxin:polyoxin.gbk" --gbk "nikkomycin:nikkomycin.gbk" \
        --outdir OUT --pdf

Outputs: `distance_matrix.csv`, `dendrogram.png`, `tree.nwk`, `comparison.pdf`. UPGMA is pure
Python (no tree library); the dendrogram uses scipy; identity uses Bio.Align. `--engine pyswrd`
prefilters ortholog candidates for large inputs.

## Fits the pipeline

    fetch_reference_cluster / extract_cluster  ->  annotated cluster GBKs
    cluster_gene_compare                       ->  gene-by-gene ortholog view
    cluster_relate                             ->  the relationship tree over those clusters

## Validated

On a set of related clusters it recovers the expected topology (the query branching with its
nearest sisters, the two characterised MIBiG references forming the outgroup pair).
Capacity/architecture-level: distance is homology, not product identity. [cohort exemplar [Redacted — publication in preparation]]
