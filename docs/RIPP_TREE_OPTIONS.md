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

- exact strain+BGC+locus and, where relevant, motif/domain index;
- exact current inventory join;
- one explicit RiPP family/class per default pool;
- full sequence and coordinate provenance;
- minimum length and invalid-residue checks;
- no silent deduplication;
- enzyme architecture and precursor-context review;
- tree-versus-network choice recorded;
- claim-safe caption and source receipt.

## Claim ceiling

These analyses can support sequence-family relatedness, diversification, and
candidate pathway-evolution context. They do not prove a mature product,
production, activity, novelty, species identity, or horizontal transfer.
