# Figure: Class × strain heatmap

- **id:** `fig_class_by_strain_heatmap`
- **category:** cohort
- **audience:** manuscript
- **output:** `fig_class_by_strain_heatmap.png` (slides, ≥200 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/class_by_strain.csv`
- **columns used:** sid, product_class, n_bgcs
- **row filter:** top 20 classes by prevalence
- **derived fields:** pivot class × strain, values = n_bgcs

## Plot
- **type:** heatmap (viridis)
- **x:** sid (strain-rank order)   **y:** product_class   **color:** n_bgcs
- **order:** strain rank; class prevalence   **scales:** —

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
> BGCs per product class and strain (n = 18; top 20 classes). Colour = BGC count.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- Box a strain column or class row on the slide to spotlight a case; never bake it in.

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
