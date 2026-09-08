# Figure: Product-class prevalence (banded)

- **id:** `fig_class_prevalence_bar`
- **category:** cohort
- **audience:** manuscript + presentation
- **output:** `fig_class_prevalence_bar.png` (slides, ≥200 dpi) + `.svg`/`.pdf` for print

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
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
> Product-class prevalence across the cohort (n = 18 strains), banded by how many strains carry each class. Universal classes are non-discriminating.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- Shade the universal-class rows with a slide rectangle if you want to flag them as excluded.

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
