# Cluster protein-inventory comparison

Always pass `--metric one_to_one_v1`. The default metric, `legacy_checked`, exists only to reproduce old results. The command compares protein inventories of two or more clusters and draws a descriptive tree:

    python tools/cluster_relate.py --metric one_to_one_v1 \
      --gbk "ExampleA:region_a.gbk" --gbk "ExampleB:region_b.gbk" --outdir OUT --pdf

Give each `--gbk` one cluster GenBank file, normally one antiSMASH region, as `LABEL:path`. Repeat it for each cluster. `--outdir` defaults to `cluster_relate_out`. On success the console prints the cluster count and the output list, and the exit code is 0.

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

The `legacy_checked` default preserves the historical directed best-hit/minimum-
inventory formula for compatibility. It checks both directions before rounding,
requires bounded finite values and matching shared-count/mean-identity details,
and refuses disagreements. It never silently substitutes the named metric.

`tree.nwk` and `dendrogram.png` are built from unrounded distances. `distance_matrix.csv`
shows them rounded to 4 decimals, so two CSV values can look equal when the tree
treats them as different. When two pairs are exactly equally close, UPGMA merges the
pair met first in `--gbk` order. `comparison_contract.json` records both rules
(`distance_precision`, `upgma_tie_policy`).

Outputs are `distance_matrix.csv`, `tree.nwk`, `dendrogram.png`,
`comparison_contract.json`, and optional `comparison.pdf`. The contract records
metric, threshold, engine, inventories and inference ceiling. All destinations
must be fresh. UPGMA is descriptive; it establishes neither orthology nor an
evolutionary outgroup, biological function, compound or activity. Labels must
preserve exact Newick leaf identity through the installed parser; unsupported
quoted spellings and control characters are refused before outputs.

The dendrogram needs SciPy, plotting needs Matplotlib, and alignment needs
Biopython. Install them with `python -m pip install -e '.[figures]'` from the bundle root (see [install](INSTALL.md#3-add-the-features-you-need)). Without SciPy the tool finishes its comparison, then stops with a `ModuleNotFoundError` and writes no outputs.

## Receipt binding and publication limits

The contract JSON records the metric, threshold, requested/effective engine and inventory counts; it does not contain source paths/hashes, output hashes or validated full-locus identities. Preserve a separate path+SHA-256 roster containing strain, full contig/node, region and alias where applicable. Inventory extraction concatenates translated CDS across every GenBank record; untranslated CDS do not enter the denominator. A descriptive comparison of a multi-record file does not establish physical linkage.

The CLI requires at least two inputs. It computes comparisons before checking destination freshness, then stages the complete expected output set with `fresh_output_set`. Existing destinations are refused, and ordinary publication failures trigger ownership-aware rollback. This is not crash-atomic across the flat-file set; interruption may leave a partial set, and staging cleanup failure can return an error after published outputs remain. Inspect the complete output roster and cleanup diagnostics before any retry; do not overwrite or discard prior evidence.

`dendrogram.png` uses a width of `2.2 + 1.2 × number of labels` inches, height 4.2 inches, and 150 dpi. Optional PDF uses Letter pages with an image-width/height cap, not guaranteed aspect-preserving publication layout. There is no SVG output or visual-QA receipt. Zero exit means the requested output set was produced; metric controls and source inspection do not certify rendering or scientific interpretation.
