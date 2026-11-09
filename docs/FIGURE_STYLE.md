# Figure style rule

**A figure shows data. The caption carries the interpretation.** Keep interpretive prose in a
separate caption file. Then you can reword the caption without redrawing the plot. If a caption is
embedded in a caption band or a compiled document, rebuild that file and inspect it again.

For the full checklist, see [Figure house rules](FIGURE_HOUSE_RULES.md). To find the renderer for a
figure type, see [Figures start here](FIGURES_START_HERE.md).

## A figure may contain
- Data (bars, points, lines, histograms), axes, axis labels and units.
- A neutral, descriptive title, such as "Chitinolytic gene complement per strain". Do not use a
  title that states a conclusion.
- A legend, color coding, and reference lines such as a mean or threshold.
- Numeric data labels, such as the count on a bar.
- Arrows that encode strand, gene order or a defined graph relation. These are data. Define them in
  the caption.

## A figure must not contain
- Arrows that point at selected data points.
- Callout text or floating annotations ("= 0, lineage control").
- Titles or subtitles that state a conclusion.
- Boxes or circles drawn around points to make an argument.
- Claim-safety wording, claim-ceiling ladders, release states or policy footers on the plotted
  canvas. Scientific limits go in the caption and the render receipt.

## Where interpretation goes
1. **The caption.** Put callouts, "note that X" and arrow targets in the figure's `_CAPTION.md`
   file (see [house rule 2](FIGURE_HOUSE_RULES.md#rules-for-every-figure)).
2. **Your own overlays.** For a talk or a panel, add arrows and circles yourself in PowerPoint,
   BioRender or Illustrator. Then the source figure stays clean.

## Size and file format
These limits apply to every figure that goes into a paper or deck.

- A single-column figure is 3.5 inches wide. A double-column figure is 7.2 inches wide.
- The smallest plot text is at least 8 pt at that width. This covers labels, ticks and notes.
- Caption text is no larger than 1.25 times the smallest plot text.
- Prefer SVG with live text and vector shapes, and no embedded raster image.
- A PNG needs at least 300 native pixels per inch. The DPI stored in the file does not count, and
  upscaling a screen PNG is not allowed.
- A screenshot of a PDF is for review only. It is never source artwork.
- No label may collide with, touch or run past another label. Tick labels must stay outside the data
  area of their own axes.

A PNG that looks fine on screen does not show that the text is legible in a compiled document.
Check the compiled file at its printed size. Run
`python tools/figure_render_qc.py <output_folder> --print-width-in <inches>` to find text below
8 pt at that width. It reads text only from a PDF or SVG beside the PNG; without a print width, or
without readable vector text, it reports the size as not checked or not measurable. It does not
look for clipped or overlapping labels. Look at the figure at its printed size for those.

## Refuse empty or meaningless plots
A renderer should stop before it creates an output folder when:
- there are no rows to plot;
- a plotted value is missing, not a number, infinite or NaN;
- a quantitative panel has only zeros; or
- a scatter has fewer than two observations.

A scatter with two or more observations and no spread on an axis is kept with a warning. A real
null result can be the answer. The shared check is `mamey.figure_policy`. A typed-state matrix or a
named diagnostic-null panel may allow all-zero cells if its chart configuration and receipt say so.
A renderer must never replace a refusal with a blank plot or a zero-height bar.

## What each caption and methods file states
Every kept figure has an editable caption and methods file. It states:

1. the question and the purpose of each panel;
2. the source files, their SHA-256, the source release and the software versions;
3. what one point, row, cell, bar, branch or count stands for;
4. which items are included, excluded, references or outgroups;
5. the total and per-group denominators, including missing and held records;
6. transformations, aggregation, and how duplicates and hybrids are counted;
7. the visual grammar: colors, marks, lines, facets, order, thresholds and compression;
8. statistics, intervals, box and whisker definitions, tests and multiple-testing handling;
9. the comparison groups and the genus-control strategy;
10. limits: assembly fragmentation, edge and over-merged regions, stale or unbound evidence; and
11. how far the interpretation may go.

If a plotted-data table has no state column for missing, held, unmeasured or not-applicable
records, the caption says so. It must not imply those records are absent.

For a figure type with no registered renderer, add a short paragraph under the figure. It explains
the rows, columns, marks, colors, symbols and summary values.

## Cohorts, benchmarks and genus
- An external benchmark is not a study member. Type it explicitly, leave it out of study n and
  percentages, and keep it off by default. The renderer never guesses benchmark status from an
  identifier. A selected benchmark appears only in a separate sensitivity comparison.
- Compare within a genus by default. A cross-genus figure must be stratified, matched, modeled, or
  show the genus mix. Do not pool genera silently.
- A cohort manifest gives each identity a role, default inclusion, genus, cohort and assembly state.
  Benchmarks and outgroups are always off by default. Assembly outliers marked default-off stay out
  of the study denominator. Included assembly-flag rows get an open diamond.
- The default cohort palette uses distinct solid fills. Hatching needs an explicit owner choice.
- Heatmaps keep raw values. They use quantile limits for the color scale. They keep `OTHER` out of
  that range so one extreme cell does not flatten the rest.

## Which tools enforce this
The page states the policy. Not every renderer enforces all of it. `mamey/figure_save.py` checks
text policy for figures saved through it. Many renderers write directly and use their own DPI.
Check the renderer you use, read its receipt, and look at the image. A missing check is a hold, not
a pass. The [locus-map review contract](LOCUS_MAP_REVIEW_CONTRACT.md) and the
[R workflows](R_FIGURE_WORKFLOWS.md) list route-specific gaps.

Domain figures F10 and F11 have extra provenance rules. See [Figure catalog](FIGURE_CATALOG.md).
