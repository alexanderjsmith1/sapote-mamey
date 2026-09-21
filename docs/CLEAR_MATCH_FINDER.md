# Clear Match Finder

Clear Match Finder ranks every CDS and every BGC in one or more validated Mamey packages by how clearly the best MIBiG protein match separates from the next **distinct MIBiG cluster**.

```bash
python tools/clear_match_finder.py \
  --packages-root runs \
  --out clear_match_results
```

Repeat `--package path/to/package` for an explicit package set. Recursive discovery requires `manifest.json`, `*_cds_table.csv`, and `*_3_mibig_per_gene.csv`; reference and analysis roots are never hardcoded.

If a governed project uses a display strain different from the package's recorded strain, pass `--strain-aliases aliases.csv`. The table must contain `source_strain,display_strain`; aliases are never inferred from directory names.

The default high-clear rule requires:

- top hit at least 70% amino-acid identity;
- top hit at least 80% interpreted query coverage;
- top bit score at least 100;
- a runner-up from a different MIBiG cluster;
- at least a 20-point gap in `identity × coverage / 100`; and
- at least a 1.5-fold top-to-runner-up bit-score ratio.

All thresholds are CLI options. Hits to multiple proteins from the same MIBiG cluster are deduplicated before selecting the runner-up. This prevents a second protein from the same reference cluster from being mistaken for an independent alternative.

Outputs:

- `ALL_MIBIG_HITS_EXACT_IDENTITY.tsv`: every source hit with complete BGC identity;
- `ALL_GENE_TOP_VS_SECOND_MIBIG.tsv`: every CDS, including explicit no-hit rows;
- `ALL_BGC_CLEAR_MATCH_RANK.tsv`: composite all-locus rank, clear-gene-count rank, and an interior-only rank;
- `ALL_BGC_MATCHING_GENE_COUNT_RANK.tsv`: separate count and percentage ranks for genes with any MIBiG match and genes agreeing with the BGC's dominant top MIBiG cluster;
- `ALL_BGC_HIT_FRACTION_RANK.tsv`: the same rows ordered by hit fraction, defined as hit-bearing CDS divided by total BGC CDS;
- `ALL_BGC_TOP_2_GENE_MATCH_RANK.tsv`: BGC rank using only each locus's two strongest hit-bearing genes;
- `ALL_BGC_TOP_3_GENE_MATCH_RANK.tsv`: BGC rank using only each locus's three strongest hit-bearing genes;
- `PER_STRAIN/<strain>/`: the full BGC, matching-gene-count, hit-fraction, top-two, top-three, gene, and raw-hit tables split and re-ranked within each strain;
- `SOURCE_HASHES.tsv`: hashes of every consumed package file; and
- `CLEAR_MATCH_RECEIPT.json`: thresholds, counts, hashes, and the claim ceiling.

The BGC score combines median top-hit quality, the fraction of hit genes that are clear, dominant-reference coherence, median top-versus-second separation, hit coverage across the BGC, and an evidence-breadth adjustment. Edge/full-contig loci and regions with fewer than five CDS receive explicit penalties. Raw component columns remain available so users can re-rank without accepting the composite score.

The full-BGC score is therefore **not an average percent identity**. The top-two and top-three views use a separate, transparent gene score: 60% top-hit `identity × coverage / 100`, 25% top-versus-second effective-similarity separation, and 15% top-to-second bit-score-ratio separation. Their BGC score is the mean of the selected two or three genes. A locus is ranked only when it has the requested number of hit-bearing genes; insufficient loci remain present with a blank rank and an explicit `NO` eligibility field.

The matching-gene-count table provides four parallel ranks. Two rank raw counts and two rank the matching genes as fractions of total BGC CDS. The any-match views include every CDS with at least one recorded MIBiG hit. The dominant-cluster views include CDS whose best hit agrees with the most frequent top MIBiG accession in that BGC. Count and percentage ties use the companion evidence, full-BGC composite, and complete identity. Retaining both count and percentage prevents sparse support such as 4 of 20 genes from being treated as stronger than 18 of 20 merely because another scoring component is high, while preserving the distinct information that absolute gene counts provide.

Clear Match Finder is a sequence-similarity prioritizer. A clear protein match does not establish the exact metabolite, pathway completeness, expression, production, biological activity, novelty, or scientific acceptance.
