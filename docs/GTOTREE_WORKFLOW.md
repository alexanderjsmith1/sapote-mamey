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
the nucleotide loci and builds a partitioned IQ-TREE tree. Look for `tree.treefile`,
`loci_report.tsv`, `taxon_map.tsv`, `run_status.json` and `mlsa.log`.
Check which loci and genomes survived: a successful tree can omit missing loci
or a genome with no retained locus. Best-hit selection needs an orthology review.

This is the five-protein-coding-locus route. Keep 16S separate; see
[phylogenomics](phylogenomics.md). The driver uses DNA models, so do not add a
protein model set. [Completion and recovery](COMPANION_RUN_CONTRACTS.md#mlsa-inputs-completion-and-recovery)
explains the output checks and reuse rules.

## Select and check the smaller panel

```bash
python tools/prune_neighbors_from_tree.py reviews/EXAMPLE-mlsa/tree.treefile \
  --genomes-dir inputs/EXAMPLE-panel --emit-panel-tsv reviews/EXAMPLE-candidates.tsv
```

Defaults select up to three nearest references per recognized query and cap the
requested panel at 60 tips. The pruner recognizes AS/AJS prefixes and numbered
SID labels as queries, and `OUTGROUP` in a name as an outgroup. Check those inferred
roles and every genome path before continuing. Fixed query/outgroup tips can
exceed the cap; this step does not enforce exactly one outgroup.

```bash
python tools/build_phylo_panel.py reviews/EXAMPLE-candidates.tsv reviews/EXAMPLE-panel
```

The panel builder defaults to 40 total tips. Choose `--panel-size` only to request
a different total, from 3 through 60. Review the selected members and one outgroup.

For manual edits, `phylo_roster.py` prints tree or panel rows in their current
order. Save edits to a fresh file, check duplicate labels and reprint the result;
row numbers belong to that exact input. For outgroup comparisons,
`mlsa_outgroup_scan.py` compares shared splits after removing outgroup-labeled
tips. Check the actual tree count and shared-tip denominator: its zero exit or
STABLE label can accompany too few informative trees.

## Plan the core-genome tree

Use a writable workspace without spaces for the external tree programs. The
example uses `/tmp/EXAMPLE-phylo`; save completed results before temporary storage
is cleared. Supply the actual selected HMM as `inputs/Actinobacteria.hmm`.

```bash
python tools/plan_gtotree_iqtree.py plan --prepared-panel reviews/EXAMPLE-panel \
  --workspace /tmp/EXAMPLE-phylo --run-id EXAMPLE-core --hmm inputs/Actinobacteria.hmm
```

The defaults request one thread per tree and a maximum four-worker budget.
For the protein alignment, ModelFinder searches protein models
`LG,WAG,JTT,Q.pfam` with rate options `G,I,I+G`.
Read the generated preflight, input hashes, resource estimate and command.
`PLANNED_AWAITING_APPROVAL` is a saved plan. The expensive core-genome alignment
and inference require approval of that plan before execution; follow
[the execution contract](COMPANION_RUN_CONTRACTS.md) and its generated command.
Resolve a hold in a new plan directory so the earlier plan remains available.

GToTree 1.8.19 uses explicit `-j`, `-n` and `-M` controls and `-N` to leave tree
inference to IQ-TREE. The v2 builder omits `-n`; its reviewed resource profile
uses `max(2 * jobs, jobs * MUSCLE threads)`. Version/help probes alone cannot
establish that profile. Keep the executable, HMM and genome hashes with the run.
The [execution gate](GTOTREE_RUNTIME_ADMISSION.md) also checks the resulting tip set.

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
