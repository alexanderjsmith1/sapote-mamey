# PKS ketosynthase-tree option guide

## Purpose

This track asks how individual PKS ketosynthase (KS) domains are related. It is
not an organismal tree and is not a compound-identification procedure. The
Actinobacteria 138-SCG GToTree alignment remains the organismal backbone.

## Why KS domains rather than complete PKS proteins

Type I PKS proteins are frequently multi-module, duplicated, recombined, and
several thousand amino acids long. Aligning complete proteins can compare
different architectures rather than homologous catalytic units. The normalized
antiSMASH module export already supplies domain-level translations, coordinates,
domain IDs, active-site annotations, and often a `domain_subtypes` value.

Each KS domain therefore receives its own tip:

```text
strain|BGC|locus|domain_id|subtype
```

Multiple tips from one locus, BGC, or strain are retained. Exact sequence
duplicates are reported but not silently collapsed.

## Separate target pools

Do not place all `PKS_KS` calls into one default tree. Prepare one pool per exact
antiSMASH subtype and then inspect architecture before alignment.

| Pool | Initial selector | Primary use | Binding caution |
|---|---|---|---|
| iterative KS | `Iterative-KS` | iterative/type-II-like or aromatic-pathway context | verify whether the call is a discrete enzyme or embedded domain |
| modular KS | `Modular-KS` | cis-AT modular PKS comparison | one protein can contribute multiple module tips |
| trans-AT KS | `Trans-AT-KS` | trans-AT pathway evolution | include trans-AT references; do not mix with cis-AT by default |
| hybrid KS | `Hybrid-KS` | PKS-NRPS and mixed architecture | inspect adjacent domains and module boundaries manually |

Unknown or blank subtypes remain a review pool. They are not assigned to the
nearest clade merely from sequence identity.

## Preparation

The manifest is tab-separated and identifies every strain explicitly:

```text
strain_id  inventory_csv  modules_csv  rrefinder_csv  ripp_motifs_csv  proteins_faa
```

Example:

```bash
python tools/prepare_biosynthetic_tree_inputs.py sources.tsv pks_iterative_pool \
  --track pks-ks --subtype Iterative-KS
```

Review:

- `sequence_ledger.tsv`: exact strain+BGC+locus/domain decisions;
- `exact_sequence_groups.tsv`: retained identical copies;
- `receipt.json`: source hashes, counts, parameters, and claim ceiling;
- `sequences.faa`: alignment-ready sequences only.

`READY_FOR_ALIGNMENT` requires at least four eligible sequences. That is a
technical floor, not evidence that the sample is biologically well designed.

## Alignment choices

All examples keep one CPU per tree.

| Choice | Command | When to use |
|---|---|---|
| higher-accuracy MAFFT | `mafft --localpair --maxiterate 1000 --thread 1 sequences.faa > aligned.faa` | preferred for a bounded, homologous KS pool |
| automatic MAFFT | `mafft --auto --thread 1 sequences.faa > aligned.faa` | larger exploratory pools |
| no automatic trim | retain full alignment first | review ends and conserved active-site region before trimming |

If trimming is used, save the untrimmed alignment, command, version, retained
columns, and tip crosswalk. Removal of poorly aligned residues does not validate
a questionable domain call.

## IQ-TREE choices

Recommended governed starting point:

```bash
iqtree3 -s aligned.faa \
  -m MFP -mset LG,WAG,JTT,Q.pfam -mrate G,I,I+G \
  -B 1000 -alrt 1000 -seed 12345 -T 1 --mem 2G \
  -pre pks_ks_iterative
```

Keep the model-selection report, alignment, treefile, log, and checksums. Do not
reuse organismal-tree branch lengths or root. Use a verified homologous outgroup
when available; otherwise label midpoint rooting as a display choice.

## Reference choices

Prefer domain sequences from:

1. experimentally characterized MIBiG BGCs with explicit domain provenance;
2. antiSMASH KnownClusterBlast/ClusterBlast candidates after exact BGC mapping;
3. curated Swiss-Prot or reviewed literature sequences;
4. nr/ClusteredNR only with database channel and query coverage preserved.

A named-compound reference provides a comparison label, not a product call for
the AS/SID BGC.

## Required gates

- exact `(strain_id, bgc_id, locus_tag, domain_id)` label;
- current mapped BGC in the matching inventory;
- valid amino-acid sequence and minimum length;
- one explicit KS subtype per default tree;
- active-site/motif review and long-branch inspection;
- architecture/synteny review for any biological interpretation;
- no silent duplicate collapse or one-tip-per-strain reduction.

## Claim ceiling

KS topology can support domain-family relatedness and candidate evolutionary
context. It does not establish product identity, pathway completeness,
production, activity, novelty, species identity, or horizontal transfer.
