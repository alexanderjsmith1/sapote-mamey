# Figure: Fragmentation-loss gradient

- **id:** `fig_fragmentation_loss_gradient`
- **category:** cohort
- **audience:** manuscript + presentation
- **output:** `fig_fragmentation_loss_gradient.png` (slides, ≥300 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/strain_summary.csv`
- **columns used:** n50, fragmentation_loss, assembly_tier
- **row filter:** all strains
- **derived fields:** —

## Plot
- **type:** scatter
- **x:** n50 (log scale)   **y:** fragmentation_loss (raw − corrected)   **color:** assembly_tier (GOOD/MODERATE/POOR/VERY_POOR/UNKNOWN; unknown is missing metadata)
- **order:** —   **scales:** log x

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, non-interpretive title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
Fill placeholders from the plotted data and drop any sentence the data do not support.

> Raw-minus-boundary-weighted BGC count versus assembly N50 (n = <admitted_isolate_n> isolates). Weighted count = Interior + 0.5·Edge + 0.25·Full-contig; Unknown records remain in raw count only. This is a policy difference, not measured biological loss. Closed/circular status alone does not force a zero gap because Full-contig is assigned before the circular-origin exemption.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- Highlight a closed-genome subset only when topology and the observed values are source-bound; do not infer closed status or zero gap from N50 alone.
- Add a downstream trend arrow only if the talk needs it — keep it off the figure.

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
