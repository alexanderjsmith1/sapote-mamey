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
Inherit `FIGURE_CONVENTIONS.md`. No arrows/callouts on points. Legend below or outside data (never overlapping). EFLS is the recovery-upside axis (≈0 in closed genomes); do NOT use FLBR megasynthase census as a fragmentation axis (it is genome-wide and high even when closed).

## Caption (suggested — claim-safe)
Fill every placeholder from the admitted plotted inputs and retain their provenance. Confirm each result-bearing sentence against those inputs; omit or revise any statement that does not hold for this set. For lead tables, state the displayed row count separately from the cohort isolate count.

> Fragment-rescue landscape (n = <admitted_isolate_n> isolates). Recoverable fragment-linkage content (EFLS) vs fragmentation loss; point size = reference-anchored recovery candidates. Tier B is a deterministic high-upside priority group, not measured re-sequencing yield.

## Overlay suggestions (downstream)
- Circle the Tier-B re-sequencing shortlist (SID-XXX, SID-XXX, SID-XXX) in PowerPoint.

## Build note
Reproducible from `Fragment_Rescue_Tiers`; keep tier thresholds stable so the figure matches the judgment pack §3.

Preparation: on an authorized working copy of a canonical master workbook containing A2_Strain_Registry, A3_Run_Manifest, B4_Cross_Strain_Scans, D1_RGGMCI_All_Strains and C1/C2 DAPR sheets, `python tools/build_dapr_rescue_sheets.py <master_workbook.xlsx>` rebuilds the sheet in place. It is not produced by `export_figure_ready.py`. Retain the workbook hash and locked tier rule; do not invent missing scan/count inputs.
