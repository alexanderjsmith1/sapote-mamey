# Figure: "Other" decomposition — recurrent only (≥2 isolates)

- **id:** `fig_other_class_decomposition_recurrent`
- **category:** cohort
- **audience:** manuscript
- **output:** `fig_other_class_decomposition_recurrent.png` (slides, ≥300 dpi) + `.svg`/`.pdf` for print

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
Fill every placeholder from the admitted plotted inputs and retain their provenance. Confirm each result-bearing sentence against those inputs; omit or revise any statement that does not hold for this set. For lead tables, state the displayed row count separately from the cohort isolate count.

> Recurrent co-label categories within the "other" class (present in ≥2 isolates; n = <admitted_isolate_n> isolates).

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- —

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.

Prerequisite derivation: `export_figure_ready.py` does not write other_breakdown.csv. Create and bind the declared derived table before rendering. Group bgc_class_long.csv by the complete strain/contig/region/bgc_id identity; select identities carrying product_class=other, retain all co-label tokens, and classify each selected identity by its sorted non-other token set (empty means standalone other). Count distinct identities as n_bgcs and distinct strain keys as n_strains per category; meets_min_2_strains is n_strains>=2. Declare tier/category display labels separately and report co-label combination categories so counts are not double counted as independent BGCs. Keep the full token audit and source hashes.
