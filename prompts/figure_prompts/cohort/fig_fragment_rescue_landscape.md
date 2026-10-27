# Figure: Fragment-rescue landscape

- **id:** `fig_fragment_rescue_landscape`
- **category:** cohort
- **audience:** presentation / paper
- **output:** `fig_fragment_rescue_landscape.png` (slides, >=300 dpi) + `.svg`/`.pdf`

## Data
- **source:** a prepared `Fragment_Rescue_Tiers` workbook sheet; the standard figure-ready exporter does not emit a scan_agg CSV alternative
- **columns used:** Frag_Loss (x), EFLS_Pairs (y), RG_GMCI_HIGH (point size), Tier (color)
- **row filter:** all admitted isolates in the prepared sheet; compute n from those rows
- **derived fields:** Tier = A intact (N50 >= 1 Mb) / D failed (EFLS < 20) / B high-upside (EFLS >= 600) / C limited (else)

## Plot
- **type:** scatter; **x:** fragmentation loss (raw - corrected); **y:** EFLS fragment-linkage pairs
- **color:** tier (A #2a9d5a, B #2c6fbb, C #e0a030, D #cc4444); **size:** RG-GMCI HIGH pairs
- **order:** n/a; **scales:** linear

## Style
Inherit `FIGURE_CONVENTIONS.md`. No arrows/callouts on points. Legend below or outside data (never overlapping). EFLS is a heuristic shared-label pair count, not measured recoverability; two Interior records are skipped, but closed/circular status alone does not prove zero pairs. Do NOT substitute FLBR megasynthase counts as a fragmentation measure.

## Caption (suggested — claim-safe)
Fill placeholders from the plotted data and drop any sentence the data do not support.

> Fragment-rescue landscape (n = <admitted_isolate_n> isolates). Heuristic shared-label EFLS candidate pairs vs raw-minus-boundary-weighted count; point size = reference-anchored candidate count. Neither axis measures physical fragment linkage or recovered content. Tier B is a deterministic high-upside priority group, not measured re-sequencing yield.

## Overlay suggestions (downstream)
- Circle the Tier-B re-sequencing shortlist (SID-XXX, SID-XXX, SID-XXX) in PowerPoint.

## Build note
Reproducible from `Fragment_Rescue_Tiers`; keep tier thresholds stable so the figure matches the judgment pack §3.

Preparation: on an authorized working copy of a canonical master workbook containing A2_Strain_Registry, A3_Run_Manifest, B4_Cross_Strain_Scans, D1_RGGMCI_All_Strains and C1/C2 DAPR sheets, `python tools/build_dapr_rescue_sheets.py <master_workbook.xlsx>` rebuilds the sheet in place. It is not produced by `export_figure_ready.py`. Retain the workbook hash and locked tier rule; do not invent missing scan/count inputs.
