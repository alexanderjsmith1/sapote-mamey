# Build a genome-marker tree

Use this workflow to compare EXAMPLE with a selected panel of genomes. You need
genome FASTA files, a chosen outgroup, the marker HMM and the tree programs.
The first stage makes a five-locus screen; the second plans a core-genome tree.
Run the Python commands from the bundle directory in your activated environment.

## Check the tools

```bash
python mamey_run.py doctor --companions
```

The MLSA screen uses Prodigal, BLAST+, MUSCLE and IQ-TREE. The core-genome stage
also needs GToTree and its selected HMM. See [external tools](EXTERNAL_TOOL_INVENTORY.md)
for installation and [external data](EXTERNAL_ASSETS_GUIDE.md) for the marker files.

The adapter in `tools/_gtotree_versions.py` accepts GToTree `1.8.19` and selected `2.0.x` interfaces.
The 1.8.19 route has priority; the experimental v2 route requires the separate
[runtime checks](GTOTREE_RUNTIME_ADMISSION.md). A missing tool or unsupported
interface stops planning before analysis.

## Screen the panel with MLSA

Put the selected genomes in `inputs/EXAMPLE-panel/` as immediate `.fna` files.
Use a fresh result directory. This example chooses four threads to bound the
external programs:

```bash
python tools/build_mlsa.py inputs/EXAMPLE-panel reviews/EXAMPLE-mlsa --threads 4
```

The driver selects coding sequences for atpD, gyrB, recA, rpoB and trpB, aligns
the nucleotide loci and builds a partitioned IQ-TREE tree. Success has four parts:

- the command exits 0 and its last screen line is `build_mlsa: outputs -> <out>/tree.treefile`;
- `run_status.json` reads `COMPLETE`;
- `RESOURCE_ATTEMPT/<attempt-id>/SUCCEEDED.json` exists;
- `tree.treefile`, `loci_report.tsv`, `taxon_map.tsv` and `mlsa.log` are in the output folder.

The `TREE_OK` line is written by the worker, not shown on screen. Find it in `mlsa.log` and in
`RESOURCE_ATTEMPT/<attempt-id>/worker.log`. Exit 6 with a `FAILED.json` in the attempt folder means
the run failed, whatever files are present. A `tree.treefile` alone does not tell you whether the run
finished, so go by the exit code and these files.
Check which loci and genomes survived: a successful tree can omit missing loci
or a genome with no retained locus. Best-hit selection needs an orthology review.

This is the five-protein-coding-locus route. Keep 16S separate; see
[phylogenomics](phylogenomics.md). The driver uses DNA models, so do not add a
protein model set. [Completion and recovery](COMPANION_RUN_CONTRACTS.md#mlsa-inputs-completion-and-recovery)
explains the output checks and reuse rules.

## Select and check the smaller panel

Give `--genomes-dir` as an absolute path. The tool writes each genome's path into the
candidate file as given, and the panel builder reads a relative path from the candidate
file's own folder, not from where you run the command. Run this from the bundle directory:

```bash
python tools/prune_neighbors_from_tree.py reviews/EXAMPLE-mlsa/tree.treefile \
  --genomes-dir "$PWD/inputs/EXAMPLE-panel" --emit-panel-tsv reviews/EXAMPLE-candidates.tsv
```

It prints a line such as `queries=1 refs_kept=3 outgroups=1 -> panel = 5 tips`. Note the tip count.

Defaults select up to three nearest references per recognized query and cap the
requested panel at 60 tips. The pruner treats a tip as a query only if its label starts with `AS-`, `AS_`, `AJS-`, `AJS_`
or `SID`, followed by digits (case ignored). It treats a tip as an outgroup if `OUTGROUP` is in
its name. There is no flag to change this. A query label that does not match is treated as a
reference, so rename your query genomes to match before the MLSA step. If no label matches, the
line above reads `queries=0` and the panel holds only the outgroup. Check those inferred
roles and every genome path before continuing. Fixed query/outgroup tips can
exceed the cap; this step does not enforce exactly one outgroup.

```bash
python tools/build_phylo_panel.py reviews/EXAMPLE-candidates.tsv reviews/EXAMPLE-panel \
  --panel-size 5
```

Replace `5` with the tip count the pruner printed. The panel builder defaults to 40 total
tips and stops with `eligible unique candidates fill 5/40 tips` if the candidates cannot fill
that many. The size must be from 3 through 60. The output folder must not exist yet. Review
the selected members and one outgroup.

To edit a roster by hand, print it with
`python tools/phylo_roster.py --panel reviews/EXAMPLE-candidates.tsv`, then drop rows with
`--remove 3,7 --out reviews/EXAMPLE-edited.tsv`. Row numbers belong to that exact input.
Save to a fresh file and print it again. To test whether the root choice changes the tree,
run `python tools/mlsa_outgroup_scan.py --trees A.treefile B.treefile`. It compares shared
splits after removing outgroup-labeled tips. Check the tree count and shared-tip count:
a zero exit or a STABLE label can accompany too few informative trees.

## Plan the core-genome tree

Use a writable workspace without spaces for the external tree programs. The
example uses `/tmp/EXAMPLE-phylo`; save completed results before temporary storage
is cleared. The HMM is the GToTree marker file for the Actinobacteria 138-gene set, here named `Actinobacteria.hmm`.
This bundle does not ship it. Take the file from your GToTree installation's HMM data, or
download it from the GToTree project; [external data](EXTERNAL_ASSETS_GUIDE.md) does not cover it,
and [phylogenomics](phylogenomics.md) shows the `--hmm` argument. Copy it to
`inputs/Actinobacteria.hmm` or point `--hmm` at its real path.

```bash
python tools/plan_gtotree_iqtree.py plan --prepared-panel reviews/EXAMPLE-panel \
  --workspace /tmp/EXAMPLE-phylo --run-id EXAMPLE-core --hmm inputs/Actinobacteria.hmm
```

The defaults request one thread per tree and a maximum four-worker budget.
For the protein alignment, ModelFinder searches protein models
`LG,WAG,JTT,Q.pfam` with rate options `G,I,I+G`.
The plan's state file, `RUN_STATE.json`, starts as `PLANNED_AWAITING_APPROVAL`, or as a hold such
as `HOLD_TOOL_MISSING` when a program is not installed. Read the generated preflight, input hashes, resource estimate and command.
`PLANNED_AWAITING_APPROVAL` is a saved plan. The expensive core-genome alignment
and inference require approval of that plan before execution; follow
[the execution contract](COMPANION_RUN_CONTRACTS.md) and its generated command.
Resolve a hold in a new plan directory so the earlier plan remains available.

GToTree 1.8.19 uses explicit `-j`, `-n` and `-M` controls and `-N` to leave tree
inference to IQ-TREE. Resource rules for the v2 route are in the
[execution gate](GTOTREE_RUNTIME_ADMISSION.md), which also checks the resulting tip set.
Keep the executable, HMM and genome hashes with the run.

## Read the completed tree

Compare the expected and retained tips, per-genome marker completeness/redundancy,
alignment, selected model and inference logs. Investigate unexpected long branches
with the underlying sequences and assembly records.

`signoff_check.py` is an advisory label check and always exits zero; read its
findings. ANI comparisons need the exact assemblies, comparison direction and
aligned fraction. A missing ANI row needs investigation, not a zero value.

For the tree beside BGC data, use the [tree/BGC overlay](TREE_BGC_OVERLAY.md) with
an explicit tip-to-strain crosswalk. BGC data annotate the organismal tree; they
are not inputs to its inference. Report the panel and assembly limitations with
the result, and cite the versions of the tools actually used.
