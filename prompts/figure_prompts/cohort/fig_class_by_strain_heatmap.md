# Figure: Class × isolate heatmap

- **id:** `fig_class_by_strain_heatmap`
- **category:** cohort
- **audience:** manuscript
- **output:** `fig_class_by_strain_heatmap.png` (slides, ≥300 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/class_by_strain.csv`
- **columns used:** strain, product_class, n_bgcs
- **row filter:** top 20 classes by prevalence
- **derived fields:** pivot class × strain, values = n_bgcs. The exporter emits observed class rows; the example fills absent pairs with zero. Confirm complete admitted isolate/class coverage before interpreting such a fill as observed absence, and retain unavailable inputs separately.

## Plot
- **type:** heatmap (viridis)
- **x:** strain (strain-rank order)   **y:** product_class   **color:** n_bgcs
- **order:** strain rank; class prevalence   **scales:** —

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, non-interpretive title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
Fill placeholders from the plotted data and drop any sentence the data do not support.

> BGCs per product class and isolate (n = <admitted_isolate_n> isolates; top 20 classes). Colour = BGC count.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- Box a strain column or class row on the slide to spotlight a case; never bake it in.

## Build note
The exporter supplies these fields. `tools/plot_examples.py` draws a related
raw-count top-20 heatmap as `fig3_class_by_strain_heatmap.png`; it does not emit
this recipe slug, SVG/PDF companions or a figure receipt. Use the approved route
and retain its actual artifacts, source bindings and visual review.
