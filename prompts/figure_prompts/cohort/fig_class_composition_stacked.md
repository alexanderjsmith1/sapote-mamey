# Figure: Per isolate class composition (stacked)

- **id:** `fig_class_composition_stacked`
- **category:** cohort
- **audience:** presentation
- **output:** `fig_class_composition_stacked.png` (slides, ≥300 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/class_by_strain.csv`
- **columns used:** strain, product_class, n_bgcs
- **row filter:** collapse rare classes into "other-minor"
- **derived fields:** stack the exported n_bgcs counts by class within strain, normalized by their sum. The exporter explodes every nonempty semicolon-delimited product token; a multi-class region contributes to multiple classes and repeated tokens are not deduplicated. Label the denominator class assignments and retain the full strain/contig/region/bgc_id token audit; this is not a mutually exclusive partition of unique regions.

## Plot
- **type:** 100%-stacked horizontal bar
- **x:** fraction of exported class assignments   **y:** strain   **color:** product_class
- **order:** strain rank   **scales:** —

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, non-interpretive title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
Fill placeholders from the plotted data and drop any sentence the data do not support.

> Relative product-class composition per isolate (n = <admitted_isolate_n> isolates).

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- Legend can be large; consider moving it beside the figure on the slide.

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
