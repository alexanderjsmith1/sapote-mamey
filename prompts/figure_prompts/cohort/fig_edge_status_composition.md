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
- **x:** fraction of admitted BGC records   **y:** strain   **color:** boundary (Interior/Edge/Full-contig/Unknown; preserve missing labels separately)
- **order:** strain rank   **scales:** —

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, non-interpretive title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
Fill placeholders from the plotted data and drop any sentence the data do not support.

> Boundary-label composition of BGC records per isolate (n = <admitted_isolate_n> isolates). Labels describe source coordinate geometry under the classifier; Interior does not independently establish pathway completeness, and Full-contig is assigned before the circular-origin exemption. Retain Unknown and missing states in the reported denominator.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- —

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
