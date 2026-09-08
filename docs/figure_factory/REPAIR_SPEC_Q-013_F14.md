# REPAIR_SPEC_Q-013 — F14 BGC PCA recolored by architecture cluster

## Status

- Queue: FF402-Q-013, priority P0, status REPAIR_FIRST.
- Repair surface: explanation/provenance, materially-present top-eight-and-other behavior,
  widget route, unclipped static caption/title.
- Disposition: `RETAIN_AND_DEEPEN / REDESIGN_EXPLANATION`, `WIDGET_CANDIDATE` (per the parent
  renderer-policy addendum). No render, patch, or scientific decision is authorized here.

## Exact source field(s) — NOT YET BOUND (owner binding required)

The addendum requires the dynamic caption/methods and provenance to state "the PCA observation
unit and the exact fixed feature vector" — this spec cannot supply the feature vector itself
without inventing one; it names the requirement precisely instead:

- **Observation unit**: must be stated as one row per physical BGC (four-part identity), not
  per strain and not per antiSMASH region alone — this spec requires the candidate to say which,
  explicitly, rather than leaving it implicit in the point-level data.
- **Feature vector**: the exact fixed set of input features the PCA was fit on (dimension count,
  field names, and their exact source — e.g. domain-count columns, KCB-derived fields, or a
  named upstream table) is an owner binding; no such vector is named anywhere in the addendum or
  the queue row.

## Denominator

Governed cohort and genus/role handling per the addendum's own wording ("the governed cohort,
genus/role handling") — this spec requires the candidate to name the exact strain-set/cohort
identity used to fit the PCA (not merely "the current cohort"), since PC positions are
fit-subset-dependent and a reader cannot interpret proximity without knowing the fitted set.

## Exclusions / defaults

- **Top-eight-and-other rule**: only architecture clusters with at least one materially plotted
  member in the final governed subset may appear in the legend/scale — an empty cluster is
  omitted, not shown as a zero-count legend entry (the cross-figure "material encodings only"
  rule in the addendum). The exact membership of the `other` bucket (everything past the top
  eight by the stated selection rule) must be disclosed, not left as an unlabeled residual.
- **Clustering rule** (bound, from the addendum): greedy cosine architecture-cluster
  construction at threshold `>= 0.85`. A candidate must use this exact rule and threshold, or
  explicitly flag and justify a deviation — it is not free to pick its own clustering method.
- Transformation, centering/scaling, typed missing-value handling, fitted-row denominator, and
  explained variance must all be stated adjacent to the figure (addendum, F14 section) — these
  are provenance requirements, not owner bindings; a candidate that omits any one of them fails
  this spec regardless of what the actual values turn out to be.

## Collision / legend-materiality / caption policy

- Cross-figure material-encodings rule (addendum): "A static figure legend, scale, or annotation
  category must be generated from values materially represented in the final governed subset. An
  encoding with zero plotted members is omitted."
- Cross-figure collision rule (addendum): "All dense static ordinations must pass a reusable
  label collision and plot-bounds check at final physical size. If labels cannot pass
  deterministically, the renderer must use leader lines, faceting, selected-label modes, a
  widget, or a small-multiple design; it must not silently accept overlap."
- Owner notes remain a separate artifact from the dynamic scientific caption/methods (addendum,
  cross-figure rule) — a candidate delivery that merges the two fails closed.

## Acceptance checks

1. Caption/methods states the PCA observation unit, exact feature vector (once owner-bound),
   transformation, centering/scaling, missing-value handling, fitted-row denominator, and
   explained variance — all present, none merely implied.
2. Caption states what PC proximity does and does not establish (a limited-interpretation
   sentence, not silence).
3. Clustering rule is stated as greedy cosine at threshold `>= 0.85`; any deviation is flagged
   explicitly, not silent.
4. Top-eight selection rule and exact `other` membership are both disclosed.
5. Static title/caption pass a reusable collision/plot-bounds check at declared final physical
   size (reuse the existing collision-check primitive rather than a bespoke one — see Non-overlap
   statement).
6. Point-level widget/hover data (future widget scope) carries the complete four-part identity
   per point, not a bare `bgc_id`.
7. Owner notes are a separate artifact from the caption/methods block.

## Owner binding required

1. **Exact PCA feature vector** — the fixed dimension set and its exact source field(s).
2. **Governed cohort identity** — which strain set the PCA is fit against for the next candidate.
3. **Whether the widget is in scope for this repair pass**, or whether only the corrected static
   artwork is being requested first (the addendum treats the widget as a companion, not a
   precondition, but does not itself set the pass boundary).

## Non-overlap statement

This spec does not implement or render F14. It is a specification only. It intentionally reuses
existing reusable primitives rather than proposing new ones — a future F14 candidate should route
its collision/plot-bounds check through whatever shared collision-check utility the F15/G01
candidates in this same batch also use (see `REPAIR_SPEC_Q-014_F15.md` and
`REPAIR_SPEC_Q-015_G01.md`), so the three do not each grow an independent, drifting
implementation of the same check.
