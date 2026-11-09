# Definitive BGC prioritization ranker

`tools/definitive_bgc_ranker.py` sorts the BGCs in your packages into review tiers, mostly by how they match a known MIBiG pathway. The tiers are review categories, not one completeness scale: most tiers rest on matched reference genes, but one Tier B route (the linked-fragment candidate) rests on an RG-GMCI pair and can be reached with no admitted reference-gene pair. Read `matched_gene_pairs` and `reference_core_completeness` with the tier. It is a tool for deciding what to review first. It does not identify a product or show that any result is scientifically correct.

The tier and score here are a separate scale from the HIGH, MEDIUM and LOW priority on the triage board. Do not merge the two. Scores are also not comparable with other ranking tools. Terms such as RG-GMCI and KCB are in the [glossary](GLOSSARY.md).

Simple rankings have two biases: a raw gene count favors long regions, and a raw hit fraction favors short ones. This tool scores reciprocal coverage (how much of the region and of the reference pathway matched), a stabilized hit fraction, how many of the reference's core genes matched, sequence similarity, how clearly the top reference beats the second, whether one reference dominates, gene-order agreement, and a penalty for regions cut by a contig edge.

Each output row shows `strain / full node-or-contig / region / BGC alias`, taken from the first CDS row of that BGC alias. A missing component stops the row.

## Inputs

- One or more [validated and sealed package](reader/03_READ_RESULTS.md) folders, given with repeatable `--package` or with `--packages-root`. The tool checks that `manifest.json` exists. It does not parse it or check the seal, so validate first (`python mamey_run.py validate <package>`).
- A MIBiG GenBank archive, given with `--mibig-gbk-archive`. The tool reads it in place, records its hash and never downloads it. Get the MIBiG release from the link in [external data](EXTERNAL_DATA.md). The example below calls the file `mibig_gbk_4.0.tar.gz`.
- Optional: a Clear Match Finder output folder, given with `--clear-match-results`. It adds the top-versus-second channel.
- Optional: a two-column table, given with `--strain-aliases`, with the columns `source_strain,display_strain`.

Each package must hold exactly one CDS table, one MIBiG per-gene hit table and one inventory table. Clear Match Finder needs the same files; see [Clear Match Finder](CLEAR_MATCH_FINDER.md).

## Run it

```bash
python3 tools/clear_match_finder.py \
  --packages-root runs \
  --out clear_match_results

python3 tools/definitive_bgc_ranker.py \
  --packages-root runs \
  --mibig-gbk-archive /path/to/mibig_gbk_4.0.tar.gz \
  --clear-match-results clear_match_results \
  --out definitive_ranking
```

Use a new, empty `--out` folder. Success is exit 0 and the files listed under Outputs. Check `RECEIPT.json` for `COMPLETE_WITH_UNRESOLVED_REFERENCES`, which still exits 0 (see "Reference evidence states").

## How a match is scored

For each candidate MIBiG reference, hit edges are ordered by BLAST bit score, effective similarity, query identifier and reference order. A greedy assignment keeps at most one reference gene per query gene and one query gene per reference gene. The reference chosen is the one with the most matched core weight, then the most matched pairs, then the highest summed bit score.

- Query coverage is matched pairs divided by the query CDS-row count. Reference coverage uses the full MIBiG reference gene count. Their harmonic mean is the reciprocal coverage score. Four matches to a four-gene fragment and four matches to a twenty-gene reference give different reference coverage.
- MIBiG `/gene_kind` sets the core weights: `biosynthetic` counts 3, `biosynthetic-additional` counts 2, other roles count 0. Core completeness is matched core weight divided by total reference core weight.
- Gene order is `2 * max(forward, reverse agreement) - 1`, floored at zero. With fewer than three pairs the order channel is unbound and adds zero.

The standalone evidence score is:

```text
25 * reciprocal coverage
+ 25 * reference core completeness
+ 15 * median effective similarity / 100
+ 10 * min(median top-vs-second gap / 50, 1)
+ 10 * dominant-reference coherence
+ 10 * orientation-aware gene-order concordance
+  5 * Wilson-stabilized query hit fraction
- boundary penalty
```

The boundary penalty is 0 for Interior, 8 for Edge, 12 for Full-contig, and 8 when the boundary is blank or unknown. The score is floored at zero. The Wilson term is a ranking stabilizer, not a confidence interval, because genes are not independent trials.

## Evidence tiers

- **A, strong pathway-family architecture:** at least four pairs; reciprocal coverage at least 0.60; core completeness at least 0.70; median similarity at least 60; order concordance at least 0.20 when measured; Interior boundary.
- **B, supported partial architecture:** at least three pairs; reciprocal coverage at least 0.35; core completeness at least 0.40; median similarity at least 45; order concordance at least 0.20 when measured.
- **B, linked-fragment candidate:** a HIGH RG-GMCI pair of type `COMPLEMENTARY_SPLIT` or `TERMINUS_TRUNCATION_SPLIT`, with each locus still shown as a fragment.
- **C, localized or incomplete match:** at least two pairs or one clear-specific gene, but Tier B is not met.
- **D, weak or diffuse similarity:** an admitted pair remains, and nothing higher is met.
- **U:** no admitted MIBiG match.

