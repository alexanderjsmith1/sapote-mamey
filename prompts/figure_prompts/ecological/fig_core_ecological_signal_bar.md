# Figure: Core ecological signal (iron + osmolyte)

- **id:** `fig_core_ecological_signal_bar`
- **category:** ecological
- **audience:** presentation
- **output:** `fig_core_ecological_signal_bar.png` (slides, ≥200 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/class_prevalence.csv`
- **columns used:** product_class, n_strains
- **row filter:** product_class in {ectoine, NI-siderophore, NRP-metallophore}
- **derived fields:** —

## Plot
- **type:** horizontal bar
- **x:** n_strains   **y:** product_class   **color:** single series
- **order:** by n_strains desc   **scales:** linear

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
> Near-core osmolyte (ectoine) and iron-acquisition (siderophore/metallophore) classes across the cohort (n = 18); presence/absence over conserved classes, not an assay.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- —

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
