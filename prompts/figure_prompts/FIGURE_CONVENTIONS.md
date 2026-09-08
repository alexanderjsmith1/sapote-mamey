# FIGURE_CONVENTIONS — read before generating ANY figure

These conventions are inherited by every prompt in this library. They exist so figures from
different sessions/LLMs look like one coherent set, and so a designer can finish them in
PowerPoint / BioRender / Illustrator without fighting baked-in decoration.

## The hard rule: no arrows or callouts on data points
- **Do NOT draw arrows, lines, leader-lines, circles, stars, or text callouts pointing at
  individual data points, bars, or cells.** Annotation is limited to: axis labels, tick labels,
  legend, title/subtitle, colorbar label, and value labels sitting flush at the end of a bar.
- Why: overlays are presentation decisions. They are added downstream in PowerPoint, BioRender,
  Keynote, or Illustrator, where they can be moved, restyled, or removed. A baked-in arrow cannot.
  Every prompt lists *overlay suggestions* separately so the figure stays clean and the emphasis
  is added on the slide.
- A highlight *color* for a category (e.g. singletons in a second color) is allowed — that is an
  encoding, not a point-callout. A legend must explain it.

## Legends
- Place the legend in **white space outside the data area** — preferably **below the x-axis labels**,
  or to the right of the plot. **Never overlap the legend with bars, points, or cells.** Overlap looks
  unfinished and hides data. If a figure is crowded, shrink the legend or drop it to a caption line.
- A user can always cut a clean legend and move it onto the figure in PowerPoint if they choose — but it
  must start *un-overlapped*.

## Palette (colorblind-safe, consistent — LOCKED house-style)
- Primary series: `#2c6fbb` (blue). Primary is BLUES-led; orange is retired as a series color
  (it reads poorly in print and overpowers blue). [v9.7.115]
- Secondary / categorical series: green family `#a8ddb5 · #52a878 · #1d6e44` (replaces the old
  orange highlight `#e07b39`). [v9.7.115]
- Sequential ordinal (e.g. Interior→Edge→Full-contig): 3-blue ramp `#cfe0f3 · #7fa9d6 · #3a6ea5`. [v9.7.115]
- Assembly tiers: GOOD `#2a9d5a` · MODERATE `#e0a030` · POOR `#cc4444`.
- Sequential (heatmaps): `viridis`. Binary present/absent: `Blues`. Diverging (rare): `RdBu`.
- Never rely on red/green alone to carry meaning.

## Heatmap normalization (avoid colorbar saturation) [v9.7.115]
A heatmap with one dominant row (e.g. GBL/AdpA TFBS at ~210 while every other row is <40)
saturates the colorbar and flattens all other signal to near-white — a real signal-loss failure.
Rule: when one row's max is >5× the median row max, default to **row-normalized** (each row scaled
to its own range) or **log1p**, and state which was used in the title. Don't ship a raw-scale
heatmap that hides its own data behind one outlier row.

## Figure-ID convention [v9.7.115]
Each figure carries a stable, typable ID (`COHORT-F1`, `DOT-D6`, `HM-…`, `SCAT-S3`) for catalog and
ordering. Per FIGURE_STYLE.md (figure = data, caption = claim), the corner-baked ID is for the
print catalog / ordering use ONLY; manuscript figures carry the ID in the **caption**, not baked
into the PNG. Emit both variants where it matters — corner-labeled for the catalog, clean for the
manuscript — or gate the corner label behind a `--catalog` flag.

## Typography & canvas (matplotlib rcParams — apply at top of every render)
- Font: DejaVu Sans. Sizes: title 13 · axis label 11 · tick 9 · bar value label 8.
- White background; top and right spines off; gridlines `alpha 0.25`.
- `savefig.dpi = 200` (slides), `bbox='tight'`. For print also emit `.svg`/`.pdf` at 300 dpi.
- Strain axis order = corrected-BGC rank (from `strain_summary.csv`, which is emitted in that order),
  so strains line up across every panel.

## Captions
- The caption is **text below the figure**, never inside it. Each prompt suggests one.
- Captions are claim-safe: antiSMASH product classes and KCB/MIBiG matches are **class-level
  hypotheses**, never assayed chemistry; say "candidate", "predicted", "consistent with".
- State n (e.g. "n = 18 strains") and the correction rule where relevant.

## Data hygiene
- Plot only from the tidy `figure_ready/` CSVs (one observation per row) or named workbook sheets.
- Never plot `kcb_cumulative` as a percentage — it is a cumulative score.
- Exclude the four universal classes (saccharide, fatty_acid, other, terpene) from shared/novel
  comparisons unless the figure is specifically about them.
- Carry strain order from `strain_summary.csv` (corrected-BGC rank) so panels line up across figures.

## File naming
- `fig_<slug>.png` / `.svg` / `.pdf`. Slugs are snake_case and stable across runs.
