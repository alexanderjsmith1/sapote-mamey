# v9.7.319 · fetch_reference_cluster (new module — reference/cohort ingress)

- **New tool `tools/fetch_reference_cluster.py`**: reconstruct a reference or cohort cluster GBK
  from the anchored BiG-SCAPE DB (`--acc ACCESSION:label`, matched on gbk.path substring — MIBiG or
  cohort) or from NCBI (`--ncbi`). Exposes the DB->CDS logic that was trapped inside
  bgc_reference_align as a reusable, file-producing step, and improves on hand reconstruction by
  writing **annotated** GBKs — Pfam domains from the DB `hsp` table become `/gene` labels (short-name
  where known, accession otherwise, never blank), which then feed clinker / cluster_gene_compare
  auto-labelling. Completes the ingress side of the external-comparison pipeline
  (fetch_reference_cluster + extract_cluster -> cluster_gene_compare). Validated: polyoxin
  (BGC0000877) -> 39 CDS, 35 annotated. Doc `FETCH_REFERENCE_CLUSTER.md`; test (3 pass, synthetic DB,
  no network). Engine unchanged at Mamey 1.9.111.
