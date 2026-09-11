# Figure: Edge-status composition per strain

- **id:** `fig_edge_status_composition`
- **category:** cohort
- **audience:** manuscript
- **output:** `fig_edge_status_composition.png` (slides, ≥200 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/bgc_inventory.csv`
- **columns used:** sid, edge_status
- **row filter:** all BGCs
- **derived fields:** count by (sid, edge_status)

## Plot
- **type:** 100%-stacked horizontal bar
- **x:** fraction of BGCs   **y:** sid   **color:** edge_status (Interior/Edge/Full-contig)
- **order:** strain rank   **scales:** —

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
> Edge-status composition of BGCs per strain (n = 18). Higher Interior fraction = more complete clusters; full-contig fraction rises with fragmentation.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- —

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
