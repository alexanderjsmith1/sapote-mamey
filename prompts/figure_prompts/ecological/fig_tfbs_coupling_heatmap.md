# Figure: TFBS regulator coupling heatmap

- **id:** `fig_tfbs_coupling_heatmap`
- **category:** ecological
- **audience:** manuscript
- **output:** `fig_tfbs_coupling_heatmap.png` (slides, ≥200 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `workbook sheet TFBS_Motifs (or gene_data tfbs)`
- **columns used:** sid, regulator, hit_count
- **row filter:** core regulators (FuR, ZuR, IolR, DmdR1, …)
- **derived fields:** pivot strain × regulator

## Plot
- **type:** heatmap (viridis)
- **x:** regulator   **y:** sid   **color:** hit_count
- **order:** strain rank   **scales:** —

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
> Transcription-factor binding-site signal per regulator across strains (n = 18); presence/strength of regulatory motifs, not expression.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- —

## Build note
Reproducible from the tidy export (`tools/export_figure_ready.py`) following the
`tools/plot_examples.py` pattern. Keep the slug and column names stable so decks don't break.
