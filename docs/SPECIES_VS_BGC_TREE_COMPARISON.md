# Comparing organismal and biosynthetic trees

<a id="three-independent-evidence-layers"></a>

## Three separate evidence layers

| Layer | Default input | Question answered |
|---|---|---|
| broad context | 16S + five MLSA loci | where should references be sampled? |
| organismal backbone | GToTree Actinobacteria 138-SCG alignment | how are the sampled genomes related across conserved genes? |
| biosynthetic tree/network | family-matched KS, RiPP enzyme/domain, or precursor | how are individual biosynthetic sequence units related? |

Do not concatenate PKS/RiPP sequences into the 138-SCG alignment. Do not graft
branch lengths or support values between trees.

The three layers are separate analyses, not statistically independent evidence. They share
inputs: the biosynthetic tips come from the same sampled genomes as the backbone, and the broad
context layer helps choose which references are sampled. Agreement between layers is therefore
not three independent confirmations. Record the shared genomes, sampling and selection steps, and
claim independent support only where the inputs are actually separate.

## Recommended linked figure

| Figure component | Exact binding |
|---|---|
| Organismal tree tip | Strain and genome assembly identity |
| Biosynthetic tip | `strain / full node-or-contig / region / BGC alias`, plus locus tag and domain ID |
| Link between panels | Exact source-record join from each biosynthetic tip to its strain/genome tip |

A genome can legitimately link to multiple biosynthetic tips. Carry the full
four-part locus identity in the crosswalk and display; do not teach a bare
BGC-alias label as if it were globally unique.

Link color may encode BGC class or family, while
line style can encode provenance: your own isolates, public isolates or references.

## Interpretation ladder

1. **Observed:** a biosynthetic tip occupies a stated supported clade.
2. **Supported comparison:** its placement is congruent or discordant with the
   organismal backbone under the sampled references.
3. **Candidate explanation:** duplication, recombination, differential loss, or
   horizontal transfer could generate discordance.
4. **Not established:** the causal evolutionary mechanism, product identity,
   production, or activity.

Before elevating horizontal transfer, inspect topology support, sampling,
paralogy, gene order, flanking mobility, composition, and assembly boundaries.

## CPU policy

- at most 4 threads per job, one heavy job at a time;
- GToTree 1.8: `-j 1 -n 1 -M 1` per tree; the shared planner/runner command builder omits `-n` for v2.
  Verify the installed interface and the selected governed plan's input, approval and native-resource bindings in
  [companion run contracts](COMPANION_RUN_CONTRACTS.md);
- for commands you run by hand: MAFFT `--thread 1` and IQ-TREE `-T 1 --mem 2G`.
  The tree builders do not apply them as a policy. `phylo_place.py` passes MAFFT
  `--thread <threads>` for its own alignments (`tools/phylo_place.py:389-390,1070`), and no
  shipped tool passes IQ-TREE `--mem`. `build_mlsa.py` aligns with MUSCLE and passes IQ-TREE
  `-T <--threads>` with no `--mem` (`tools/build_mlsa.py:439-441`). The tree planner and
  `run_planned_tree.py` pass `-T`, which defaults to 1 in the runner, and no `--mem`
  (`tools/plan_gtotree_iqtree.py:528`, `tools/run_planned_tree.py:106,461-462`);
- run at reduced priority when other workstation work is active.

The four-core total is a ceiling, not a target.
