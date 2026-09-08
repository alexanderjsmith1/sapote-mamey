# Figure: Per-strain class mix (donut/bar)

- **id:** `fig_per_strain_class_donut`
- **category:** per_strain
- **audience:** presentation
- **output:** `fig_per_strain_class_donut.png` (slides, ≥200 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/bgc_class_long.csv`
- **columns used:** sid, product_class
- **row filter:** sid == <SID>
- **derived fields:** count by product_class

## Plot
- **type:** donut or horizontal bar (prefer bar for >6 classes)
- **x:** n_BGCs   **y:** product_class   **color:** single series
- **order:** by count desc   **scales:** linear

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
> Product-class composition of <SID> (class-level antiSMASH calls).

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- —

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
