# Figure: Product-class prevalence (banded)

- **id:** `fig_class_prevalence_bar`
- **category:** cohort
- **audience:** manuscript + presentation
- **output:** `fig_class_prevalence_bar.png` (slides, ≥300 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/class_prevalence.csv`
- **columns used:** product_class, n_strains, band
- **row filter:** top 16–20 by n_strains
- **derived fields:** —

## Plot
- **type:** horizontal bar, colored by band
- **x:** n_strains   **y:** product_class   **color:** band (CORE/COMMON/ACCESSORY/UNIQUE)
- **order:** by n_strains desc   **scales:** linear

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, non-interpretive title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
Fill placeholders from the plotted data and drop any sentence the data do not support.

> Product-class prevalence across the cohort (n = <admitted_isolate_n> isolates), banded by how many isolates carry each class. Universal classes are non-discriminating.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- Shade the universal-class rows with a slide rectangle if you want to flag them as excluded.

## Build note
The exporter supplies these fields/bands. `tools/plot_examples.py` draws the
top 16 classes as `fig2_class_prevalence.png` with its own palette; it does not
emit this recipe slug, SVG/PDF companions or a figure receipt. Use the approved
route and retain its actual artifacts, source bindings and visual review.
