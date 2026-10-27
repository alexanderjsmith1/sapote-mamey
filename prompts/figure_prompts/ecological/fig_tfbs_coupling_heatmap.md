# Figure: TFBS regulator coupling heatmap

- **id:** `fig_tfbs_coupling_heatmap`
- **category:** ecological
- **audience:** manuscript
- **output:** `fig_tfbs_coupling_heatmap.png` (slides, ≥300 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `workbook sheet TFBS_Motifs (or gene_data tfbs)`
- **columns used:** legacy TFBS_Motifs is wide: strain, taxonomy, motif-name columns, Total. The native gene_data.json writer currently emits tfbs={} as a placeholder; a separately populated mapping needs its own documented schema and source receipt. Neither source already has sid/regulator/hit_count columns.
- **row filter:** core regulators (FuR, ZuR, IolR, DmdR1, …)
- **derived fields:** first reshape only actual motif columns to strain, regulator (motif label), hit_count; exclude taxonomy and Total from motif values, preserve missingness, then pivot strain × regulator. Bind the selected source schema; do not infer a full motif profile from a total-hit field.

## Plot
- **type:** heatmap (viridis)
- **x:** regulator   **y:** strain   **color:** hit_count
- **order:** strain rank   **scales:** —

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, non-interpretive title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
Fill placeholders from the plotted data and drop any sentence the data do not support.

> Transcription-factor binding-site signal per regulator across isolates (n = <admitted_isolate_n> isolates); presence/strength of regulatory motifs, not expression.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- —

## Build note
The standard tidy exporter does not emit a TFBS table. Prepare the declared reshaped table from a bound TFBS_Motifs workbook or gene_data.json tfbs mapping before rendering; hold this figure when that source is unavailable. Keep the slug and column names stable so decks don't break.
