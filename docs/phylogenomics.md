# Phylogenomics: panels, GToTree, MLSA, ANI and IQ-TREE

This page explains how the organismal tree workflow fits together and what to check at each step. The tree work comes after a package exists. It does not change BGC calls or scores. Read the [companion tool protocol](LLM_COMPANION_TOOL_PROTOCOL.md) first. For terms such as BGC, package and ClusterBlast, see the [glossary](GLOSSARY.md). The exact commands for each stage are in the [GToTree workflow](GTOTREE_WORKFLOW.md).

A tree answers "where does this genome sit among the sampled genomes". It is not a species call.

## Set up the tools

Install the tree tools in their own conda environment, not in the environment that runs the engine. The [external tool inventory](EXTERNAL_TOOL_INVENTORY.md) lists the packages (environment `phylo`). Then check:

```bash
conda activate phylo
GToTree -v
iqtree3 --version
python mamey_run.py doctor --companions
```

The production GToTree version is 1.8.19. Version 2.0.x is also accepted and 1.8.16 is refused (see [GToTree workflow](GTOTREE_WORKFLOW.md)). Installing or upgrading needs your approval and network access. Using an installed environment does not.

## The design

1. Take the whole-genome assembly from each antiSMASH ZIP. Do not build organismal trees from region GBKs.
2. Rank reference candidates by taxonomic closeness and by repeated ClusterBlast hits across several BGCs. ClusterBlast recurrence helps pick candidates. It does not show that two genomes are the same organism. Because ClusterBlast hits help choose the panel, a later comparison of BGC trees on that panel is not independent of the choice. Say so when you compare them; see [comparing organismal and biosynthetic trees](SPECIES_VS_BGC_TREE_COMPARISON.md).
3. Use up to three linked reference genomes and up to two type-strain anchors per focal genome, and at most four comparators per focal genome in all. `build_phylo_panel.py` enforces the caps, and `plan_gtotree_iqtree.py` checks them again. Remove identical or near-identical assemblies before building.
4. The six-locus target is 16S, `atpD`, `gyrB`, `recA`, `rpoB` and `trpB`. The shipped `build_mlsa.py` extracts the five protein-coding loci only. It is a screen. A six-locus result needs a separate 16S record and a written alignment and partition procedure.
5. The 138-gene GToTree run uses predicted proteins, so 16S must not be disguised as a GToTree protein HMM. Treat the two analyses as separate.
6. Start around 40 tips when the biological panel supports it. Surface 60 as the default
   maximum, with the actual user-selected count recorded. The panel builder rejects more than 60.
   A larger panel needs a new preflight.
7. These rules are for analysis trees. A publication tree uses at most four references.

## Approval before the expensive step

The core-genome run (GToTree plus IQ-TREE) needs your approval of a saved plan. Do not start GToTree until the plan is approved. With the default `--threads-per-tree 1`, the plan runs GToTree 1.8.19 with `-j 1 -n 1 -M 1` and IQ-TREE with `-T 1`. Before you approve, read the plan for:

- the focal and reference counts, and which genomes are local or must be downloaded;
- the total assembly size and the SHA-256 of each assembly;
- the HMM name, path, target count and checksum;
- the threads, the core budget (four at most) and the expected run time and disk use;
- the output folder, and whether this is a new run or a resume.

`plan_gtotree_iqtree.py plan` writes these into the run folder. Downloads and reference discovery are separate steps and need their own network approval.

## Build the panel

Keep the data flowing in one direction:

```text
raw antiSMASH ClusterBlast channel
  -> rank_clusterblast_phylo_candidates.py (candidate evidence only)
  -> curator-approved accession resolution/local genome retrieval
  -> [OPTIONAL cheap wide-net screen — feeds, does not replace, the panel builder:
       build_mlsa.py (5-locus screen within its watched resource limits)
       -> prune_neighbors_from_tree.py --emit-panel-tsv (<=60-tip bounded panel TSV)]
  -> build_phylo_panel.py (membership, one outgroup, labels, exact-content dedup)
  -> plan_gtotree_iqtree.py --prepared-panel (immutable compute preflight)
  -> explicit user approval
  -> GToTree alignment
  -> content-based alignment discovery
  -> IQ-TREE inference
  -> tree x BGC overlay figure (annotation track only; see TREE_BGC_OVERLAY.md)
```

The MLSA screen is optional and cheap. `build_mlsa.py` has no `--approved` flag. It still runs BLAST, gene prediction, alignment and IQ-TREE, and it uses the threads you give it. It watches memory, disk and time as described in [bounded native workspaces](NATIVE_WORKSPACES.md). Run it only inside your authorized budget. The approval step applies to the 138-gene GToTree and IQ-TREE run.

`prepare_biosynthetic_tree_inputs.py` builds separate PKS and RiPP sequence pools. Those gene trees answer pathway questions. They do not feed the organismal tree.

Build the panel from a candidate table. The template is `examples/phylo_panel_candidates.template.tsv`:

```bash
python tools/build_phylo_panel.py \
  examples/phylo_panel_candidates.template.tsv \
  phylogenomics_workspace/prepared_panels/EXAMPLE_40 \
  --panel-size 40 --max-related-per-query 3
```

