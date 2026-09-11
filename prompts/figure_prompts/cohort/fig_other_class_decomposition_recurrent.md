# Figure: "Other" decomposition — recurrent only (≥2 strains)

- **id:** `fig_other_class_decomposition_recurrent`
- **category:** cohort
- **audience:** manuscript
- **output:** `fig_other_class_decomposition_recurrent.png` (slides, ≥200 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/other_breakdown.csv`
- **columns used:** co_label_category, n_strains, meets_min_2_strains
- **row filter:** meets_min_2_strains == yes (26 categories)
- **derived fields:** —

## Plot
- **type:** horizontal bar
- **x:** n_strains   **y:** co_label_category   **color:** single series
- **order:** by n_strains desc   **scales:** linear

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
> Recurrent co-label categories within the "other" class (present in ≥2 strains; n = 18).

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- —

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
