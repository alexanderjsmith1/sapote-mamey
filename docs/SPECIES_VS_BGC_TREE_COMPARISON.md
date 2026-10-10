# Comparing organismal and biosynthetic trees

## Three independent evidence layers

| Layer | Default input | Question answered |
|---|---|---|
| broad context | 16S + five MLSA loci | where should references be sampled? |
| organismal backbone | GToTree Actinobacteria 138-SCG alignment | how are the sampled genomes related across conserved genes? |
| biosynthetic tree/network | family-matched KS, RiPP enzyme/domain, or precursor | how are individual biosynthetic sequence units related? |

Do not concatenate PKS/RiPP sequences into the 138-SCG alignment. Do not graft
branch lengths or support values between trees.

## Recommended linked figure

| Figure component | Exact binding |
|---|---|
| Organismal tree tip | Bound strain and genome assembly identity |
| Biosynthetic tip | `strain / full node-or-contig / region / BGC alias`, plus locus tag and domain ID |
| Link between panels | Exact source-record join from each biosynthetic tip to its strain/genome tip |

A genome can legitimately link to multiple biosynthetic tips. Carry the full
four-part locus identity in the crosswalk and display; do not teach a bare
BGC-alias label as if it were globally unique.

The link key retains the full four-part BGC identity plus locus/domain. Link color may encode BGC class or family, while
line style can encode AS, SID, or reference provenance.

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

- one alignment/tree pipeline uses one core;
- at most four independent pipelines may run concurrently;
- GToTree 1.8: `-j 1 -n 1 -M 1` per tree; the v2 runner omits `-n`.
  Verify the installed interface and the planner compatibility hold in
  [companion run contracts](COMPANION_RUN_CONTRACTS.md);
- MAFFT: `--thread 1`;
- IQ-TREE: `-T 1 --mem 2G`;
- run at reduced priority when other workstation work is active.

The four-core total is a ceiling, not a target.
