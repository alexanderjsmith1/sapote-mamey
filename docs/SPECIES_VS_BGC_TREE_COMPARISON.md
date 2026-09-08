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

```text
138-SCG organismal tree       PKS/RiPP tree or network
strain A ────────────────┐    A|BGC012|KS.1
strain B ─────────────┐  ├──  A|BGC021|KS.2
strain C ──────────┐  │  └──  B|BGC004|KS.1
reference genomes  │  └─────  MIBiG/reference domains
                   └────────  C|BGC007|KS.1
```

The link key is exact strain+BGC+locus/domain. A genome can legitimately link to
multiple biosynthetic tips. Link color may encode BGC class or family, while
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
- GToTree: `-j 1 -n 1 -M 1` per tree;
- MAFFT: `--thread 1`;
- IQ-TREE: `-T 1 --mem 2G`;
- run at reduced priority when other workstation work is active.

The four-core total is a ceiling, not a target.
