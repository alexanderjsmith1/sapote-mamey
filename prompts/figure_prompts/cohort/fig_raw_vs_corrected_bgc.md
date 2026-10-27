# Figure: Raw vs corrected BGC count per isolate

- **id:** `fig_raw_vs_corrected_bgc`
- **category:** cohort
- **audience:** presentation
- **output:** `fig_raw_vs_corrected_bgc.png` (slides, ≥300 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/strain_summary.csv`
- **columns used:** strain, raw_bgcs, corrected_bgcs
- **row filter:** all strains
- **derived fields:** —

## Plot
- **type:** paired horizontal bars (raw outline, corrected filled)
- **x:** BGC count   **y:** strain   **color:** raw=light, corrected=solid
- **order:** by corrected_bgcs desc   **scales:** linear

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, non-interpretive title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
Fill placeholders from the plotted data and drop any sentence the data do not support.

> Raw and boundary-weighted BGC counts per isolate (n = <admitted_isolate_n> isolates). The gap follows the declared weighting policy; Unknown records contribute to raw count but not the weighted sum. It is not a measured number of missing or recoverable clusters. Missing correction values remain uncomputed.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- On the slide, bracket the strains with the largest gap to call out assembly-limited cases.

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
