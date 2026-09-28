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

## Placing fragments on a reference module order

A giant modular type I PKS in a draft genome often breaks into many small contigs. Each piece hits the same
reference clusters almost equally, so shared-reference homology, which RG-GMCI uses, cannot tell one pathway in many
pieces from a web of similar clusters. RG-GMCI demotes such webs as hubs. A KS tree that includes a reference
cluster's own module KS can tell them apart: pieces of one pathway sit one-to-one beside the reference's modules.

```bash
python tools/ks_module_placement.py inputs --gbk-dir <one isolate's region GBKs> \
  --reference BGC0002357.gbk --out placement_run
# run the two commands written to placement_run/COMMANDS.txt (MUSCLE, then IQ-TREE)
python tools/ks_module_placement.py place --tree placement_run/ks_tree.treefile \
  --out placement_run/placement.tsv
```

- Reference KS are numbered by position along the reference record (`MIBiG__<accession>_KS<nn>`). They are labelled
  tips, not a second query genome, so the one-isolate rule holds.
- Each isolate KS gets the smallest well-supported split of the tree around it (UFBoot ≥ 80 by default) that holds
  reference KS. The tree is read unrooted, so the call does not depend on the root.
  - `PLACED_ON_REFERENCE_MODULE`: one reference KS, shared with at most one other isolate KS. The module number
    is reported.
  - `MODULE_FAMILY`: one reference KS but more isolate KS than that. It reads as a family of similar modules.
  - `AMBIGUOUS_MODULES`: several reference KS fit.
  - `UNPLACED`: no supported split holds a reference KS.
- Read the placements per contig. Consecutive KS of one contig should land on consecutive modules. A run in reverse
  is what a minus-strand contig gives when KS are numbered by position.
- Choose references the pieces actually hit (KnownClusterBlast), and keep the tip count modest: a 265-tip tree with
  ModelFinder and 1,000 UFBoot took about 3.5 h on 4 threads.
- Worked public example: SID8382 (WGS WWFZ01). KS domains on ten contigs placed on 18 of the 30 modules of
  neomediomycin B (MIBiG BGC0002357), in order within each contig. The pieces included two RG-GMCI hubs whose pairs
  the hub guard had demoted. Protein homology agreed: the contig carrying module 1 also carried homologs of the
  reference's ten upstream genes in order (75–94% identity), and another carried the downstream acyltransferase,
  transporters, type II thioesterase and sulfotransferase (78–92%).
- Placement is advisory. It assigns no score, changes no RG-GMCI confidence, and joins nothing. Module order read from
  a tree is not contig order, and KS similarity is not product identity. Use it to decide which demoted RG-GMCI pairs a
  person should look at.

## Gene by gene against a reference cluster

`tools/gene_synteny_map.py` answers, for each gene of a reference cluster: does the genome carry a candidate match,
at what identity and coverage, on which contig, and do neighbouring reference genes find neighbouring matches on one
contig, in the reference's order?

```bash
python tools/gene_synteny_map.py --zip <antiSMASH.zip> --label <strain> --reference BGC0000115.gbk \
  --reference-name "nystatin A1" --out synteny_run [--placement placement_run/placement.tsv]
```

- It writes `gene_synteny.png` (the reference to scale, a heat row of best identity with a colour scale, a contig
  row, the full table and a contig key), `gene_synteny.tsv` and `gene_synteny_receipt.json`.
- Homology comes from DIAMOND through `mamey.diamond_align` when it is installed, or from `--hits`, a precomputed
  tabular file with the columns listed in the tool's docstring.
- **Modular PKS genes need KS placement.** Their modules resemble one another, so the best whole-gene match of a
  giant PKS gene tends to go to whichever contig carries the most modules. In SID8382 it placed one contig on three
  PKS genes about 100 kb apart; the KS tree placed that contig on two modules only. With `--placement` (from
  `tools/ks_module_placement.py place`), a PKS gene is assigned the contigs whose KS placed on its modules; without it,
  PKS matches are drawn hatched and marked "paralogous modules; see KS placement".
- Worked public examples: SID8382 against neomediomycin B, where 27 of 28 genes match (24 at ≥ 70% with placement)
  and the contigs step through the reference in order; and a nystatin A1 comparison where three blocks keep the
  reference order on single contigs.
- Identity is similarity, not product identity. The figure orders no contigs and joins nothing; a similar cluster is
  a class-level candidate.

## Missing genes, looked for across the genome

`tools/gap_directed_rescue.py` starts from one core region and a reference cluster and asks what the reference has
that the core lacks, then looks for those genes in every protein of the genome, not only inside antiSMASH regions.
The missing part of a split pathway often sits on a short contig that antiSMASH did not flag, because it holds
tailoring genes and no core gene; region-to-region pairing cannot see it.

```bash
python tools/gap_directed_rescue.py --zip <antiSMASH.zip> --label <strain> --core <contig>.region001 \
  --reference BGC0000809.gbk --reference-name "AT2433-A1" --out rescue_run
```

- A missing gene counts as found only when the genome's best match beats the next candidate's bitscore by 20% or more
  at 35% identity or above. Halogenases, glycosyltransferases and methyltransferases come in paralog families; only a
  clear margin picks one.
- A partner is another contig with two or more clear finds. It is reported as concentrated when the two leading
  partners hold at least 60% of all clear finds (a missing piece puts the genes in one or two places; paralogs
  scatter them), and as a plausible split when the core runs to a contig end, the partner contig is under 30 kb, or
  its region touches a contig end.
- The reference's own antiSMASH `gene_kind` separates biosynthetic finds from regulators, transporters and flanking
  housekeeping genes that some MIBiG entries include.
- Outputs: `gap_rescue.tsv`, `gap_rescue_partners.tsv`, `gap_rescue_receipt.json` and `gap_rescue.png`. The figure puts
  the reference in the middle and each contig above or below it, on the side where its ribbons cross no other contig.
  Contig ends are heavy bars, and matched genes carry the number of their reference gene. The table beneath lists
  locus, protein lengths, identity and coverage.
- Modular PKS genes of the reference (genes carrying a KS domain) are drawn hatched and never count toward a partner:
  their best whole-gene match follows module paralogy. Order those pieces with KS placement (above).
- Ribbons join reciprocal best matches only. When several reference genes share one genome protein as their best
  match (paralogous PKS modules), only the closest keeps the ribbon; the table lists the others as cross-hits.
- Homology comes from DIAMOND through `mamey.diamond_align`, or from `--hits`.
- A partner contig is a candidate missing piece. Nothing is joined, and a fragmented assembly is never joined with
  full confidence. Identity is similarity, not product identity.

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
