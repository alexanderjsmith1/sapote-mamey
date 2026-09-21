# RG-GMCI complementary-rescue atlas

`tools/rggmci_rescue_atlas.py` is an additive, post-seal review tool. It asks whether two
complete loci match distinct proteins in the same MIBiG comparator and whether those proteins
form coherent reference segments. It does not change the deterministic RG-GMCI result.

## Inputs

- a pair table containing `strain`, `identity_a`, `identity_b`, RG-GMCI confidence, and tiling verdict;
- a locus table keyed by `complete_identity`, with boundary and current product/class context;
- one or more `MIBIG_HITS_EXACT_IDENTITY.tsv` files containing retained per-gene alignments; and
- a locally supplied MIBiG GenBank tar archive for the reference-protein order and denominator.

Every locus must use `strain / full node-or-contig / region / BGC alias`. Missing or malformed
identities stop the build. No network access is used.

## Run

```bash
python tools/rggmci_rescue_atlas.py \
  --pairs review/RGGMCI_LINKED_UNIT_REVIEW.tsv \
  --loci review/ALL_BGC_FUNCTIONAL_LOGIC_WORKUP.tsv \
  --hits-root review/per_strain \
  --mibig references/mibig_gbk.tar.gz \
  --out review/rggmci_rescue_atlas
```

The tool writes a complete candidate ranking, the full pair-by-reference evidence table, a strict
A/B review subset, a Markdown front door, and a JSON receipt. Comparator names remain comparator
labels. Physical joining, exact product identity, pathway completeness, expression, production,
activity, novelty, and scientific acceptance remain unresolved without independent evidence.

## Evidence tiers

- **A** requires high RG-GMCI support, at least three distinct comparator proteins from each locus,
  ten combined proteins, no shared subjects, broad reference coverage, ordered tiling, boundary
  support, and no generic modular caution.
- **B** accepts a smaller but still disjoint, ordered, high-ranked and boundary-supported signal.
- **C** retains plausible complementary pairs for biological review.
- **D** holds shared-reference signals that lack sufficient breadth, specificity, or disjointness.

The numeric score orders evidence within these gates. It is a prioritization score, not a posterior
probability or biological truth value.
