# Cluster protein-inventory comparison

Use the declared `one_to_one_v1` metric for a bounded, symmetric inventory comparison:

    python tools/cluster_relate.py --metric one_to_one_v1 \
      --gbk "FixtureA:fixture_a.gbk" --gbk "FixtureB:fixture_b.gbk" --outdir OUT --pdf

The metric globally aligns every cross-inventory protein pair using Bio.Align,
BLOSUM62 and gap penalties -11/-1. It excludes identities below `--min-id` (default
30 percent), then maximizes the sum of identity/100 under one-to-one matching.
Similarity equals this sum divided by the larger translated-CDS inventory;
distance equals 1 minus similarity. Unmatched copies contribute zero, and every
copy remains in the denominator. Sequence sorting, canonical whole-inventory orientation and canonical pair orientation
make input and gene-order permutations preserve the result, including alignment
tie behavior. Equal-weight assignments can differ in member identities while
preserving the same score; no ortholog assignment is emitted. Empty inventories
are unmeasured and refused. Identities must be finite percentages.

`--engine pyswrd` with this metric still performs exhaustive Bio.Align global
alignment: a prefilter would change the admitted edge set. The requested and
effective engine are recorded separately. This can be slower than a prefilter.

The default `legacy_checked` preserves the historical directed best-hit/minimum-
inventory formula for compatibility. It checks both directions before rounding,
requires bounded finite values and matching shared-count/mean-identity details,
and refuses disagreements. It never silently substitutes the named metric.

Outputs are `distance_matrix.csv`, `tree.nwk`, `dendrogram.png`,
`comparison_contract.json`, and optional `comparison.pdf`. The contract records
metric, threshold, engine, inventories and inference ceiling. All destinations
must be fresh. UPGMA is descriptive; it establishes neither orthology nor an
evolutionary outgroup, biological function, compound or activity. Labels must
preserve exact Newick leaf identity through the installed parser; unsupported
quoted spellings and control characters are refused before outputs.

The dendrogram needs SciPy, plotting needs Matplotlib, and alignment needs
Biopython. Tests check the assignment against an independent exhaustive oracle,
copy-count behavior, symmetry, bounds, engine route and legacy refusals. These
controls verify the declared computation, not a biological interpretation.
