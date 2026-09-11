# BGC-machinery domain-tree contract

Status: candidate interface contract. This document does not authorize or build a tree.

## Scope separation

A domain tree asks about relatedness among homologous biosynthetic machinery domains. It is not an organismal tree, BGC tree, product-identification method, pathway-completeness test, or physical-linkage proof. The organismal 138-SCG phylogeny remains a separate channel. PKS KS pools and RiPP enzyme/precursor pools remain family- and architecture-specific; they are not combined by default.

## Extractor interface

`mamey.ks_phylogeny.extract_module_core_domains` owns strain-internal raw domain extraction. Its required result fields are frozen here and in code:

<!-- DOMAIN_TREE_REQUIRED_TOP_LEVEL: strain,domains,class_counts,ks_per_node,claim_safety -->
<!-- DOMAIN_TREE_REQUIRED_DOMAIN_FIELDS: domain_class,locus_tag,domain_id,translation,node,region -->

| Layer | Required fields | Refusal boundary |
|---|---|---|
| extraction result | `strain`, `domains`, `class_counts`, `ks_per_node`, `claim_safety` | mixed or unrecognizable strain filenames refuse |
| each domain | `domain_class`, `locus_tag`, `domain_id`, `translation`, `node`, `region` | missing/invalid translation is not alignment-ready |
| alignment admission | complete `strain / full node-or-contig / region / BGC alias`, locus tag, domain ID, subtype/family, sequence SHA-256, source locator/hash | raw extractor rows lack the BGC alias and therefore require an exact inventory/module join before alignment |

The portable alignment-preparation owner is `tools/prepare_biosynthetic_tree_inputs.py`. Its sequence ledger supplies the BGC alias and source-row binding. No consumer may infer an alias from node order, region order, or a filename.

## Required workflow receipts

1. Extraction receipt: source GBK/module hashes, strain-internal check, retained/excluded counts, exact domain roster, and sequence hashes.
2. Pool-design receipt: one declared KS subtype or one homologous RiPP family, inclusion/exclusion reasons, duplicate-copy policy, reference provenance, and outgroup/rooting plan.
3. Alignment receipt: tool/version/command, input roster hash, alignment hash, retained columns, and invalid/short-sequence holds.
4. Inference receipt: tool/version/model/seed/thread count, alignment hash, tree hash, support method, and completion marker.
5. Figure/admission receipt: exact tip crosswalk, tree-sanity status, outgroup, omitted tips, caption/methods block, and output hashes.

## Guard composition

- Iterative-module guard: KS count is not module count or chain length; low KS count is not fragmentation evidence.
- Housekeeping convergence guard: FAS/FabB/FabF/FabH/hglE-like domains cannot anchor a rescue.
- Two-proof guard: domain co-clustering without RG-GMCI complementarity is `DOMAIN_ONLY_HINT`, never a rescue.
- Tree-source separation: rendering consumes a completed, bound tree and never builds, re-roots, or relabels it.
- Exact-locus gate: any BGC-specific tip must display `strain / full node-or-contig / region / BGC alias`; incomplete identity fails closed.
- Duplicate gate: exact copies remain enumerated; no silent one-tip-per-strain collapse.

## Claim ceiling

Domain topology can support domain-family relatedness and candidate evolutionary context. It does not establish product identity, pathway completeness, production, activity, novelty, physical linkage, species identity, ancestry direction, or horizontal transfer. Judgment deferred.
