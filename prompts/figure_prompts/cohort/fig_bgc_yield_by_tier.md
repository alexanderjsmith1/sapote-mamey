# Figure: BGC yield by assembly tier

- **id:** `fig_bgc_yield_by_tier`
- **category:** cohort
- **audience:** presentation
- **output:** `fig_bgc_yield_by_tier.png` (slides, ≥300 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/strain_summary.csv`
- **columns used:** assembly_tier, corrected_bgcs
- **row filter:** all strains
- **derived fields:** group by assembly_tier

## Plot
- **type:** box + strip overlay (points jittered)
- **x:** assembly_tier   **y:** corrected_bgcs   **color:** tier palette
- **order:** GOOD, MODERATE, POOR, VERY_POOR, UNKNOWN   **scales:** linear; retain all actual emitted groups

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
Fill every placeholder from the admitted plotted inputs and retain their provenance. Confirm each result-bearing sentence against those inputs; omit or revise any statement that does not hold for this set. For lead tables, state the displayed row count separately from the cohort isolate count.

> Corrected BGC yield by assembly tier (n = <admitted_isolate_n> isolates). Distribution, not a single estimate.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- Add the n per tier as a slide text box rather than on the axis if space is tight.

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
