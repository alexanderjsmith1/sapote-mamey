# Figure: Edge-status composition per isolate

- **id:** `fig_edge_status_composition`
- **category:** cohort
- **audience:** manuscript
- **output:** `fig_edge_status_composition.png` (slides, ≥300 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/bgc_inventory.csv`
- **columns used:** strain, boundary
- **row filter:** all BGCs
- **derived fields:** count by (strain, boundary)

## Plot
- **type:** 100%-stacked horizontal bar
- **x:** fraction of BGCs   **y:** strain   **color:** boundary (Interior/Edge/Full-contig)
- **order:** strain rank   **scales:** —

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
Fill every placeholder from the admitted plotted inputs and retain their provenance. Confirm each result-bearing sentence against those inputs; omit or revise any statement that does not hold for this set. For lead tables, state the displayed row count separately from the cohort isolate count.

> Edge-status composition of BGCs per isolate (n = <admitted_isolate_n> isolates). Higher Interior fraction = more complete clusters; full-contig fraction rises with fragmentation.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- —

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
