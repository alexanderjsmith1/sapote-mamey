# Definitive BGC prioritization ranker

`tools/definitive_bgc_ranker.py` produces the bundle's definitive **prioritization** ranking under the currently admitted evidence. It does not create a scientific-acceptance or product-identification result.

The ranker addresses two common biases in simple BGC rankings. A raw count favors long regions, while a raw hit fraction favors very short regions. The tool therefore combines reciprocal query/reference coverage, a Wilson-stabilized query hit fraction, MIBiG biosynthetic-core completeness, effective sequence similarity, top-versus-second specificity, dominant-reference coherence, orientation-aware gene-order agreement, and explicit boundary penalties.

Every output row uses the complete identity `strain / full node-or-contig / region / BGC alias`. Missing identity components fail closed.

## Inputs

- One or more sealed Mamey package directories, supplied with repeatable `--package` arguments or `--packages-root`.
- An explicitly supplied MIBiG GenBank archive through `--mibig-gbk-archive`. Its hash is recorded. The archive is read in place and is not silently downloaded.
- Optionally, a Clear Match Finder output directory through `--clear-match-results`; this adds the top-versus-second specificity channel.
- Optionally, a two-column alias table through `--strain-aliases` with `source_strain,display_strain`.

Example:

```bash
python tools/clear_match_finder.py \
  --packages-root /path/to/packages \
  --out /path/to/clear-match

python tools/definitive_bgc_ranker.py \
  --packages-root /path/to/packages \
  --mibig-gbk-archive /path/to/mibig_gbk_4.0.tar.gz \
  --clear-match-results /path/to/clear-match \
  --out /path/to/definitive-ranking
```

## Reciprocal matching

For each candidate MIBiG reference, hit edges are ordered by BLAST bit score, effective similarity, query identifier, and reference order. A deterministic greedy assignment retains at most one reference CDS for each query CDS and at most one query CDS for each reference CDS. The candidate reference is selected by weighted matched core evidence, then matched-pair count, then summed bit score.

Query coverage is matched pairs divided by query-region CDS count. Reference coverage is matched pairs divided by the complete MIBiG reference CDS count. Their harmonic mean is the reciprocal coverage score. This prevents four matches to a four-gene fragment and four matches to a twenty-gene reference from being treated as complete on both sides.

## Core weighting and scoring

MIBiG `/gene_kind` annotations define the core denominator: `biosynthetic` receives weight 3 and `biosynthetic-additional` receives weight 2. Other roles remain visible but receive no core weight. Core completeness is matched core weight divided by total reference core weight.

The standalone biological evidence score is:

```text
25 * reciprocal coverage F1
+ 25 * reference core completeness
+ 15 * median effective similarity / 100
+ 10 * min(median top-vs-second gap / 50, 1)
+ 10 * dominant-reference coherence
+ 10 * orientation-aware gene-order concordance
+  5 * Wilson-stabilized query hit fraction
- boundary penalty
```

The boundary penalty is 0 for Interior, 8 for Edge, and 12 for Full-contig. Gene-order concordance takes the better of forward and reverse orientation and is unbound when fewer than three pairs exist. An unbound order channel contributes zero rather than presumed agreement. The Wilson statistic is a conservative ranking stabilizer; genes are not independent Bernoulli trials, so it is not interpreted as a biological confidence interval.

## Evidence tiers

- **A — strong pathway-family architecture:** at least four pairs; reciprocal coverage at least 0.60; core completeness at least 0.70; median effective similarity at least 60; measurable order agreement at least 0.60; and an Interior boundary.
- **B — supported partial architecture:** at least three pairs; reciprocal coverage at least 0.35; core completeness at least 0.40; median effective similarity at least 45; and acceptable measurable order agreement.
- **B — supported linked-fragment candidate:** a HIGH RG-GMCI pair with `COMPLEMENTARY_SPLIT` or `TERMINUS_TRUNCATION_SPLIT`, while each locus remains explicitly represented as a fragment.
- **C — localized or incomplete reference match:** at least two pairs or one clear-specific gene, but the Tier B rules are not met.
- **D — weak or diffuse similarity:** an admitted mapped pair remains but higher rules are not met.
- **U — no admitted MIBiG reference match.**

These are rule-based review tiers. Thresholds are transparent engineering choices and have not been calibrated as probabilities on an independent labelled benchmark.

## RG-GMCI channel

RG-GMCI is intentionally separate. Only a HIGH, genuine-tiling pair receives a four-point **review-priority** bonus; a MODERATE, genuine-tiling pair receives two points. `OVERLAPPING_PARALOG`, `MIXED_SUBJECT_SIGNAL`, and `INSUFFICIENT_SUBJECT_DATA` receive no bonus. The RG-GMCI bonus never changes reciprocal coverage, reference-core completeness, or the standalone biological evidence score. `RGGMCI_LINKED_UNIT_REVIEW.tsv` preserves both complete locus identities and the interpretation guard.

RG-GMCI is homology-guided linkage plausibility. It does not establish a nucleotide-level contig join or physical linkage; long-read closure or boundary-spanning PCR remains decisive.

## Outputs

- `ALL_BGC_DEFINITIVE_EVIDENCE_RANK.tsv`
- `ALL_BGC_RECIPROCAL_REFERENCE_METRICS.tsv`
- `ALL_BGC_CORE_GENE_EVIDENCE.tsv`
- `ALL_BGC_RGGMCI_BOUNDARY_EVIDENCE.tsv`
- `RGGMCI_LINKED_UNIT_REVIEW.tsv`
- `TIER_SUMMARY.tsv`
- `PER_STRAIN/<strain>/DEFINITIVE_EVIDENCE_RANK.tsv`
- `PER_STRAIN/<strain>/RGGMCI_BOUNDARY_EVIDENCE.tsv`
- `SOURCE_HASHES.tsv`
- `RECEIPT.json`

All rankings remain pathway-family prioritization aids. They do not prove exact products, complete pathways, expression, production, activity, novelty, physical linkage, or scientific acceptance.
