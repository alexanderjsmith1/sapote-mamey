# Historical cluster_relate change note

The module-announcement text below is retained development history. Its “outgroup” and ortholog wording does not describe a phylogenetically established relationship. Current `tools/cluster_relate.py:344–360,386–395` labels the least similar input under a descriptive metric and explicitly denies phylogenetic outgroups, orthology, compound or activity inference. CLI `:400–408` offers legacy_checked and one_to_one_v1 metrics; preserve the actual selected metric/input/hash/result bindings.

Use [the current cluster comparison guide](CLUSTER_RELATE.md) for present inputs, outputs and recovery. The historical topology/dataset assertion and “2 pass” count below require their original test/run receipts before reuse. Keep clustering, sequence alignment, rendered figures and scientific acceptance as separate evidence states.

## Retained announcement — unchanged below

# cluster_relate (new module — cluster relationship tree)

- **New tool `tools/cluster_relate.py`**: turns a set of homologous cluster GBKs into a distance
  matrix, UPGMA dendrogram, Newick tree, and (with --pdf) a figure + methods + interpretation naming
  the closest pair and the outgroup. Distance = 1 - [(shared orthologs / min gene count) x mean
  global identity], using the clinker-consistent global-identity metric shared with cluster_gene_compare;
  it rewards both gene-content overlap and sequence conservation. UPGMA is pure-python (no tree lib);
  dendrogram via scipy, alignment via Bio.Align, optional pyswrd prefilter. Completes the comparative
  chain: fetch_reference_cluster/extract_cluster -> cluster_gene_compare -> cluster_relate. Validated
  on a set of related clusters -> expected topology (query with sisters; MIBiG refs outgroup). Doc
  CLUSTER_RELATE.md; test test_cluster_relate.py (2 pass, synthetic, no network). Builder (no gate
  row); engine unchanged at Mamey 1.9.111.
