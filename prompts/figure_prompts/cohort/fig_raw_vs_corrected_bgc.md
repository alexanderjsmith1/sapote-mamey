# Figure: Raw vs corrected BGC count per strain

- **id:** `fig_raw_vs_corrected_bgc`
- **category:** cohort
- **audience:** presentation
- **output:** `fig_raw_vs_corrected_bgc.png` (slides, ≥200 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/strain_summary.csv`
- **columns used:** sid, raw_bgcs, corrected_bgcs
- **row filter:** all strains
- **derived fields:** —

## Plot
- **type:** paired horizontal bars (raw outline, corrected filled)
- **x:** BGC count   **y:** sid   **color:** raw=light, corrected=solid
- **order:** by corrected_bgcs desc   **scales:** linear

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
> Raw vs corrected BGC counts per strain (n = 18). The gap is the fragmentation discount.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- On the slide, bracket the strains with the largest gap to call out assembly-limited cases.

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
