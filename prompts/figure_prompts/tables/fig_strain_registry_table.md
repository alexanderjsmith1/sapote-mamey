# Figure: Strain registry table (slide-ready)

- **id:** `fig_strain_registry_table`
- **category:** tables
- **audience:** presentation
- **output:** `fig_strain_registry_table.png` (slides, ≥300 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/strain_summary.csv`
- **columns used:** strain, taxonomy, assembly_tier, contigs, n50, raw_bgcs, corrected_bgcs
- **row filter:** all strains
- **derived fields:** —

## Plot
- **type:** formatted table (zebra rows, tier-colored grade cell)
- **x:** —   **y:** —   **color:** grade cell
- **order:** by corrected_bgcs desc   **scales:** —

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, non-interpretive title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
Fill placeholders from the plotted data and drop any sentence the data do not support.

> Isolate registry: assembly metrics and BGC counts (n = <admitted_isolate_n> isolates).

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- Keep to ≤12 rows per slide; split if more.

## Build note
The exporter supplies the named CSV fields. `tools/plot_examples.py` does not draw
this recipe; see [renderer choice](../HOW_TO_USE.md#renderer-choice).
