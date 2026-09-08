# Figure: Novelty floor vs assembly contiguity

- **id:** `fig_novelty_vs_fragmentation`
- **category:** novelty
- **audience:** manuscript
- **output:** `fig_novelty_vs_fragmentation.png` (slides, ≥200 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/bgc_inventory.csv + strain_summary.csv`
- **columns used:** sid→n50; kcb_top_present→%dark
- **row filter:** all BGCs aggregated per strain
- **derived fields:** join %KCB-dark to n50

## Plot
- **type:** scatter
- **x:** n50 (log scale)   **y:** % KCB-dark   **color:** assembly_grade
- **order:** —   **scales:** log x

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
> Per-strain KCB-dark fraction versus assembly N50 (n = 18). Apparent novelty is partly a fragmentation artifact — interpret jointly.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- —

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
