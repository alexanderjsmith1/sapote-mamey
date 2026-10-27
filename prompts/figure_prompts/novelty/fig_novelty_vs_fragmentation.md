# Figure: Reported KnownClusterBlast top-hit presence versus assembly contiguity

- **id:** `fig_novelty_vs_fragmentation`
- **category:** novelty
- **audience:** manuscript
- **output:** `fig_novelty_vs_fragmentation.png` (slides, ≥300 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/bgc_inventory.csv + strain_summary.csv`
- **columns used:** strain→n50; kcb_top_present→reported top-hit presence fraction
- **row filter:** all BGCs aggregated per strain
- **derived fields:** join reported top-hit presence fraction to n50

## Plot
- **type:** scatter
- **x:** n50 (log scale)   **y:** % reported top-hit presence   **color:** assembly_tier
- **order:** —   **scales:** log x

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, non-interpretive title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
Fill placeholders from the plotted data and drop any sentence the data do not support.

> Reported KnownClusterBlast top-hit-text presence versus assembly N50 (n = <admitted_isolate_n> isolates). Report search coverage and unknown/unbound cases separately; this association does not establish new chemistry or an assembly-caused novelty effect.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- —

## Build note
The exporter supplies the named CSV fields. `tools/plot_examples.py` does not draw
this recipe; see [renderer choice](../HOW_TO_USE.md#renderer-choice).
