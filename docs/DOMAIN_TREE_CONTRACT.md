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

The portable alignment-preparation owner is `tools/prepare_biosynthetic_tree_inputs.py`. Its sequence ledger supplies the BGC alias and source-row binding, but not all four identity components. No consumer may infer an alias from node order, region order, or a filename.

## Current retry and output boundaries

The required receipts below are acceptance requirements. The current
`tools/build_domain_tree.py` runner does not produce that complete receipt set.
A staging-only run writes files: `--skip-inference` stops after extraction and
staging and returns success without running inference. It is not a read-only
preview and does not establish a completed tree.

Use a distinct output directory for each attempt and retain prior outputs with
their input bindings. The current `mamey/domain_tree.py` writes fixed output
names directly. A staging refusal can replace the provenance table while leaving
an earlier FASTA, alignment, tree and summary in that directory. Inference opens
the alignment for replacement and requests IQ-TREE redo. This is not an atomic
output-set transaction or checkpoint resume. After a refusal or interruption,
existing files alone do not identify which outputs belong to that attempt.

A full runner success means the tree passed its sanity gate and a summary was
written. The summary currently uses raw extracted rows, including rows excluded
from staging, and leaves tip, BGC alias, clade and reference measurements blank.
It is not an admitted-tip crosswalk or a completed placement table. This runner
does not write the clade table or render a figure. Preserve the input roster,
staging decisions, native logs and hashes, and verify the current tree and exact
tip crosswalk before using downstream outputs.

The separate `tools/domain_phylo_rescue.py` exporter replaces its requested TSV
path directly. An empty result writes a header-only file; its JSON summary is
printed to the console rather than saved as a bound completion receipt. Retain
that invocation's input hashes, output hash, console summary and failure state.
A retained older TSV after an input or runtime failure is not a current result;
an empty successful export and a failed attempt must remain distinct.

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


## Current preparation identity boundary

The .447 `tools/prepare_biosynthetic_tree_inputs.py` checks a strain-local BGC alias
against the supplied inventory and records source file/row, locus, sequence digest
and its generated tip token. Its inventory reader retains products by `bgc_id`;
the emitted sequence ledger and FASTA tip do **not** carry the full contig/node and
region components of `strain / full node-or-contig / region / BGC alias`.

A `MAPPED` row, alias membership or `READY_FOR_ALIGNMENT` count therefore does not
establish the complete locus identity. Before using an individual locus as an
alignment/figure tip, make an exact join to the bound current inventory/module
record and retain all four identity components plus locus/domain and source hashes.
Do not infer those missing fields from tip order or the alias. Unresolved or
conflicting joins remain identity holds. The preparer currently needs an owning
code change to emit and verify that complete crosswalk automatically.

## Claim ceiling

Domain topology can support domain-family relatedness and candidate evolutionary context. It does not establish product identity, pathway completeness, production, activity, novelty, physical linkage, species identity, ancestry direction, or horizontal transfer. Judgment deferred.
