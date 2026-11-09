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

The organismal tree, built from 138 single-copy genes (see [phylogenomics](phylogenomics.md)), remains separate. A RiPP enzyme or precursor tree is
a pathway-evolution layer.

## Preparation commands

`tools/prepare_biosynthetic_tree_inputs.py` builds a sequence pool. It runs no tree. The command is:

```bash
python tools/prepare_biosynthetic_tree_inputs.py <manifest.tsv> <new-output-folder> --track <track> [options]
```

The output folder must not exist yet. The tracks are `pks-ks`, `ripp-enzyme`, `ripp-rre` and `ripp-precursor`. Every RiPP track requires `--family`, and `ripp-enzyme` also requires at least one `--domain`. `--min-aa` sets the minimum length; the defaults are 80 (`ripp-enzyme`), 35 (`ripp-rre`) and 8 (`ripp-precursor`). `--show-options` prints the rules and exits.

### Source manifest

The manifest is a tab-separated file with one row per strain. Paths are resolved relative to the manifest file, and each path must exist.

| Column | Required | Holds |
|---|---|---|
| `strain_id` | yes, unique | Strain label |
| `inventory_csv` | yes | The BGC inventory file from that strain's package |
| `modules_csv` | no | Normalized antiSMASH module rows (with domain translations) |
| `domains_csv` | no | Domain rows, used with `proteins_faa` |
| `rrefinder_csv` | no | RRE rows (for `ripp-rre`) |
| `ripp_motifs_csv` | no | Precursor motif rows (for `ripp-precursor`); see [the antiSMASH inputs page](ANTISMASH_INPUTS_CONSUMED.md) for the motif export |
| `proteins_faa` | no | Protein FASTA matching the rows above |

These are the strain's package tables and the protein FASTA from the same run. The RRE and motif
tables must carry `bgc_id`, `locus_tag` and `mapping_status`; a row counts only when
`mapping_status` is `MAPPED` and its `bgc_id` is in the inventory. The RRE table also uses
`rre_family`, `protein_start` and `protein_end`. The motif table uses `ripp_family` (or
`peptide_class`), `leader`, `core_sequence`, `tail` and `motif_index`. A row that fails these tests
is held, not dropped: read `reason` in `sequence_ledger.tsv` before you trust a count. The tool does
not infer missing parts from tip order or the alias.

An RRE row is cut from its protein by `protein_start` and `protein_end` (1-based, inclusive). When
either is blank, is not a whole number, or falls outside the protein, the row is held with
`RRE_COORDINATES_MISSING`, `RRE_COORDINATES_NOT_INTEGER` or `RRE_COORDINATES_OUTSIDE_PROTEIN`. The
full protein is never used in its place. A held row has a blank `aa_length` and `sequence_sha256`.

An identifier that appears twice in `proteins_faa`, or a `BGC_ID` that appears twice in an
`inventory_csv`, stops the run with an error, and no output folder is written. Remove or rename the
repeated record first.

Example, with tabs between columns:

```text
strain_id	inventory_csv	domains_csv	proteins_faa
EXAMPLE-1	EXAMPLE-1/inventory.csv	EXAMPLE-1/domains.csv	EXAMPLE-1/proteins.faa
EXAMPLE-2	EXAMPLE-2/inventory.csv	EXAMPLE-2/domains.csv	EXAMPLE-2/proteins.faa
```

A RiPP enzyme comes either from a module row that already holds a domain translation, or from `domains_csv` plus `proteins_faa`. The second route prepares the full-length protein and keeps the matched domain as its selection evidence. RRE extraction needs `proteins_faa`, because the RRE table keeps coordinates but not every sequence.

### Examples

Enzyme or domain pool:

```bash
python tools/prepare_biosynthetic_tree_inputs.py sources.tsv lanthipeptide_iii_lanc \
  --track ripp-enzyme --domain LANC_like --domain micKC \
  --family lanthipeptide-class-iii
```

RRE pool:

```bash
python tools/prepare_biosynthetic_tree_inputs.py sources.tsv azole_rre_pool \
  --track ripp-rre --family azole-containing-RiPP
```

Precursor pool:

```bash
python tools/prepare_biosynthetic_tree_inputs.py sources.tsv lanthipeptide_iii_precursors \
  --track ripp-precursor --family lanthipeptide-class-iii
```

### What you should see

The command prints JSON with the output path, a `status` and counts. The folder holds:

- `sequences.faa`: the eligible sequences, one tip token each;
- `sequence_ledger.tsv`: every candidate with a status and reason, kept or excluded;
- `exact_sequence_groups.tsv`: identical sequences. Copies stay in the pool;
- `receipt.json`: the parameters, counts and a SHA-256 for each source file.

`READY_FOR_ALIGNMENT` means at least four sequences are eligible. Fewer gives `HOLD_TOO_FEW_ELIGIBLE_SEQUENCES`. The command exits 0 in both cases, so read the status. A manifest error exits non-zero.

## Enzyme-tree alignment

This step builds a tree, which is compute. Do the size check and get approval first, as described in [the phylo autopilot workflow](PHYLO_AUTOPILOT_WORKFLOW.md) and [the phylogenetics workflow](PHYLOGENETICS_WORKFLOW.md). Check that the tools exist with `mafft --version` and `iqtree3 --version`.

For a bounded, homologous enzyme or domain pool:

```bash
mafft --localpair --maxiterate 1000 --thread 1 sequences.faa > aligned.faa
nice -n 15 iqtree3 -s aligned.faa \
  -m MFP -mset LG,WAG,JTT,Q.pfam -mrate G,I,I+G \
  -B 1000 -alrt 1000 -seed 12345 -T 1 --mem 2G \
  -pre ripp_family_enzyme
```

The run is complete only when you have a `.treefile` and a `.contree`, a `.iqtree` report, and a `.log` that ends with "Total wall-clock time". A `.treefile` alone means the run was interrupted. Keep the alignment, the log and the model-selection report.

Before you read the tree, inspect alignment coverage, conserved catalytic regions, architecture, BGC class, precursor adjacency, duplicate copies and long branches.

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


## Tip identity

The preparer's sequence ledger and FASTA tip token do not carry the full contig or region. A tip is not a full locus identity. The same limit is spelled out in [the domain-tree contract](DOMAIN_TREE_CONTRACT.md#current-retry-and-output-boundaries). Join each tip to the current inventory and keep all four parts, `strain / full node-or-contig / region / BGC alias`, before using it as a locus.

## Claim ceiling

These analyses can support sequence-family relatedness, diversification, and
candidate pathway-evolution context. They do not prove a mature product,
production, activity, novelty, species identity, or horizontal transfer.
