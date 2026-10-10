# Definitive BGC prioritization ranker

`tools/definitive_bgc_ranker.py` produces a deterministic **review-prioritization** ranking from the supplied evidence tables. It does not create a scientific-acceptance or product-identification result.

The ranker addresses two common biases in simple BGC rankings. A raw count favors long regions, while a raw hit fraction favors very short regions. The tool therefore combines reciprocal query/reference coverage, a Wilson-stabilized query hit fraction, MIBiG biosynthetic-core completeness, effective sequence similarity, top-versus-second specificity, dominant-reference coherence, orientation-aware gene-order agreement, and explicit boundary penalties.

Output rows print `strain / full node-or-contig / region / BGC alias`, assembled from the first CDS row per BGC alias. Missing components fail closed; row-to-row identity agreement and cross-table membership are not fully verified (see admission limits below).

## Inputs

- One or more package directories (sealing is required by governance but not validated here), supplied with repeatable `--package` arguments or `--packages-root`.
- An explicitly supplied MIBiG GenBank archive through `--mibig-gbk-archive`. Its hash is recorded. The archive is read in place and is not silently downloaded.
- Optionally, a Clear Match Finder output directory through `--clear-match-results`; this adds the top-versus-second specificity channel.
- Optionally, a two-column alias table through `--strain-aliases` with `source_strain,display_strain`.

Example:

```bash
python3 tools/clear_match_finder.py \
  --packages-root /path/to/packages \
  --out /path/to/clear-match

python3 tools/definitive_bgc_ranker.py \
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

- **A — strong pathway-family architecture:** at least four pairs; reciprocal coverage at least 0.60; core completeness at least 0.70; median effective similarity at least 60; rescaled order concordance at least 0.20 when measured (the code also accepts an unbound value); and an Interior boundary.
- **B — supported partial architecture:** at least three pairs; reciprocal coverage at least 0.35; core completeness at least 0.40; median effective similarity at least 45; and rescaled order concordance at least 0.20 when measured (unbound is also accepted).
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

## Current source admission, score and receipt limits

The `manifest.json` requirement is an existence check; the ranker does not parse it or verify sealing and member hashes. It requires exactly one CDS/hit/inventory table; an optional RG-GMCI suffix with zero **or multiple** matches becomes absent. Empty CDS tables and duplicate source strains across packages are refused. Alias-table duplicates overwrite earlier mappings, and different source strains may still collapse to one display strain. Review the alias map before use (`tools/definitive_bgc_ranker.py:81–137,293–338`).

CDS, inventory, hits and RG-GMCI are joined by BGC alias within each package. Identity is taken from the first CDS row of that group; no check proves every row has the same full node, region or strain. Greedy hits are admitted by reference-gene mapping and query name, without a separate check that every query gene belongs to the CDS roster. Validate those joins upstream, retain the exact full locus identity, and hold inconsistent rows. Reference accessions and gene identifiers strip trailing numeric versions; duplicate normalized archive members/IDs overwrite earlier rosters/mappings (`:145–181,221–245`). The archive hash binds bytes, not a unique declared release or absence of identifier collisions.

The order statistic is rescaled: `2 * max(forward,reverse agreement) - 1`, floored at zero. A raw 0.60 orientation agreement maps to 0.20, which is the actual A/B rule threshold. Fewer than three pairs yields an unbound channel, contributing zero score; A/B rule code nevertheless treats `None` as acceptable. Inspect the channel, not just the tier (`:195–218,272–290`). Core weight zero produces completeness zero, not evidence of measured core absence. Missing specificity contributes zero; malformed numeric fields default to zero, and nonfinite/range-invalid numeric inputs are not comprehensively rejected. Unknown/blank boundary receives an eight-point penalty. The standalone score is floored at zero, specificity gaps are clamped into the score fraction, and final ordering is tier, standalone score, review score, full identity (`:384–457`). The label “biological evidence score” is a software field name, not a calibrated biological probability.

`reference_evidence_state` distinguishes `REFERENCE_MATCHED`, `EVALUATED_NO_PAIRS`, `REFERENCE_ROSTER_UNRESOLVED`, and `NO_MIBIG_HITS`. An unresolved roster is not a negative. `COMPLETE_WITH_UNRESOLVED_REFERENCES` is printed in the receipt while the CLI still returns zero (`:375–383,486–516`). Even `COMPLETE` concerns archive-roster resolution, not all evidence gates, profile verification or scientific acceptance.

`SOURCE_HASHES.tsv` binds package table/manifest bytes and archive bytes. It does **not** bind the optional Clear Match input, alias table, source code or all parameters. `RECEIPT.json` hashes only top-level TSVs, not `PER_STRAIN` files or itself. Writes are sequential into a reused directory, can overwrite outputs and may inventory stale top-level TSVs; no all-output transaction or clean-directory guard is provided (`:70–78,293–324,464–496`). Use an unused external output, preserve partial failures, and add the missing input/code/parameter/per-strain/output hashes to the governed inventory. Current50 card verification is a separate gate; ranking does not clear it.

The Clear Match example above is illustrative, not a complete governed admission command. Resolve its required manifest and source prerequisites against [the current Clear Match contract](CLEAR_MATCH_FINDER.md) before any separately authorized run. Retain the selected tool invocation, inputs and output receipts.
