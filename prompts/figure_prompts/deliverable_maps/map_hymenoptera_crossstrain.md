# Deliverable map: Cross-Strain Ecological Synthesis (e.g. Hymenoptera actinomycetes)

Maps library figures to a **cross-strain ecological deliverable** (the Hymenoptera-cross-strain style).
Audience: ecologist / specialist. Goal: shared vs distinctive chemistry + the regulatory/ecological layer.
All figures inherit `FIGURE_CONVENTIONS.md` (no arrows on data points). This is Module-11 territory.

| # | Library figure | Data source | Caption (suggested) | Overlay (downstream) |
|---|---|---|---|---|
| 1 | `fig_class_prevalence_bar` | class_prevalence.csv | Shared backbone vs accessory chemistry across the strain set. | Bracket the accessory tail where the ecological story lives. |
| 2 | `fig_class_by_strain_heatmap` | class_by_strain.csv | Class × strain matrix — which strains carry which chemistry. | Group columns by host/habitat with a slide bracket. |
| 3 | `fig_core_ecological_signal_bar` | class_prevalence.csv (ectoine/siderophore/metallophore) | Near-core osmolyte + iron-acquisition layer; presence/absence, not assay. | — |
| 4 | `fig_tfbs_coupling_heatmap` | TFBS data (F2_Regulatory_TFBS / gene tfbs) | Regulatory-motif signal per regulator × strain (presence/strength, not expression). | Spotlight a regulator row tied to the ecological hypothesis. |
| 5 | `fig_other_class_decomposition_recurrent` | other_breakdown.csv (≥2 strains) | Recurrent finer categories within "other" — real shared chemistry, not the inflated catch-all. | — |

**Claim-safety:** ecological statements are presence/absence over conserved classes and motif signals —
never functional assays. Habitat-exclusive claims are retired (hglE-KS is collection-specific, prevalent-not-exclusive).
