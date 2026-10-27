# Figure: Genome size vs BGC count

- **id:** `fig_genome_size_vs_bgc`
- **category:** cohort
- **audience:** manuscript
- **output:** `fig_genome_size_vs_bgc.png` (slides, ≥300 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/strain_summary.csv`
- **columns used:** assembly_bp, corrected_bgcs, assembly_tier
- **row filter:** all strains
- **derived fields:** assembly_mb = assembly_bp / 1,000,000; admit finite source-derived values and preserve missingness

## Plot
- **type:** scatter
- **x:** assembly_mb (Mb)   **y:** corrected_bgcs   **color:** assembly_tier
- **order:** —   **scales:** linear

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, non-interpretive title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
Fill placeholders from the plotted data and drop any sentence the data do not support.

> Corrected BGC count versus genome size (n = <admitted_isolate_n> isolates); color = assembly tier to show the fragmentation confound.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- If a regression line is wanted, add it downstream; do not imply causation in the figure.

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
