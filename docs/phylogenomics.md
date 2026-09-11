# Phylogenomics — GToTree, MLSA, ANI, and IQ-TREE companion workflow

**Authority:** read `docs/LLM_COMPANION_TOOL_PROTOCOL.md` first. This workflow is downstream of a
sealed Mamey package and does not change BGC calls or Mamey scores.

## Installation and version policy

The active Bioconda package page is `https://anaconda.org/bioconda/gtotree`. Install into an
isolated environment; do not install into the Mamey core environment:

```bash
conda create -n sapote-phylo -c conda-forge -c bioconda gtotree iqtree fastani ncbi-datasets-cli
conda activate sapote-phylo
GToTree -v
```

The package page currently offers `conda install bioconda::gtotree`; resolve dependencies with the
configured strict channel priority and preserve the exported environment plus the exact resolved
builds. The local workflow was verified with GToTree 1.8.16, but the channel can publish newer
versions. Therefore no LLM may assume 1.8.16 behavior without checking `GToTree -h` for the installed
version. Installation or upgrade needs user approval and network access; using an already installed
environment does not.

## Scientific design used by this project

1. Recover the **whole-genome assembly** from each antiSMASH ZIP. Do not build organismal trees from
   region GBKs.
2. Rank reference candidates using taxonomic proximity plus recurrent ClusterBlast evidence across
   multiple BGCs. ClusterBlast recurrence is a candidate-selection heuristic, not organism identity.
3. Use at most three related reference genomes per focal AS/SID genome. De-replicate identical or
   near-identical assemblies before tree building.
4. Build the broad screen with the six-locus MLSA target set (16S, `atpD`, `gyrB`, `recA`, `rpoB`,
   `trpB`) using the separate MLSA extractor/alignment workflow. GToTree searches predicted proteins,
   so 16S must not be disguised as a GToTree protein HMM. Build a smaller selected 138-SCG
   Actinobacteria GToTree analysis as the high-information overlay.
5. Start around 40 total genomes when the biological panel supports it. Surface 60 as the default
   maximum, with the actual user-selected count recorded. A larger panel requires a new preflight.
6. Use ANI/aligned fraction and locus-level comparisons to investigate duplicate, mislabeled, or
   contaminated assemblies. A tree alone does not resolve those cases.

## Mandatory approval checkpoint

Do not start GToTree until the user has seen and approved:

- focal/reference counts and per-focal reference cap;
- local genomes versus accessions requiring download;
- total assembly bytes and assembly SHA-256 values;
- HMM set name/path, target count, and checksum;
- 6-locus versus 138-SCG plan;
- one core per tree and maximum concurrent cores (never above four);
- expected runtime and work-disk use, labelled measured or estimated;
- exact output root and resume/new-run status.

Reference discovery and downloads are separate from tree execution and require network approval.

## Canonical preparation chain

Use one direction of data flow. Do not apply the older patch families as independent, competing
panel planners:

```text
raw antiSMASH ClusterBlast channel
  -> rank_clusterblast_phylo_candidates.py (candidate evidence only)
  -> curator-approved accession resolution/local genome retrieval
  -> [OPTIONAL cheap wide-net screen — feeds, does not replace, the panel builder:
       build_mlsa.py (5-locus full-pool MLSA; cheap, un-gated, build many)
       -> prune_neighbors_from_tree.py --emit-panel-tsv (<=60-tip bounded panel TSV)]
  -> build_phylo_panel.py (membership, one outgroup, labels, exact-content dedup)
  -> plan_gtotree_iqtree.py --prepared-panel (immutable compute preflight)
  -> explicit user approval
  -> GToTree alignment
  -> content-based alignment discovery
  -> IQ-TREE inference
  -> tree x BGC overlay figure (annotation track only; see TREE_BGC_OVERLAY.md)
```

The optional MLSA screen is a **cheap** front-end, not a competing planner: **MLSA trees are not
compute-heavy — build as many as useful, un-gated.** `prune_neighbors_from_tree.py` emits its result
in the exact `build_phylo_panel.py` manifest columns (`candidate_id, role, source_path,
selection_basis, related_query_ids`; references carry `selection_basis=nearest_neighbour_patristic_MLSA`),
so the screen still flows through the bounded-panel builder and the compute-approval preflight. The
approval gate applies only to the **expensive** GToTree 138-SCG + IQ-TREE step; a wide MLSA screen
does not commit those cores. Execution commands for both tiers are in `GTOTREE_WORKFLOW.md`.

`prepare_biosynthetic_tree_inputs.py` creates independent PKS/RiPP sequence pools. Those gene trees
answer pathway-evolution questions and do not enter the organismal GToTree alignment.

Build the final candidate panel, with 40 total tips by default:

```bash
python tools/build_phylo_panel.py \
  examples/phylo_panel_candidates.template.tsv \
  phylogenomics_workspace/prepared_panels/streptomyces_40_v1 \
  --panel-size 40 --max-related-per-query 3
```

The panel must contain all focal queries, exactly one curator-nominated outgroup, and enough local
reference assemblies to reach the chosen total. A short panel is an error rather than silent scope
drift. The tool accepts a named whole-genome FASTA or GenBank member inside an antiSMASH ZIP and
writes both a human label crosswalk and the separate headerless two-column GToTree `-m` mapping.

Create the non-running compute preflight from that exact prepared panel:

