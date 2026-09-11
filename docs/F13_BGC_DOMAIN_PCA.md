# F13 BGC domain-count PCA source-artwork contract

F13 is a descriptive source-artwork candidate, not a scientific acceptance or a claim about products, sequences, activity, evolution, or phylogeny. It consumes existing `gene_data.json` `domain_arch` records and never infers a missing identity, source version, roster, or assembly decision.

Run the cohort figure command with all of the following inputs:

```text
python -m mamey cohort-figures \
  --runs-dir <runs-dir> \
  --out <output-dir> \
  --f13-cohort-manifest <cohort.json> \
  --f13-cohort-manifest-sha256 <exact-sha256> \
  --f13-denominator-registry <denominators.json> \
  --f13-denominator-registry-sha256 <exact-sha256> \
  --f13-profile SINGLE_COLUMN|DOUBLE_COLUMN
```

The JSON cohort manifest uses `sapote-mamey.figure-cohort-manifest.v1`. Every loaded strain must have one declared row. Only `STUDY` rows with `include_by_default=true` are plotted. `EXTERNAL_BENCHMARK` and `OUTGROUP` rows are default-off by shared policy; an assembly `DEFAULT_OFF` row is also excluded. The output records those exclusions and keeps them out of study denominators.

The independent denominator registry uses `sapote-mamey.cohort-denominator-registry.v1`. Its row for the cohort manifest's `denominator_scope` must exactly match both the number of default-on study strains and the number of source-manifest regions observed for those strains. Both JSON inputs require their own exact SHA-256 digest. Omitting, mismatching, or supplying an ungoverned denominator registry produces `DENOMINATOR_UNGOVERNED` and no new F13 artwork; the command never chooses or repairs a denominator automatically.

For every plotted BGC, the source package must bind `manifest.json`, `gene_data.json`, and exactly one intake file. The package manifest must provide the full identity:

```text
strain / full node-or-contig / region / BGC alias
```

The source-artwork outputs are an SVG with live text, a complete plot-data CSV, caption/methods JSON, separate empty owner-notes JSON, provenance JSON, and a receipt. The SVG is a source-artwork candidate only. A final delivery PDF remains subject to the shared post-embed PDF gate.

If any binding is absent, stale, malformed, duplicate, or incomplete, F13 writes `F13_bgc_domain_pca_2d_HOLD.json` and creates no new F13 artwork.
