# Figure: TFBS regulator coupling heatmap

- **id:** `fig_tfbs_coupling_heatmap`
- **category:** ecological
- **audience:** manuscript
- **output:** `fig_tfbs_coupling_heatmap.png` (slides, ≥300 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `workbook sheet TFBS_Motifs (or gene_data tfbs)`
- **columns used:** legacy TFBS_Motifs is wide: strain, taxonomy, motif-name columns, Total. Gene-data tfbs is a mapping keyed by isolate then motif. Neither source already has sid/regulator/hit_count columns.
- **row filter:** core regulators (FuR, ZuR, IolR, DmdR1, …)
- **derived fields:** first reshape only actual motif columns to strain, regulator (motif label), hit_count; exclude taxonomy and Total from motif values, preserve missingness, then pivot strain × regulator. Bind the selected source schema; do not infer a full motif profile from a total-hit field.

## Plot
- **type:** heatmap (viridis)
- **x:** regulator   **y:** strain   **color:** hit_count
- **order:** strain rank   **scales:** —

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
Fill every placeholder from the admitted plotted inputs and retain their provenance. Confirm each result-bearing sentence against those inputs; omit or revise any statement that does not hold for this set. For lead tables, state the displayed row count separately from the cohort isolate count.

> Transcription-factor binding-site signal per regulator across isolates (n = <admitted_isolate_n> isolates); presence/strength of regulatory motifs, not expression.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- —

## Build note
The standard tidy exporter does not emit a TFBS table. Prepare the declared reshaped table from a bound TFBS_Motifs workbook or gene_data.json tfbs mapping before rendering; hold this figure when that source is unavailable. Keep the slug and column names stable so decks don't break.
