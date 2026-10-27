# Deliverable map: Project White Paper

Maps library figures to a **broad project white paper** (cohort overview for a PI / collaborator / funder).
Audience: mixed. Goal: the broad-view story — many genomes at once, patterns emerging. Order = narrative.
All figures inherit `FIGURE_CONVENTIONS.md` (no arrows on data points). Overlays go on the page in
PowerPoint/BioRender, never in the figure.

| # | Library figure | Data source | Caption (suggested) | Overlay (downstream) |
|---|---|---|---|---|
| 1 | `fig_fragmentation_loss_gradient` | strain_summary.csv | Raw-minus-boundary-weighted count vs assembly N50 (n=<admitted_isolate_n>); state the observed pattern and weighting/missingness limits without assuming monotonicity or convergence. | Circle the closed-genome cluster to anchor "why assembly matters". |
| 2 | `fig_strain_registry_table` | strain_summary.csv | The strain set: assembly metrics and BGC counts. | — |
| 3 | `fig_class_prevalence_bar` | class_prevalence.csv | Product-class prevalence across the cohort; universal classes are non-discriminating. | Shade the universal-class rows to flag them as excluded. |
| 4 | `fig_class_by_strain_heatmap` | class_by_strain.csv | BGCs per class × strain (top 20) — the cohort chemistry matrix. | Box a class row or strain column for the talk's subject. |
| 5 | `fig_kcb_dark_by_strain` | bgc_inventory.csv | Fraction of records with no exported top-hit text per strain, with missing/unsearched evidence separated; neither a novelty floor nor a fixed cohort percentage. | Note the fragmentation confound in the page text, not on the bar. |
| 6 | `fig_diagnostic_landscape_heatmap` | diagnostics_long.csv | Source-validated TIGRFAM diagnostic values with unavailable cells and actual per-diagnostic search status. | Spotlight the enediyne column. |
| 7 | `fig_cross_strain_findings_table` | cross_strain_findings.csv (overlay) | Findings carried from the bound synthesis sheet with explicit claim status; report any non-reproduction result only with its own evidence. | Color claim_status to the deck theme. |

**Note:** keep "other" decomposed (don't present the inflated universal "other"). If the white paper
discusses novelty, pair figure 5 with `fig_novelty_vs_fragmentation` so novelty is read jointly with assembly.
