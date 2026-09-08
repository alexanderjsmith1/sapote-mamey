# Sapote-Mamey Figure Style Rule

**Figures are data; interpretation lives in the caption.** A Sapote-Mamey figure must be regenerable-free for any wording change — because annotation tweaks should never cost a figure rebuild (a real concern for users on metered Claude plans, where regenerating a plot to move one label burns credits).

## A figure MAY contain
- Data (bars, points, lines, histograms), axes, axis labels, units.
- A **neutral, descriptive** title ("Chitinolytic gene complement per strain"), not an interpretive one ("...proves defensive symbiosis").
- A legend, color-coding, and reference lines (mean/threshold) — these carry signal without prose.
- **Numeric data labels** (the count on a bar) — these are data, not commentary.

## A figure MUST NOT contain
- **Arrows pointing to data points.** This is the primary rule.
- Overlaid interpretive callout text or floating annotations ("= 0 — lineage control", "the exception that proves the rule").
- Interpretive titles or subtitles that state a conclusion.
- Highlight boxes/circles drawn around specific points to make an argument.
- Governance labels, claim-ceiling ladders, release states, or policy footers on the plotted canvas.
  Scientific limitations belong in ordinary caption prose and machine receipts, not as a visual track.

## Where the interpretation goes instead
1. **The figure caption** (a `*_Captions.md` alongside the figures) — every callout, arrow target, and "note that X" belongs here. Free to edit, no regeneration.
2. **User-driven overlays** — the user adds arrows, circles, and callouts in PowerPoint / BioRender / Illustrator for a specific talk or panel, where they control placement and it doesn't touch the source figure.

## Fail before rendering meaningless output

Every scalable renderer must invoke the shared preflight in `mamey.figure_policy` before it
creates an output directory. The default quantitative policy refuses:

- no plotted rows;
- missing, nonnumeric, infinite, or NaN plotted values;
- a quantitative panel whose declared values are all zero;
- a scatter with fewer than two observations.

A scatter with two or more observations but no variation on any declared axis is retained with
a typed warning because equality across real observations can be a scientifically valid null
result. It should remain in the publication queue only if that null result answers a named question.

A typed-state matrix or a named diagnostic-null panel may explicitly permit all observed-zero
cells because observed zero can be the answer. The exception must use a registered semantic
code and its exact canonical explanation; arbitrary prose length is not a semantic gate. Both
must be declared in the chart configuration and receipt. Renderers must not synthesize either
field or replace a refusal with an apparently
successful blank plot, arbitrary origin point, or zero-height bar panel.

## Caption and methods acceptance

Every retained figure has a separate, editable traveling caption/method record. It must state:

1. the figure question and purpose of every panel;
2. the exact source artifacts, source release, and software/version context;
3. the unit of analysis represented by each point, row, cell, bar, branch, or count;
4. inclusion, exclusion, external-benchmark, reference, and outgroup roles;
5. total and per-group denominators, including missing and held records;
6. transformations, aggregations, duplicate/hybrid handling, and counting rules;
7. the complete visual grammar: colors, marks, lines, facets, order, thresholds, and compression;
8. summary statistics, intervals, box/whisker/error-bar definitions, models, tests, and multiple-testing treatment where used;
9. comparison groups and genus-control strategy;
10. contradictions and limitations, including assembly fragmentation, edge, overmerge, and stale/unbound evidence; and
11. the interpretation boundary for the plotted annotation or similarity.

Caption/method records use the versioned `sapote-mamey.figure-caption-methods.v2` contract. The
record must bind at least one exact source SHA-256 and must distinguish the overall study
denominator from the actual per-group values encoded in plotted rows. It also carries typed
missingness and external-benchmark sensitivity as separate fields. When a plotted-data table has
no typed state column, the caption says so explicitly; it must not imply that missing, held,
unmeasured, or not-applicable records are absent. Declared upstream artifact names without hashes
remain visibly `NOT_SUPPLIED_BY_WIDGET` rather than being presented as exact bindings.

For an invented or nonstandard visual, add a self-contained visual-grammar paragraph beneath
the figure explaining its rows, columns, marks, colors, symbols, and summary values. Review HTML
may display this prose directly below the clean SVG; the SVG remains reusable and free of policy
footers.

These fields travel with LLM-invented and other nonstandard figures until final manuscript
construction. They are validated before the renderer creates an output directory. An external
benchmark is not a study-cohort member: it must be explicitly typed, excluded from study n and
percentages, and default to not displayed unless the owner selects that benchmark comparison.
The renderer never infers benchmark status from an identifier. A selected benchmark may enter
only the separately reported sensitivity-comparison roster; it never enters strain-level study
plots, study denominators, or study percentages. The render receipt records available and
selected benchmark identifiers independently.

