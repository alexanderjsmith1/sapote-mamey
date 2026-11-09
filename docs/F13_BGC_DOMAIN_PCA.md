# F13 BGC domain-count PCA source-artwork contract

F13 is the BGC domain-count PCA panel (a principal-component plot of each BGC's domain counts; the panel list is in [the figure catalog](FIGURE_CATALOG.md)). It is a descriptive source-artwork candidate, not a scientific acceptance or a claim about products, sequences, activity, evolution, or phylogeny. It consumes existing `gene_data.json` `domain_arch` records and never infers a missing identity, source version, roster, or assembly decision.

Run the cohort figure command from the bundle root with all of the following inputs. `--f13-profile` is `SINGLE_COLUMN` (the default) or `DOUBLE_COLUMN`; the example uses `DOUBLE_COLUMN`.

```text
python mamey_run.py cohort-figures \
  --runs-dir <runs-dir> \
  --out <output-dir> \
  --f13-cohort-manifest <cohort.json> \
  --f13-cohort-manifest-sha256 <exact-sha256> \
  --f13-denominator-registry <denominators.json> \
  --f13-denominator-registry-sha256 <exact-sha256> \
  --f13-profile DOUBLE_COLUMN
```

The JSON cohort manifest uses `sapote-mamey.figure-cohort-manifest.v1`. Get each digest with `shasum -a 256 <file>`. F13 needs at least two strains in the runs folder, so the minimal pair of files below declares two (`EXAMPLE-1` and `EXAMPLE-2` stand for strains in your runs folder). Replace the region count with the `bgcs` entries you actually loaded.

```json
{"schema_version": "sapote-mamey.figure-cohort-manifest.v1",
 "denominator_scope": "EXAMPLE_SCOPE",
 "rows": [{"identity": "EXAMPLE-1", "role": "STUDY", "include_by_default": true,
           "genus": "Streptomyces", "cohort": "BEE",
           "assembly_state": "PASS", "assembly_reason": "none"},
          {"identity": "EXAMPLE-2", "role": "STUDY", "include_by_default": true,
           "genus": "Streptomyces", "cohort": "BEE",
           "assembly_state": "PASS", "assembly_reason": "none"}]}
```

```json
{"schema_version": "sapote-mamey.cohort-denominator-registry.v1",
 "scopes": [{"scope": "EXAMPLE_SCOPE", "strains": 2, "regions": 21}]}
```

Roles are `STUDY`, `REFERENCE`, `EXTERNAL_BENCHMARK` and `OUTGROUP`. Assembly states are `PASS`, `FLAG`, `DEFAULT_OFF` and `UNRESOLVED`. `cohort` must be one of `BEE`, `WASP`, `ATTINE`, `MOSS`, `REFERENCE`, `EXTERNAL_BENCHMARK` or `UNRESOLVED`. The `regions` count must equal the total number of entries in the `bgcs` list of each plotted strain's package `manifest.json`. F13 also needs at least two eligible BGC rows in total.

Every loaded strain must have one declared row. Only `STUDY` rows with `include_by_default=true` are plotted. `EXTERNAL_BENCHMARK` and `OUTGROUP` rows are default-off by shared policy; an assembly `DEFAULT_OFF` row is also excluded. The output records those exclusions and keeps them out of study denominators.

The independent denominator registry uses `sapote-mamey.cohort-denominator-registry.v1`. Its row for the cohort manifest's `denominator_scope` must exactly match both the number of default-on study strains and the number of source-manifest regions observed for those strains. Both JSON inputs require their own exact SHA-256 digest. Omitting, mismatching, or supplying an ungoverned denominator registry produces `DENOMINATOR_UNGOVERNED` and no new F13 artwork; the command never chooses or repairs a denominator automatically.

For every plotted BGC, the source package must bind `manifest.json`, `gene_data.json`, and exactly one intake file. The package manifest must provide the full identity:

```text
strain / full node-or-contig / region / BGC alias
```

The source-artwork outputs are an SVG with live text, a PNG preview, a plot-data CSV for retained F13 rows, caption/methods JSON, separate empty owner-notes JSON, provenance JSON, and a receipt. The SVG is a source-artwork candidate only. A final delivery PDF remains subject to the shared post-embed PDF gate.

If any binding is absent, malformed, duplicate, or incomplete, F13 writes `F13_bgc_domain_pca_2d_HOLD.json` and creates no new F13 artwork. That includes these cases:

- a manifest BGC with no `domain_arch` row (`F13_DOMAIN_ARCH_BGC_MISSING`), because every manifest BGC counts in the region denominator;
- a domain count that is present but blank or null (`F13_DOMAIN_COUNT_MISSING`).

A domain class that is absent from a BGC's `domain_counts` is a counted zero, because the producer writes only the classes it found. F13 records the SHA-256 of `manifest.json`, `gene_data.json` and the intake file. It does not check that the three files come from the same run, so confirm that from the package yourself.

## Invocation limits, held outputs, and recovery

F13 is invoked by the **multi-strain F-series branch**. A single loaded strain uses the single-strain panels instead, so it makes no F13 attempt and no hold file; G/D-only series do not invoke F13. Supplying F13 flags does not itself guarantee an F13 attempt. Record the loaded roster and series before checking the expected receipt.

`cohort-figures` refuses an existing non-empty output directory before loading packages. Use a fresh directory for each attempt, including a retry after partial output.

F13 status is still separate from overall suite success: the command can exit 0 because other figures were produced while F13 is held. Inspect the current F13 hold or `PASS_SOURCE_ARTWORK_ONLY` receipt, bound inputs and exact expected artifacts rather than an overall PNG count. The internal F13 helper itself writes fixed names without the outer directory admission: a direct invocation can replace outputs or leave preexisting artwork alongside its hold, whose `preexisting_f13_artwork_detected` field lists those files. That internal behavior is not the normal CLI retry contract. Preserve partial outputs and the hold, then use a new candidate path after resolving the cause.
