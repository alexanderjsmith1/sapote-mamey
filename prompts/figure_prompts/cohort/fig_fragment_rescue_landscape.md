# Figure: Fragment-rescue landscape

- **id:** `fig_fragment_rescue_landscape`
- **category:** cohort
- **audience:** presentation / paper
- **output:** `fig_fragment_rescue_landscape.png` (slides, >=200 dpi) + `.svg`/`.pdf`

## Data
- **source:** `Fragment_Rescue_Tiers` sheet (or figure_ready join of strain_summary + scan_agg)
- **columns used:** Frag_Loss (x), EFLS_Pairs (y), RG_GMCI_HIGH (point size), Tier (color)
- **row filter:** all strains (n = 18)
- **derived fields:** Tier = A intact (N50 >= 1 Mb) / D failed (EFLS < 20) / B high-upside (EFLS >= 600) / C limited (else)

## Plot
- **type:** scatter; **x:** fragmentation loss (raw - corrected); **y:** EFLS fragment-linkage pairs
- **color:** tier (A #2a9d5a, B #2c6fbb, C #e0a030, D #cc4444); **size:** RG-GMCI HIGH pairs
- **order:** n/a; **scales:** linear

## Style
Inherit `FIGURE_CONVENTIONS.md`. No arrows/callouts on points. Legend below or outside data (never overlapping). EFLS is the recovery-upside axis (≈0 in closed genomes); do NOT use FLBR megasynthase census as a fragmentation axis (it is genome-wide and high even when closed).

## Caption (suggested — claim-safe)
> Fragment-rescue landscape (n = 18). Recoverable fragment-linkage content (EFLS) vs fragmentation loss; point size = reference-anchored recovery candidates. Tier B = highest re-sequencing yield.

## Overlay suggestions (downstream)
- Circle the Tier-B re-sequencing shortlist (SID-XXX, SID-XXX, SID-XXX) in PowerPoint.

## Build note
Reproducible from `Fragment_Rescue_Tiers`; keep tier thresholds stable so the figure matches the judgment pack §3.
