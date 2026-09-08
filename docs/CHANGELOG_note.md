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
