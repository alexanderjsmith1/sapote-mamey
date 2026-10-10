# Figure: Priority-leads table

- **id:** `fig_top_leads_table`
- **category:** tables
- **audience:** presentation
- **output:** `fig_top_leads_table.png` (slides, ≥300 dpi) + `.svg`/`.pdf` for print

## Data
- **source:** `figure_ready/diagnostics_long.csv + bgc_inventory.csv`
- **columns used:** diagnostics_long: strain, diagnostic_name, present; bgc_inventory: strain, bgc_id, contig, region, length_kb, boundary
- **row filter:** aggregate diagnostics may supply isolate context only. For a locus-ranked lead table, require independently admitted locus-specific diagnostic evidence; hold this rendering if that evidence is unavailable.
- **derived fields:** join locus-specific evidence on the complete strain / contig / region / bgc_id identity from one bound source record; rank only after that binding. Do not copy an aggregate marker onto every BGC.

## Plot
- **type:** formatted table
- **x:** —   **y:** —   **color:** diagnostic_name cell
- **order:** by strain   **scales:** —

## Style
Inherit `FIGURE_CONVENTIONS.md`. **No arrows, leader-lines, circles, or text callouts pointing at
individual data points** — emphasis is added downstream (PowerPoint / BioRender). Permitted
annotation: axis labels, legend, title, colorbar, and value labels flush at bar ends. A highlight
*color* (with a legend entry) is allowed.

## Caption (suggested — claim-safe)
> Candidate leads with complete source-bound locus identities and admitted locus-specific marker evidence. Isolate-level aggregate diagnostics remain separate context; scores and markers support class-level capacity hypotheses, with activity and expression unconfirmed.

## Overlay suggestions (add downstream in PowerPoint / BioRender — NOT in the figure)
- Color-code the diagnostic column consistently with the deck theme.

## Build note
The tidy export (`tools/export_figure_ready.py`) supplies inventory and isolate context only.
It does not emit the required locus-specific diagnostic join or a ranked leads table. Prepare and
validate that additional source-bound table before rendering; `tools/plot_examples.py` is a plotting
pattern, not an implementation of this recipe. Keep the slug and column names stable so decks don't break.