```bash
python tools/plan_gtotree_iqtree.py plan \
  --prepared-panel phylogenomics_workspace/prepared_panels/streptomyces_40_v1 \
  --workspace phylogenomics_workspace \
  --run-id streptomyces_40_138scg_v1 \
  --hmm /absolute/path/to/Actinobacteria.hmm \
  --references-per-query 3 \
  --max-concurrent-cores 4 \
  --gtotree-bin /absolute/path/to/GToTree \
  --iqtree-bin /absolute/path/to/iqtree3
```

The planner derives the 40-tip cap from the panel receipt, re-hashes every staged assembly, and
refuses a conflicting `--panel-cap`. It never runs the tree. See `GTOTREE_PANEL_SELECTION.md`,
`CLUSTERBLAST_PHYLO_CANDIDATES.md`, `GTOTREE_IQTREE_PREFLIGHT.md`, the execution companion
`GTOTREE_WORKFLOW.md` (two-tier MLSA screen + approved core-genome commands), and
`TREE_BGC_OVERLAY.md` (phylogeny × BGC-figure overlay).

## Input and duplicate screening

For each antiSMASH ZIP, locate the genome assembly member, record archive/member hashes and sizes,
and reconstruct a FASTA without changing the source archive. Reject region-only files. Create a
`labels.tsv` mapping so focal tips read, for example, `Streptomyces sp. AS-XXX`.

Before final panel admission:

- compare whole-assembly SHA-256 and normalized-sequence SHA-256;
- run ANI with aligned fraction for suspected duplicates;
- compare 16S and the other retained MLSA loci;
- inspect assembly size/contig count and taxonomic discordance;
- retain one representative of a proven duplicate and record every excluded alias.

Do not merge records solely because they have 100% 16S identity. Do not label contamination without
assembly-level evidence; use `SUSPECT/REQUEST` while it is unresolved.

## GToTree execution

Verify the local interface first:

```bash
GToTree -v
GToTree -h
gtt-hmms
```

In the locally verified GToTree 1.8.16 interface, defaults can exceed the project core limit (`-n`
defaults to 2 and `-M` to 5), so all three controls must be explicit. Re-check these defaults after
any upgrade. Generate the alignment first and infer the final tree in a separate, recorded IQ-TREE
step:

```bash
GToTree \
  -f genomes.txt \
  -H <protein-profile-HMM> \
  -m labels.tsv \
  -j 1 -n 1 -M 1 \
  -N -k \
  -o <run>/gtotree_alignment
```

Use `-B` only after documenting the multicopy-marker tradeoff. It selects a best hit when multiple
hits exist; it is not universally mandatory and can mask contamination/paralogy. Report results
with and without it when the choice changes taxon retention or placement.

Do not use `-F` to overwrite an existing output. Do not assume the alignment is named
`Aligned_SCGs.faa`; discover the emitted alignment in the completed output and record its SHA-256.

The packaged `Actinobacteria.hmm` in GToTree 1.8.16 contains 138 protein profiles; verify the local
count with `grep -c '^NAME' <path>/Actinobacteria.hmm` and record it. A custom GToTree HMM must contain
protein profiles and be versioned and hashed like any other reference resource. Six-locus MLSA that
includes 16S is built separately and cannot be represented as one GToTree protein-HMM target set.

## IQ-TREE execution

Run one IQ-TREE process per approved tree with one thread. A reproducible protein-tree template is:

```bash
iqtree3 \
  -s <observed-alignment-path> \
  -m MFP -mset LG,WAG,JTT,Q.pfam -mrate G,I,I+G \
  -B 1000 -alrt 1000 \
  -T 1 -seed 12345 \
  --prefix <run>/iqtree/final
```

Reconcile options against the installed IQ-TREE help. The restricted model set controls runtime on
long protein supermatrices. Save the exact version, command, seed, selected model, log, `.iqtree`,
`.treefile`, and alignment hash. If multiple one-core trees run simultaneously, the dispatcher must
prove the combined ceiling is no more than four cores.

The GToTree `-T IQ-TREE` shortcut uses its own defaults (`-m MFP -B 1000`) and is not the preferred
publication workflow because it hides parameter control. FastTree is acceptable for a rapid
assessment tree, clearly labelled preliminary; it does not replace the final IQ-TREE inference.

## QA and comparison outputs

Report both input and retained denominators:

- genomes proposed, admitted, excluded, and retained in the final alignment/tree;
- loci/profiles requested and retained per genome;
- missing/multicopy markers and the `-B` decision;
- concatenated alignment length and gap/missingness summaries;
- tree software/model/seed/support settings;
- ANI/aligned-fraction and locus identities for suspected duplicates;
- exact reference accessions, type status when known, and download receipts;
- checksums for inputs, alignments, trees, labels, and figures.

Keep the six-locus and 138-SCG analyses separate. A figure may overlay the smaller 138-SCG topology
or support on the broad MLSA context only when the mapping between common tips is explicit; do not
pretend they are one inferred tree.

## Claim-safe wording

Use: “placed near X within this sampled panel,” “ANI/aligned fraction are consistent with…,” or
“the two assemblies require duplicate/contamination reconciliation.” Avoid “is X,” “new species,”
or “same strain” without the necessary orthogonal evidence and formal taxonomic work.

Phylogeny may be overlaid with BGC counts/classes, but BGC content is an annotation track, not a
character used to infer the organismal tree unless a separate, explicitly described analysis does so.
