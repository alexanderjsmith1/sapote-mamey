# PKS ketosynthase-tree option guide

This page is for readers who already have a validated package (see [First run](reader/01_FIRST_RUN.md)) and want to compare polyketide synthase (PKS) ketosynthase (KS) domains. A KS domain is the catalytic domain that joins two-carbon units. The tools here are optional helpers. They read saved antiSMASH output, change nothing in the package, and give candidate evidence only.

Which tool to use:

| Question | Tool | Section |
|---|---|---|
| Do my contig pieces tile a reference PKS protein? | `tools/pks_piece_map.py` | [First check](#first-check-do-the-pieces-tile-the-reference-protein) |
| Which KS domains are related? | `tools/prepare_biosynthetic_tree_inputs.py`, MAFFT, IQ-TREE | [Build a KS tree](#build-a-ks-tree) |
| Which reference module does each KS sit on? | `tools/ks_module_placement.py` | [Placing fragments](#placing-fragments-on-a-reference-module-order) |
| Which reference genes does my genome carry? | `tools/gene_synteny_map.py` | [Gene by gene](#gene-by-gene-against-a-reference-cluster) |
| Where are the reference's missing genes? | `tools/gap_directed_rescue.py` | [Missing genes](#missing-genes-looked-for-across-the-genome) |

## Before you start

- Install the tools you use. Run `python mamey_run.py doctor --companions` to see whether MUSCLE and IQ-TREE 3 (`iqtree3`) are present. It does not check MAFFT, so check `mafft --version` yourself. Setup is in [Prerequisites](PREREQUISITES.md) and [Companion tools](companion_tools.md).
- DIAMOND must be on your PATH for `pks_piece_map.py`, `gene_synteny_map.py` and `gap_directed_rescue.py`, unless you pass precomputed hits (see each section).
- A tree is a long run. Run one tree at a time under `nice -n 15` with at most 4 threads. Read the size check in [LLM_COMPANION_TOOL_PROTOCOL.md](LLM_COMPANION_TOOL_PROTOCOL.md) first.
- Write every output to a new folder outside the package.
- Four tools take a reference cluster as a MIBiG GenBank file (`BGC0000116.gbk`, an antiSMASH-annotated GenBank file): `pks_piece_map.py` (`--reference-gbk`), `ks_module_placement.py`, `gene_synteny_map.py` and `gap_directed_rescue.py` (`--reference`). Download them from the [MIBiG download page](https://mibig.secondarymetabolites.org/download). Each tool opens the path you pass as given. Only `gap_directed_rescue.py` also looks in a folder, `--mibig-dir` or `SAPOTE_MIBIG_GBK_DIR`, when you omit `--reference`.

## First check: do the pieces tile the reference protein?

A modular type I PKS repeats near-identical modules. In a draft genome it often breaks into many contigs. `tools/pks_piece_map.py` aligns one genome's proteins to each large protein of a reference cluster. The reference is an antiSMASH-annotated MIBiG GenBank file. The tool uses DIAMOND (every alignment segment) and maps each piece of at least 85% identity onto the reference's modules.

```bash
python tools/pks_piece_map.py --reference-gbk BGC0000116.gbk \
  --genome <antiSMASH.zip> --label EXAMPLE --out piece_map_run
```

It writes `PKS_PIECE_MAP.txt` (read this first), `PKS_PROTEIN_CALLS.tsv`, `PKS_PIECES.tsv`, `PKS_PIECE_MAP.tsv`, `PKS_GAPS.tsv`, `PKS_JUNCTIONS.tsv` and `RECEIPT.json`. The output folder must not exist yet.

- `TILED`: the pieces follow reference order, and no two consecutive pieces overlap by more than 10 amino acids, so their order along the gene can be read. It is an order-and-overlap rule only: it has no gap or piece-count requirement, so a single piece, or two pieces with a large uncovered stretch between them, are also `TILED`. It does not show continuous coverage or physical linkage. Read it with the `pieces`, `ref_covered_pct`, `uncovered_gaps` and `largest_gap_aa` columns of `PKS_PROTEIN_CALLS.tsv`. The tool lists every gap in `PKS_GAPS.tsv`, whether it falls at a contig end, and the contigs that carry the end of one reference protein and the start of the next.
- `OVERLAPPING`: the pieces match several places. This is usually module resemblance at lower identity. The order cannot be read from the matches. Use KS placement below.
- `NO_PIECES`: no match reached the identity threshold.

No contigs are joined. Linkage needs long reads or PCR across the breaks.

## Build a KS tree

### Why KS domains

Type I PKS proteins are often multi-module and thousands of amino acids long. Aligning whole proteins can compare different architectures. The antiSMASH module export already gives one translation per domain, so the tree uses KS domains instead. A KS tree shows domain relatedness. It is not an organismal tree.

### Choose one pool

Build one tree per exact antiSMASH KS subtype. Do not mix subtypes.

| Pool | `--subtype` value | Use | Caution |
|---|---|---|---|
| iterative KS | `Iterative-KS` | type II-like or aromatic pathways | check whether the call is a discrete enzyme or an embedded domain |
| modular KS | `Modular-KS` | cis-AT modular PKS | one protein can contribute several tips |
| trans-AT KS | `Trans-AT-KS` | trans-AT pathways | add trans-AT references; do not mix with cis-AT |
| hybrid KS | `Hybrid-KS` | PKS-NRPS and mixed architectures | inspect adjacent domains by hand |

Blank or unknown subtypes stay in a review pool. Do not assign them to a clade by identity alone.

### Prepare the sequences

The manifest is a tab-separated file with one row per strain. `strain_id` and `inventory_csv` are required. The `pks-ks` track also needs `modules_csv`. The other columns (`domains_csv`, `rrefinder_csv`, `ripp_motifs_csv`, `proteins_faa`) serve the RiPP tracks and can be left empty. Relative paths resolve from the manifest's folder.

```text
strain_id	inventory_csv	modules_csv
EXAMPLE_A	pkgA/EXAMPLE_A_2_inventory.csv	pkgA/EXAMPLE_A_3_antismash_modules.csv
EXAMPLE_B	pkgB/EXAMPLE_B_2_inventory.csv	pkgB/EXAMPLE_B_3_antismash_modules.csv
```

`inventory_csv` is the package's BGC inventory file. `modules_csv` is the package's antiSMASH module table for the same strain, the file ending `_3_antismash_modules.csv`. Run `python tools/prepare_biosynthetic_tree_inputs.py --show-options` to list the tracks and filters.

```bash
python tools/prepare_biosynthetic_tree_inputs.py sources.tsv pks_iterative_pool \
  --track pks-ks --subtype Iterative-KS
```

The output folder must be new. Open these files:

- `receipt.json`: source hashes, counts and parameters. Its status is `READY_FOR_ALIGNMENT` when at least four sequences qualify, and `HOLD_TOO_FEW_ELIGIBLE_SEQUENCES` otherwise. Four is a technical floor, not a sign of a good sample.
- `sequence_ledger.tsv`: one row per KS domain, with the source row it came from.
- `exact_sequence_groups.tsv`: identical copies that were kept.
- `sequences.faa`: the alignment-ready sequences.

**Tip names are not full locus identities.** Each tip reads `strain|BGC_alias|locus|domain_id|subtype`. It does not carry the full contig or node and the region. A `MAPPED` row or a `READY_FOR_ALIGNMENT` status does not establish the whole `strain / full node-or-contig / region / BGC alias` identity. Before you use a tip in a figure, join it to the package inventory and keep all four parts plus the locus and domain. If a join fails or conflicts, hold the tip. Do not infer the missing parts from tip order or from the alias. The preparer does not emit this join. The same boundary is described in [the domain-tree contract](DOMAIN_TREE_CONTRACT.md#current-retry-and-output-boundaries).

### Align

| Choice | Command | When |
|---|---|---|
| more accurate | `mafft --localpair --maxiterate 1000 --thread 1 sequences.faa > aligned.faa` | a bounded pool of clearly homologous KS |
| automatic | `mafft --auto --thread 1 sequences.faa > aligned.faa` | a larger exploratory pool |

Review the untrimmed alignment before you trim. If you trim, save the untrimmed file, the command, the tool version, the kept columns and the tip list. Trimming does not validate a doubtful domain call.

### Build the tree

```bash
nice -n 15 iqtree3 -s aligned.faa \
  -m MFP -mset LG,WAG,JTT,Q.pfam -mrate G,I,I+G \
  -B 1000 -alrt 1000 -seed 12345 -T 1 --mem 2G \
  -pre pks_ks_iterative
```

Success is a `.treefile` and a `.contree`, plus a `.iqtree` report and a `.log` that ends with "Total wall-clock time". A `.treefile` alone means the run was interrupted. Keep the alignment, the log and the model-selection report.

Do not reuse an organismal tree's branch lengths or root. Use a verified homologous outgroup if you have one. Otherwise label midpoint rooting as a display choice.

The placement tool below writes its own IQ-TREE command with a smaller model set (`LG,WAG,JTT`) and aligns with MUSCLE. That tree has one job, placing KS on reference modules, so use the commands in its `COMMANDS.txt` as written.

### Choose references

Prefer domain sequences from, in this order:

1. MIBiG clusters with characterized products and explicit domain provenance;
2. antiSMASH KnownClusterBlast or ClusterBlast hits after you map them to the exact BGC;
3. curated Swiss-Prot or reviewed literature sequences;
4. nr or ClusteredNR hits, with the database channel and query coverage kept.

A named-compound reference gives a comparison label. It is not a product call for your BGC.

### Checks before you interpret

- Keep the full four-part identity, locus tag and domain ID for every tip.
- Check the BGC is in the matching inventory.
- Check each sequence is valid amino acids above the minimum length.
- Use one KS subtype per tree.
- Review active-site motifs and long branches.
- Review architecture and synteny before any biological reading.
- Do not collapse duplicates or keep one tip per strain without recording it.

## Placing fragments on a reference module order

In a draft genome, each contig piece of a giant modular PKS hits the same reference clusters almost equally. Shared-reference homology (RG-GMCI, the reference-guided linkage step in [the glossary](GLOSSARY.md)) cannot tell one pathway in many pieces from a web of similar clusters, so it demotes such webs as hubs. A KS tree that includes the reference cluster's own module KS can add candidate placement evidence.

```bash
python tools/ks_module_placement.py inputs --gbk-dir <one isolate's region GBKs> \
  --reference BGC0002357.gbk --out placement_run
# run the two commands in placement_run/COMMANDS.txt (MUSCLE, then IQ-TREE)
python tools/ks_module_placement.py place --tree placement_run/ks_tree.treefile \
  --out placement_run/placement.tsv
```

`inputs` prints the KS count and the two commands to run, and writes `COMMANDS.txt` and `ks_with_references.faa`. `place` writes `placement.tsv`.

- Reference KS are numbered by position (`MIBiG__<accession>_KS<nn>`). They are labelled tips, not a second query genome.
- Each isolate KS gets the smallest well-supported split of the unrooted tree (UFBoot 80 or higher by default) that holds reference KS.

| Call | Meaning |
|---|---|
| `PLACED_ON_REFERENCE_MODULE` | one reference KS, shared with at most one other isolate KS; the module number is reported |
| `MODULE_FAMILY` | one reference KS but more isolate KS; a family of similar modules |
| `AMBIGUOUS_MODULES` | several reference KS fit |
| `UNPLACED` | no supported split holds a reference KS |
| `SUPPORT_UNVERIFIED` | a smaller reference-containing split has missing or unusable support, so placement is held |

- Read placements per contig. Consecutive KS on one contig should land on consecutive modules. A reversed run is what a minus-strand contig gives.
- Choose references the pieces actually hit (KnownClusterBlast) and keep the tip count modest. A 265-tip tree with model selection and 1,000 UFBoot replicates took about 3.5 hours on 4 threads.
- Placement is advisory. It assigns no score, changes no RG-GMCI confidence, and joins nothing. Module order read from a tree is not contig order. KS similarity is not product identity. Use it to decide which demoted RG-GMCI pairs a person should look at.

## Gene by gene against a reference cluster

`tools/gene_synteny_map.py` asks, for each gene of a reference cluster, whether the genome carries a candidate match, at what identity and coverage, and on which contig. It also asks whether neighboring reference genes find neighboring matches on one contig, in the reference's order.

```bash
python tools/gene_synteny_map.py --zip <antiSMASH.zip> --label EXAMPLE \
  --reference BGC0000115.gbk --reference-name "nystatin A1" --out synteny_run \
  [--placement placement_run/placement.tsv]
```

- It writes `gene_synteny.png`, `gene_synteny.tsv` and `gene_synteny_receipt.json`. Open the PNG first. It shows the reference to scale, a heat row of best identity, a contig row and a table.
- Homology comes from DIAMOND, or from `--hits`, a precomputed table whose columns are listed in the tool's docstring.
- Modular PKS genes need KS placement. Their modules resemble one another, so the best whole-gene match goes to whichever contig carries the most modules. With `--placement`, a PKS gene is assigned the contigs whose KS placed on its modules. Without it, PKS matches are drawn hatched and marked "paralogous modules; see KS placement".
- Identity is similarity, not product identity. The figure orders no contigs and joins nothing. A similar cluster is a class-level candidate.

## Missing genes, looked for across the genome

`tools/gap_directed_rescue.py` starts from one core region and a reference cluster. It asks what the reference has that the core lacks, then searches every protein of the genome for those genes, not only those inside antiSMASH regions. The missing part of a split pathway often sits on a short contig that antiSMASH did not flag, because it holds tailoring genes and no core gene.

```bash
python tools/gap_directed_rescue.py --zip <antiSMASH.zip> --label EXAMPLE \
  --core <contig>.region001 --reference BGC0000809.gbk \
  --reference-name "AT2433-A1" --out rescue_run
```

- A missing gene counts as found only when the best match beats the next candidate's bitscore by 20% or more, at 35% identity or above. Families of paralogs (halogenases, glycosyltransferases, methyltransferases) need a clear margin.
- A partner is another contig with two or more clear finds. It is "concentrated" when the two leading partners hold at least 60% of all clear finds. It is a "plausible split" when the core runs to a contig end, the partner is under 30 kb, or its region touches a contig end.
- The reference's own antiSMASH `gene_kind` separates biosynthetic finds from regulators, transporters and flanking housekeeping genes.
- Outputs are `gap_rescue.tsv`, `gap_rescue_partners.tsv`, `gap_rescue_receipt.json` and `gap_rescue.png`. Open the PNG first. The reference sits in the middle and each contig above or below it. Contig ends are heavy bars. Matched genes carry the number of their reference gene.
- Reference genes with a KS domain are drawn hatched and never count toward a partner. Order those with KS placement.
- When several reference genes pick the same genome protein, the row with the highest identity keeps the ribbon. The table keeps the other cross-hits. This is a forward-hit choice. It runs no reverse search and does not show one-to-one orthology.
- Homology comes from DIAMOND, or from `--hits`.
- A partner contig is a candidate missing piece. Nothing is joined. Identity is similarity, not product identity.

### Redraw with a named contig

`--named-contig` adds one undrawn, ambiguous contig to a redraw as review context. It needs `--redraw`, the same genome ZIP and label, the local reference folder, and a new `--out` that does not exist and is not a symlink. Give the contig as `strain / full contig / region / BGC alias`, copied from the source model. For a contig with no antiSMASH region, use `strain / full contig / NO_ANTISMASH_REGION / NO_BGC_ALIAS`. Duplicate, unresolved or already drawn contigs are refused, and so is a contig with no `MISSING_FOUND_AMBIGUOUS` candidate.

The added row is labeled `AMBIGUOUS`. It adds no ribbon, promotes no partner, and changes no gene status or score. The run writes `named_contig_review.json`, which records the selections and the input and output hashes. A redraw rereads saved tables. It does not show which earlier alignment made them, so keep the earlier search receipts. If an input changes mid-run, treat any graphics left behind as incomplete.

### Forward and reverse match records

Rescue and completion records can carry a `reciprocal_provenance` field. Its `forward_winner` part says which reference row won among the forward hits. It does not mean a reverse search ran. Its `reverse_search` part records the state of the reverse check:

| State | Meaning |
|---|---|
| `NOT_NEEDED` | no find outside the core required the check |
| `NOT_RUN` | the database or a prerequisite was unavailable |
| `FAILED` | the selected search returned a failure |
| `RUN` | the search reported success, including an empty result; this is not a match and not proof of absence |
| `UNJUDGED` | the search succeeded, but the reference was not an eligible MIBiG accession |

Keep this record apart from gene statuses, partner verdicts and scores. A record without the field does not show whether a reverse search ran. The older `reciprocal_check` text is separate and can say "not run" when the structured state is `FAILED`.

## Claim ceiling

KS topology can support domain-family relatedness and candidate evolutionary context. It does not establish product identity, pathway completeness, production, activity, novelty, species identity, or horizontal transfer.