The default is 40 tips. The tool rejects more than 60. The panel needs every focal genome, exactly one curator-nominated outgroup, and enough local references to reach the total. A short panel is an error. The output folder must not exist yet. The tool writes a label crosswalk and the headerless two-column mapping that GToTree `-m` reads. Candidate sources and panel options are in [panel selection](GTOTREE_PANEL_SELECTION.md) and [ClusterBlast candidates](CLUSTERBLAST_PHYLO_CANDIDATES.md).

Then make the plan. It does not run any tree:

```bash
python tools/plan_gtotree_iqtree.py plan \
  --prepared-panel phylogenomics_workspace/prepared_panels/EXAMPLE_40 \
  --workspace phylogenomics_workspace \
  --run-id EXAMPLE_40_138scg \
  --hmm /absolute/path/to/Actinobacteria.hmm \
  --references-per-query 3 \
  --max-concurrent-cores 4 \
  --gtotree-bin /absolute/path/to/GToTree \
  --iqtree-bin /absolute/path/to/iqtree3
```

The planner takes the tip cap from the panel receipt and re-hashes every assembly. It refuses a conflicting `--panel-cap`. The run folder holds `RUN_MANIFEST.json`, `RUN_STATE.json` and `COMMAND.sh`. Read the `state` it prints and records. `PLANNED_AWAITING_APPROVAL` (exit 0) means every planner check passed and the plan waits for approval. A `HOLD_…` state (exit 2) names the check that failed: panel cap, duplicate query, outgroup, network inputs, no query, missing tool, tool interface or resource profile. A held plan's `COMMAND.sh` only exits 2. Fix the hold and plan again before you ask for approval. See the [preflight page](GTOTREE_IQTREE_PREFLIGHT.md).

## Run the approved plan

Run the command the plan generated, as `bash COMMAND.sh --approved`, after `RUN_STATE.json` records `approved: true`. Do not type a GToTree or IQ-TREE command by hand: a hand-typed command skips these checks. The generated command is the version-specific one:

- for 1.8.19, it first checks the `--approved` argument, the approval in `RUN_STATE.json`, and the SHA-256 of every staged genome and the HMM against `RUN_MANIFEST.json`. Any failure prints `COMMAND_REFUSED:` and exits 2 before GToTree starts. It then passes `-j`, `-n` and `-M` explicitly. The IQ-TREE line still holds a `<DISCOVERED_ALIGNMENT_PATH>` placeholder for you to replace after `discover`;
- for 2.0.x, it calls `run_planned_tree.py --plan-dir`, which makes the same checks itself. Details are in the [run contracts](COMPANION_RUN_CONTRACTS.md).

For reference, the IQ-TREE step the plan builds looks like this: one process per tree, one thread, a restricted protein model set, 1000 ultrafast bootstraps and 1000 SH-aLRT replicates, with a fixed seed. The IQ-TREE shortcut inside GToTree (`-T IQ-TREE`) hides these settings, so the plan does not use it. FastTree is fine for a quick tree labeled preliminary. It does not replace the final IQ-TREE run.

If several one-core trees run at once, the combined total must stay at four cores or fewer.

## Is the tree complete

A tree build is complete only when all three hold:

- the `.contree` file exists;
- the `.treefile` carries support values;
- the IQ-TREE log (`.log`) contains a "Total wall-clock time" line. The check looks for it on any line, not only the last.

The check reports `INTERRUPTED` or `MISSING` with the reasons it found (`mamey/phylo_evidence.py`). It does not say why a file is absent. A `.treefile` alone, without the other two, is not a finished run. Do not use it; keep the folder and find out what happened.

Then check the alignment. GToTree names it differently across versions, so find the alignment file in the output and record its SHA-256. Do not assume it is called `Aligned_SCGs.faa`. Never use `-F` to overwrite an existing output.

`-B` keeps the best hit when a marker has several. It can hide paralogs or contamination, so document the choice. Report results with and without it when it changes which genomes stay.

## Check inputs and duplicates

For each antiSMASH ZIP, find the assembly file inside, record the archive and member hashes, and rebuild a FASTA without changing the ZIP. Reject region-only files. Write a `labels.tsv` so each focal tip reads like `Streptomyces sp. STRAIN_01`.

Before a genome enters the panel:

- compare whole-assembly SHA-256 and normalized-sequence SHA-256;
- run ANI with aligned fraction on suspected duplicates;
- compare 16S and the other MLSA loci;
- check assembly size, contig count and any taxonomic mismatch;
- keep one copy of a proven duplicate and record every alias you dropped.

Do not merge two records only because their 16S is 100% identical. Do not call an assembly contaminated without assembly-level evidence. Label it `SUSPECT/REQUEST` until it is settled.

## What to report

- genomes proposed, admitted, excluded and kept in the final tree;
- loci or profiles requested and kept per genome, and missing or multicopy markers;
- alignment length and gap summary;
- IQ-TREE version, model, seed and support settings;
- ANI and aligned fraction for suspected duplicates;
- reference accessions, with type status when known;
- checksums for inputs, alignments, trees, labels and figures.

Keep the six-locus and 138-gene analyses apart. A figure may overlay one on the other only if the shared tips are mapped explicitly. They are not one inferred tree.

## Wording

Write "placed near X within this sampled panel", "ANI and aligned fraction are consistent with ...", or "these two assemblies need duplicate or contamination review". Do not write "is X", "new species" or "same strain" without other evidence and formal taxonomy work.

BGC content can be drawn beside the tree as an annotation track. It is not used to infer the tree.
