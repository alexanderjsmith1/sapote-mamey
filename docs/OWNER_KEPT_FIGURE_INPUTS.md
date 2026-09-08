# Owner-kept Figure Factory inputs

`tools/build_owner_kept_figure_inputs.py` prepares current, source-bound data for the nine
legacy Figure Factory designs retained by scientific-owner review. It does **not** render or
accept a figure. The adapter exists so a growing strain collection can be reprojected once,
then reviewed or plotted without re-authoring the old July tables.

## Required sequence

1. Build current widget data from the intended sealed-package cohort.
2. Run `codex-figure-sources` against those exact package ZIPs. The source bundle now includes
   `STRAIN_CONTEXT.csv`, `DOMAIN_CATEGORY_COUNTS.csv`, `CASSETTE_FAMILY_COUNTS.csv`, and
   `RESISTANCE_FAMILY_COUNTS.csv`, derived from each sealed
   `Project_Memory_Snapshot.json`. Missing snapshots remain typed missingness.
3. Build the owner-kept input projection:

```bash
python tools/build_owner_kept_figure_inputs.py \
  --widget-data AS_All_Strains_Widget_Data.json \
  --source-bundle FIGURE_SOURCE_BUNDLE \
  --outdir OWNER_KEPT_INPUTS
```

The output directory must not already exist. Source receipt hashes and the widget-data hash
must match before any output is written.

## Output tables

- `domain_counts.csv` — strain × source-derived domain category; used by F03a–F03c.
- `class_by_strain.csv` — strain × antiSMASH product-class membership count; used by
  F04f, F04g, and F09a.
- `cassette_types.csv` — strain × current cassette-registry family; used by F05a.
- `resistance_families.csv` — strain × current resistance-scan family; used by F06d.
- `strain_context.csv` — governance, host group, cohort role, denominator membership,
  taxonomy/genus, genome size, corrected-BGC count, assembly tier, and snapshot state.
- `genus_selection.tsv` — an editable downstream plotting surface. It does not infer taxonomic
  scope. Owners may exclude or add comparison genera without changing extraction code.
- `FIGURE_REBUILD_READINESS.tsv` — one row for each of F03a, F03b, F03c, F04f, F04g,
  F05a, F06d, F09a, and F09e.
- `FIGURE_INPUT_RECEIPT.json` — exact source hashes, row counts, study denominator, benchmark
  selection, and readiness holds.

## Denominators and external benchmarks

Records typed `EXTERNAL_BENCHMARK` must declare `include_by_default=false`. They remain absent
unless their exact identifier is selected with a repeated `--external-benchmark` option. A
selected external benchmark is available for a sensitivity/comparison panel but never enters
the study denominator or study percentages. Unrecognized selections and default-on benchmarks
fail before output creation.

Genus-aware interpretation is required whenever ecological groups contain different genus
mixtures. The adapter therefore carries genus on every selected strain and holds F03b, F03c,
F04f, F04g, F06d, F09a, and F09e if a study strain lacks genus. It does not infer genus from
strain identifiers or host labels.

## Interpretation boundary

Domain, cassette, resistance-family, and product-class values are annotation-derived genomic
capacity summaries. They are not expression, metabolite production, activity, product identity,
novelty, or causal ecological adaptation. Corrected BGCs per Mbp are an assembly-aware inventory
projection, not a rate of metabolite production. Caption construction and scientific comparison
remain separate downstream steps.