The thresholds are engineering choices. They have not been calibrated as probabilities. Tier order is not monotonic in reference completeness: `B_SUPPORTED_LINKED_FRAGMENT_CANDIDATE` sorts above Tier C and D rows that have more matched reference genes, because it comes from the separate RG-GMCI channel. For A and B, an unbound order channel passes the order test, so check the channel and not just the tier.

## RG-GMCI bonus

The RG-GMCI channel stays separate. A HIGH pair with genuine tiling adds 4 points to the review-priority score. A MODERATE pair with genuine tiling adds 2. `OVERLAPPING_PARALOG`, `MIXED_SUBJECT_SIGNAL` and `INSUFFICIENT_SUBJECT_DATA` add nothing. The bonus never changes the standalone score. RG-GMCI shows plausible linkage from homology. It does not show a nucleotide-level join. Long-read closure or boundary-spanning PCR decides that. `RGGMCI_LINKED_UNIT_REVIEW.tsv` keeps both full locus identities and the interpretation guard.

## Outputs

- `ALL_BGC_DEFINITIVE_EVIDENCE_RANK.tsv`: the main table, one row per BGC. Sort on `definitive_rank_all_bgcs`; the order is tier, then standalone score, then review-priority score, then identity. Key columns: `complete_identity`, `evidence_tier`, `standalone_biological_evidence_score_0_100`, `review_priority_score_0_100`, `dominant_mibig_accession`, `dominant_mibig_product`, `reference_evidence_state`, `matched_gene_pairs`, `reciprocal_coverage_f1`, `reference_core_completeness`, `boundary` and `claim_ceiling`. It also has `definitive_rank_within_strain`.
- `ALL_BGC_RECIPROCAL_REFERENCE_METRICS.tsv`, `ALL_BGC_CORE_GENE_EVIDENCE.tsv` and `ALL_BGC_RGGMCI_BOUNDARY_EVIDENCE.tsv`: subsets of those columns by topic.
- `RGGMCI_LINKED_UNIT_REVIEW.tsv`: linked-fragment pairs.
- `TIER_SUMMARY.tsv`: BGC and strain counts per tier.
- `PER_STRAIN/<strain>/DEFINITIVE_EVIDENCE_RANK.tsv` and `RGGMCI_BOUNDARY_EVIDENCE.tsv`.
- `SOURCE_HASHES.tsv` and `RECEIPT.json`.

Every row carries the `claim_ceiling` text: rankings are pathway-family aids. They do not prove products, complete pathways, expression, production, activity, novelty or physical linkage.

## Reference evidence states

`reference_evidence_state` is one of `REFERENCE_MATCHED`, `EVALUATED_NO_PAIRS`, `REFERENCE_ROSTER_UNRESOLVED` and `NO_MIBIG_HITS`. An unresolved roster is not a negative result. `COMPLETE` in the receipt means every required reference has a roster with at least one CDS. A required accession that is absent from the archive, unreadable, or present with zero CDS is listed in `mibig_accessions_unresolved`, and the status is then `COMPLETE_WITH_UNRESOLVED_REFERENCES`. `mibig_rosters_resolved` counts required accessions with a usable roster; `mibig_archive_members_read` counts archive members read, including empty ones. It does not mean any evidence gate or card check passed. Card verification is a separate step.

## Limits

- Identity comes from the first CDS row of each alias group. Nothing checks that every row shares one node, region and strain, or that every query gene is in the CDS roster. Validate those joins upstream and hold inconsistent rows.
- Reference accessions and gene IDs drop trailing version numbers. Duplicate archive members overwrite earlier ones. The archive hash binds bytes, not a stated release.
- Malformed numbers default to zero. Missing specificity adds zero. Core weight zero gives completeness zero, which is not evidence that core genes are absent.
- An empty CDS table or the same source strain in two packages is refused. Duplicate rows in the alias table overwrite earlier ones, and two source strains can map to one display strain. Check the alias map before you run.
- `SOURCE_HASHES.tsv` covers package tables, manifests and the archive. It does not cover the Clear Match input, the alias table, the code or the parameters. `RECEIPT.json` hashes only the top-level TSVs, not `PER_STRAIN` files or itself.
- Writes go in sequence into the output folder and can overwrite files or leave stale TSVs. Use an unused folder, keep partial failures, and record the missing hashes in your own inventory.
- Per-strain folder names replace characters other than letters, digits, dot, underscore and hyphen with an underscore. Two display strains can share a folder and overwrite each other. Dot and dot-dot names are not refused. Keep the folder names unique and keep the map back to the original and display strain IDs.
