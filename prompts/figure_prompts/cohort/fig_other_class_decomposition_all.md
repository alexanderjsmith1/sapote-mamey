# Figure: "Other" class decomposition — all categories

- **id:** `fig_other_class_decomposition_all`
- **category:** cohort
- **audience:** presentation
- **output:** `fig_other_class_decomposition_all.png` (slides, ≥300 dpi) + `.svg`/`.pdf` for print

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
Fill every placeholder from the admitted plotted inputs and retain their provenance. Confirm each result-bearing sentence against those inputs; omit or revise any statement that does not hold for this set. For lead tables, state the displayed row count separately from the cohort isolate count.

> Decomposition of the antiSMASH "other" class (n = <admitted_isolate_n> isolates): the <other_tagged_region_n> "other"-tagged BGCs separated into co-labeled and standalone entries (<standalone_other_region_n> standalone). Single-genome rarities highlighted.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- On the slide, point to a specific singleton (e.g. the nucleoside cluster) if that genome is the talk's subject.
- This is exactly the kind of emphasis that belongs on the slide, not in the figure.

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.

Prerequisite derivation: `export_figure_ready.py` does not write other_breakdown.csv. Create and bind the declared derived table before rendering. Group bgc_class_long.csv by the complete strain/contig/region/bgc_id identity; select identities carrying product_class=other, retain all co-label tokens, and classify each selected identity by its sorted non-other token set (empty means standalone other). Count distinct identities as n_bgcs and distinct strain keys as n_strains per category; meets_min_2_strains is n_strains>=2. Declare tier/category display labels separately and report co-label combination categories so counts are not double counted as independent BGCs. Keep the full token audit and source hashes.
