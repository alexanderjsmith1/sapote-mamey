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
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
Fill every placeholder from the admitted plotted inputs and retain their provenance. Confirm each result-bearing sentence against those inputs; omit or revise any statement that does not hold for this set. For lead tables, state the displayed row count separately from the cohort isolate count.

> Loss of BGC count to fragmentation correction versus assembly contiguity (n = <admitted_isolate_n> isolates). Corrected count = Interior + 0.5·Edge + 0.25·full-contig. Loss approaches zero for closed genomes.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- Circle the closed-genome cluster (loss≈0, high N50) on the slide to anchor the "why assembly matters" point.
- Add a downstream trend arrow only if the talk needs it — keep it off the figure.

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
