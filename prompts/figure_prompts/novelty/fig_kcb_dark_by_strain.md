# Figure: KCB-dark (novelty floor) per strain

- **id:** `fig_kcb_dark_by_strain`
- **category:** novelty
- **audience:** manuscript + presentation
- **output:** `fig_kcb_dark_by_strain.png` (slides, ≥200 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/bgc_inventory.csv`
- **columns used:** sid, kcb_top_present (1 = has a KnownClusterBlast top hit; 0 = none)
- **row filter:** all BGCs
- **derived fields:** per strain: % with kcb_top_present == 0

## Plot
- **type:** horizontal bar
- **x:** % BGCs that are KCB-dark   **y:** sid   **color:** single series
- **order:** by % desc   **scales:** linear

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
> Fraction of BGCs with no KnownClusterBlast hit per strain (n = 18). "KCB-dark" is shorthand for BGCs with no known-cluster anchor at all; it is the only strict novelty floor (KCB presence elsewhere is a class anchor, not a known-compound call). Axis/title spell the term out; KCB-dark is the legend shorthand.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- Note that high values track the most fragmented assemblies — say so in the talk, not on the bar.

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
