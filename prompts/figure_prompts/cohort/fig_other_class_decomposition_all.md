# Figure: "Other" class decomposition — all categories

- **id:** `fig_other_class_decomposition_all`
- **category:** cohort
- **audience:** presentation
- **output:** `fig_other_class_decomposition_all.png` (slides, ≥200 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/other_breakdown.csv`
- **columns used:** co_label_category, n_strains, n_bgcs, tier
- **row filter:** all 40 categories
- **derived fields:** —

## Plot
- **type:** horizontal bar; singletons in highlight color
- **x:** n_strains   **y:** co_label_category   **color:** tier (RECURRENT blue / SINGLETON orange)
- **order:** by n_strains asc (rare tail at bottom)   **scales:** linear

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
> Decomposition of the antiSMASH "other" class (n = 18): the 211 "other"-tagged BGCs re-attributed to their co-labels (none were standalone). Single-genome rarities highlighted.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- On the slide, point to a specific singleton (e.g. the nucleoside cluster) if that genome is the talk's subject.
- This is exactly the kind of emphasis that belongs on the slide, not in the figure.

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
