# Figure: Genome size vs BGC count

- **id:** `fig_genome_size_vs_bgc`
- **category:** cohort
- **audience:** manuscript
- **output:** `fig_genome_size_vs_bgc.png` (slides, ≥300 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/strain_summary.csv`
- **columns used:** assembly_bp, corrected_bgcs, assembly_tier
- **row filter:** all strains
- **derived fields:** —

## Plot
- **type:** scatter
- **x:** assembly_bp (Mb)   **y:** corrected_bgcs   **color:** assembly_tier
- **order:** —   **scales:** linear

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
Fill every placeholder from the admitted plotted inputs and retain their provenance. Confirm each result-bearing sentence against those inputs; omit or revise any statement that does not hold for this set. For lead tables, state the displayed row count separately from the cohort isolate count.

> Corrected BGC count versus genome size (n = <admitted_isolate_n> isolates); colour = assembly tier to show the fragmentation confound.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- If a regression line is wanted, add it downstream; do not imply causation in the figure.

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
