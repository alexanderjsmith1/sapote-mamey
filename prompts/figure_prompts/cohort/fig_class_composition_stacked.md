# Figure: Per isolate class composition (stacked)

- **id:** `fig_class_composition_stacked`
- **category:** cohort
- **audience:** presentation
- **output:** `fig_class_composition_stacked.png` (slides, ≥300 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/class_by_strain.csv`
- **columns used:** strain, product_class, n_bgcs
- **row filter:** collapse rare classes into "other-minor"
- **derived fields:** stack n_bgcs by class within strain

## Plot
- **type:** 100%-stacked horizontal bar
- **x:** fraction of BGCs   **y:** strain   **color:** product_class
- **order:** strain rank   **scales:** —

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
Fill every placeholder from the admitted plotted inputs and retain their provenance. Confirm each result-bearing sentence against those inputs; omit or revise any statement that does not hold for this set. For lead tables, state the displayed row count separately from the cohort isolate count.

> Relative product-class composition per isolate (n = <admitted_isolate_n> isolates).

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- Legend can be large; consider moving it beside the figure on the slide.

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
