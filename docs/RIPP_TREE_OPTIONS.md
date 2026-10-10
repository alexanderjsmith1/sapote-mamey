# RiPP tree and sequence-network option guide

## Purpose

RiPPs require family-specific analysis. A single tree containing all RiPP
precursors or all RiPP enzymes is not biologically coherent. The workflow first
chooses a homologous family, then chooses the sequence unit that can answer the
question.

## Track selector

| RiPP question | Preferred sequence unit | Default visual | Caution |
|---|---|---|---|
| lanthipeptide synthetase evolution | LanB, LanC, LanM, or LanKC family-matched enzyme/domain | enzyme tree | do not mix classes I-IV without an explicit deep-family design |
| YcaO-associated pathways | family- and architecture-matched YcaO enzyme | enzyme tree | YcaO occurs in distinct chemistries; BGC context is mandatory |
| RRE-bearing systems | RRE domain plus cognate enzyme/precursor context | network or small family tree | short domains may have weak deep-tree resolution |
| precursor diversification | precursor within one homologous RiPP family | sequence-similarity network; tree only after alignment review | short cores, leader variation, and repeat-rich sequences can destabilize topology |
| radical-SAM RiPP maturation | family-matched radical-SAM enzyme | enzyme tree | radical-SAM is far broader than RiPP biosynthesis |

The organismal 138-SCG tree remains separate. A RiPP enzyme or precursor tree is
a pathway-evolution layer.

## Preparation commands

The source manifest identifies every strain explicitly. RiPP enzymes may come
from a normalized antiSMASH module row that already contains a domain
translation, or from `domains_csv` plus `proteins_faa`. The latter prepares a
full-protein enzyme sequence while retaining the matched domain as its
selection evidence.

Family-matched enzyme/domain example:

```bash
python tools/prepare_biosynthetic_tree_inputs.py sources.tsv lanthipeptide_iii_lanc \
  --track ripp-enzyme \
  --domain LANC_like \
  --domain micKC \
  --family lanthipeptide-class-iii
```

RRE example:

```bash
python tools/prepare_biosynthetic_tree_inputs.py sources.tsv azole_rre_pool \
  --track ripp-rre --family azole-containing-RiPP
```

Family-specific precursor example:

```bash
python tools/prepare_biosynthetic_tree_inputs.py sources.tsv lanthipeptide_iii_precursors \
  --track ripp-precursor --family lanthipeptide-class-iii
```

The tool requires an explicit family filter. RRE extraction also requires the
matched protein FASTA because the normalized RRE table preserves coordinates
but does not itself carry every amino-acid sequence.

## Enzyme-tree alignment

For a bounded, homologous enzyme/domain pool:

```bash
mafft --localpair --maxiterate 1000 --thread 1 sequences.faa > aligned.faa
iqtree3 -s aligned.faa \
  -m MFP -mset LG,WAG,JTT,Q.pfam -mrate G,I,I+G \
  -B 1000 -alrt 1000 -seed 12345 -T 1 --mem 2G \
  -pre ripp_family_enzyme
```

Before interpreting the tree, inspect alignment coverage, conserved catalytic
regions, architecture, BGC class, precursor adjacency, duplicate copies, and
long branches.

## Precursor analysis

Use a tree only when the precursor set is clearly homologous and the alignment
has defensible shared columns. Otherwise use a sequence-similarity network:

```text
precursor sequences
→ all-vs-all similarity with coverage retained
→ family-specific thresholds
→ connected components
→ overlay BGC class, strain, host cohort, and MIBiG references
```

Leader and core regions should remain separately visible. A high core-peptide
identity does not by itself establish the same mature product because processing,
tailoring, cleavage, and stereochemistry can differ.

## Reference choices

- curated MIBiG precursors and maturation enzymes with explicit BGC/locus keys;
- class-matched antiSMASH references;
- reviewed proteins with literature support;
- channel-separated nr, ClusteredNR, Swiss-Prot, and EBI evidence.

Do not merge database channels or transfer a compound name from the top sequence
hit to the query BGC.

## Required gates

- exact `strain / full node-or-contig / region / BGC alias`, plus locus tag and, where relevant, motif/domain index;
- exact current inventory join;
- one explicit RiPP family/class per default pool;
- full sequence and coordinate provenance;
- minimum length and invalid-residue checks;
- no silent deduplication;
- enzyme architecture and precursor-context review;
- tree-versus-network choice recorded;
- claim-safe caption and source receipt.


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

These analyses can support sequence-family relatedness, diversification, and
candidate pathway-evolution context. They do not prove a mature product,
production, activity, novelty, species identity, or horizontal transfer.