## Genus-aware comparison presets

Within-genus comparison is the default for strain-level interpretation. Cross-genus figures
must be stratified, matched, modelled, or display genus composition. A renderer may expose
additional genera as independent selectable options, but must not silently pool them into the
default roster. Presets are explicit inputs and receipts, not a hardcoded project cohort.

## Publication artwork gate

Blurred plot text in a compiled PDF is a major output defect. Publication artwork is validated at
its declared physical size before document rendering:

- `SINGLE_COLUMN` is 3.5 inches wide and `DOUBLE_COLUMN` is 7.2 inches wide;
- the smallest plot label, tick, support label, or annotation is at least 8 pt in both profiles;
- SVG is preferred and must contain live text plus vector geometry, with no embedded raster image;
- a PNG fallback must provide at least 300 native pixels per embedded inch. Metadata DPI does not
  rescue a thumbnail, and upscaling a screen PNG is refused;
- a PDF-derived screenshot is review evidence only and is never source artwork;
- caption text may not exceed 1.25 times the smallest plot text size; and
- document compilation preserves suitable vectors. A high-resolution raster fallback is allowed
  only when vector conversion is unavailable and the native-pixel gate passes.

Standalone PNG inspection does not establish compiled-document legibility. The compilation receipt
carries the physical profile, effective DPI for every raster, vector/live-text state, and embedded
artwork result. Renderers also reject colliding, touching, or overflowing label boxes. After the
final layout pass at declared physical width, every visible x/y tick-label bounding box must be
disjoint from the data rectangle for its own axes; label-label clearance alone is insufficient.
The reusable gate pairs labels and data rectangles by explicit `axis_id` and fails closed when an
axis binding is absent or a label touches or enters a data rectangle.

## Cohort, assembly, palette, and heatmap policy

An authoritative cohort manifest declares every identity's role, default inclusion, genus, cohort,
assembly state, and assembly reason. `EXTERNAL_BENCHMARK` and `OUTGROUP` are always default-off for
study figures. `DEFAULT_OFF` assembly outliers remain outside the study denominator even when
selected as sensitivity rows; included `FLAG` rows receive an open-diamond overlay. No private or
project-specific identity is built into this rule.

The default cohort palette is accessible and uses distinct solid fills. Hatching or other patterns
require an explicit owner override. Heatmaps preserve raw values, use robust quantile limits for
color normalization, and separate `OTHER` from the informative normalization range so a pooled or
extreme cell cannot flatten the remaining signal.

### F10 raw-domain-token provenance

F10 is a visualization of selected raw domain-token occurrences carried through
`deep_data.domain_hits`; it is not a regulator-gene caller. Its traveling caption/method record must
name the displayed raw tokens, identify the upstream antiSMASH GBK `aSDomain`/`PFAM_domain`
annotation types, and define one counted observation as one retained domain-hit occurrence assigned
to a BGC overlap. It must disclose the upstream deduplication boundary: whole-record GBKs are
preferred, region-file copies are excluded when those whole-record files exist, identical feature
keys are deduplicated, distinct loci remain distinct, and an upstream feature may be represented in
more than one per-BGC row when BGC intervals overlap. Any friendly family label is a display aid
chosen by Sapote-Mamey, not an independently validated functional call. `LysR_substrate` is a
substrate-binding-domain token and alone does not establish a complete LysR regulator or regulatory
role.

### F11 source-class hold

The legacy F11 clustermap is `REDESIGN_NOT_PUBLICATION_READY`. Its input
`deep_data.domain_hits` flattens retained domain-architecture rows without carrying the source
feature type and accession needed to distinguish Pfam records from aSDomain, motif, TIGRFAM, and
tool-like tokens. A renderer must not describe that mixed-token matrix as the “40 most abundant
Pfam domains.” Until a domain adapter binds feature type, accession, annotation source, source
feature identity, and BGC-overlap assignment, F11 emits a typed hold instead of artwork.

After that contract is supplied, the traveling methods must state the exact input files and hashes,
antiSMASH and Mamey versions, observation and deduplication unit, cohort/exclusion denominator,
top-row ranking rule, matrix transformation, distance and linkage, raw/positive ranges and zeros,
and the descriptive-only interpretation ceiling. Publication artwork must independently pass the
declared-width vector/live-text, minimum 8 pt, and no-raster-embedding gates.

## Why
A clean figure + a separate caption is reusable across every context (paper, slide, poster) and lets anyone re-label without touching the plot code. Baking callouts into the PNG couples the figure to one narrative and forces a rebuild for every rewording. When `tools/build_figures.py` is added, it must follow this rule — emit clean figures and a captions file, never overlaid callouts.
