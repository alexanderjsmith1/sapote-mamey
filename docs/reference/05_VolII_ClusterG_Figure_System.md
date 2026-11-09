# Figure system overview

This page explains how the figure system is built. To make a figure, use [Figures start here](../FIGURES_START_HERE.md).

## Terms used on this page

- **Sealed package:** the finished, validated output folder of a `run`. Figures drawn after the run read from it. This is "post-seal".
- **Sidecar:** the data CSV saved beside a figure image. It holds the exact values plotted.
- **Receipt:** a small file that records which inputs and renderer made a figure.
- **Locus map:** a gene-arrow diagram of one biosynthetic gene cluster (BGC). The current post-seal locus-map route is [Locus map v8](../LOCUS_MAP_V8.md). The older "legacy" route is still selectable.

## Where to start

Pick a figure route in [Figures start here](../FIGURES_START_HERE.md). Compare panel meanings in the [figure catalog](../FIGURE_CATALOG.md). If you already have a sidecar and need its R renderer, use [R figure workflows](../R_FIGURE_WORKFLOWS.md).

Before you regenerate an existing figure, open its data CSV, receipt and caption. Inspect the saved image at its intended size. A missing required figure is an open deliverable item. A skipped or failed figure is not a negative result.

Follow the [figure house rules](../FIGURE_HOUSE_RULES.md) for wording, formats, palettes and provenance. For an individual locus, show strain / full node-or-contig / region / BGC alias. Source details are in [the source-scope reference](06_CURRENT_SOURCE_SCOPE.md).

## Which BGCs are drawn

- **Pure-saccharide BGCs are left out of the brief, extra and lead figures.** A region counts as pure saccharide when `saccharide` is its only specialist signal. A region such as `NRPS;saccharide` is not pure saccharide and is drawn under NRPS. The rule lives in `mamey/figure_policy.py` (`is_pure_saccharide`, `omit_saccharides`), and the brief, extra and lead figures import it. The cohort class heatmap applies a matching rule and parks saccharide-only regions. Left-out clusters can still be discussed in text. One figure draws them on purpose: `fig_saccharide_adjusted` from `tools/build_figures.py` stacks a separate pure-saccharide segment on each strain's specialist BGCs, so the full bar is the raw region count. Its CSV gives `raw_BGC`, `specialist_BGC` and `pure_saccharide` per strain.
- **Raw region counts are not a strain ranking.** Raw counts depend on assembly fragmentation. The workbook figure set (`--figure-set mamey-native`) uses the raw count only as a QC value. `fig_saccharide_adjusted` orders its strains from the highest raw count to the lowest; that is a display order, not a ranking of the strains.

## Where figures come from

- **During a run:** per-strain charts built from the triage rows. A figure that cannot be drawn is reported as skipped. A skip is not a negative result.
- **After the seal:** locus maps, lead bars and the workbook figure set can be redrawn from the sealed package.
- **Across strains:** when you give more than one package, the cohort figures compare them.

Figures that have a data CSV beside the image show the exact plotted values. Open it to check a value. The module list is in the [tools reference](../user_guides/tools_reference.md).
