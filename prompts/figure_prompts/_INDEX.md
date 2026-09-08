# _INDEX — figure-prompt library

27 figure prompts across 5 categories, plus 4 deliverable-map recipes (31 prompt files total). Each figure maps to its exact data source; each map composes library figures into a named deliverable. Global rules in `FIGURE_CONVENTIONS.md`; usage in `HOW_TO_USE.md`.

| category | figure id | data source |
|---|---|---|
| cohort | `fig_fragmentation_loss_gradient` | figure_ready/strain_summary.csv |
| cohort | `fig_raw_vs_corrected_bgc` | figure_ready/strain_summary.csv |
| cohort | `fig_bgc_yield_by_tier` | figure_ready/strain_summary.csv |
| cohort | `fig_genome_size_vs_bgc` | figure_ready/strain_summary.csv |
| cohort | `fig_class_prevalence_bar` | figure_ready/class_prevalence.csv |
| cohort | `fig_class_by_strain_heatmap` | figure_ready/class_by_strain.csv |
| cohort | `fig_class_composition_stacked` | figure_ready/class_by_strain.csv |
| cohort | `fig_other_class_decomposition_all` | figure_ready/other_breakdown.csv |
| cohort | `fig_other_class_decomposition_recurrent` | figure_ready/other_breakdown.csv |
| cohort | `fig_edge_status_composition` | figure_ready/bgc_inventory.csv |
| cohort | `fig_diagnostic_landscape_heatmap` | figure_ready/diagnostics_long.csv |
| cohort | `fig_domain_burden_heatmap` | domain_level/domain_role_counts_by_bgc.csv |
| cohort | `fig_fragment_rescue_landscape` | `Fragment_Rescue_Tiers` sheet (or figure_ready join of strain_summary + scan_agg) |
| novelty | `fig_kcb_dark_by_strain` | figure_ready/bgc_inventory.csv |
| novelty | `fig_novelty_vs_fragmentation` | figure_ready/bgc_inventory.csv + strain_summary.csv |
| per_strain | `fig_per_strain_bgc_ranking` | figure_ready/bgc_inventory.csv |
| per_strain | `fig_per_strain_class_donut` | figure_ready/bgc_class_long.csv |
| per_strain | `fig_per_strain_cohort_context_panel` | figure_ready/strain_summary.csv + class_by_strain.csv + bgc_inventory.csv |
| per_strain | `fig_domain_role_burden` | domain_level/domain_complexity_metrics_by_bgc.csv |
| per_strain | `fig_domain_strip` | domain_level/domain_rows_long.csv (ordered by cds_start) |
| ecological | `fig_tfbs_coupling_heatmap` | workbook sheet TFBS_Motifs |
| ecological | `fig_core_ecological_signal_bar` | figure_ready/class_prevalence.csv |
| tables | `fig_strain_registry_table` | figure_ready/strain_summary.csv |
| tables | `fig_top_leads_table` | figure_ready/diagnostics_long.csv + bgc_inventory.csv |
| tables | `fig_cross_strain_findings_table` | figure_ready/cross_strain_findings.csv |
| tables | `fig_top_antibacterial_leads` | workbook sheet C1_DAPR_Antibacterial |
| tables | `fig_top_antifungal_leads` | workbook sheet C2_DAPR_Antifungal |

## deliverable_maps — recipes that compose library figures into a named deliverable

These are not single figures; each is a recipe mapping several library figures (+ downstream overlays) into a complete deliverable. See each file for the figure list, captions, and overlay notes.

| map id | deliverable | composes |
|---|---|---|
| `map_gene_by_gene` | per-strain gene-by-gene BGC deep-dive (single-strain, 30+pp) | per_strain + novelty figures filtered to one strain |
| `map_hymenoptera_crossstrain` | cross-strain ecological synthesis (e.g. Hymenoptera actinomycetes) | cohort + ecological figures |
| `map_judgment_pack` | Sapote judgment pack (DAPR antibacterial + antifungal boards + fragment-rescue evaluation) | tables (C1/C2 leads) + fragment-rescue figure |
| `map_white_paper` | broad project white paper (cohort overview for PI / collaborator / funder) | cohort + novelty + tables figures |
