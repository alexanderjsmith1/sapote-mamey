# REPAIR_SPEC_Q-008 — BW01 Streptomyces bee boundary inventory

## Status

- Queue: FF402-Q-008, priority P0, status REPAIR_FIRST.
- Repair surface: preserve stacked bars; vertical padded or omitted y-axis title; materially
  represented categories only; reusable collision/plot-bounds check.
- Authority: `DEC-005` — an explicit owner figure decision (not merely a policy-TSV row; BW01 is
  not one of the nine POL-FF402-0xx-numbered items, so this spec cites the decision ledger entry
  directly instead of inventing a policy number for it).

## Exact source field(s) — NOT YET BOUND (owner binding required)

Neither `DEC-005` nor the cross-figure register row names the exact roster/source field this
figure's boundary counts are drawn from. The register row itself states the open item plainly:
"Bind exact roster/source and dynamic caption; retain owner notes separately." This spec does
not attempt to infer it — a Streptomyces/bee-boundary inventory could plausibly draw from the
strain-registry's host/genus fields, from a dedicated cohort-membership table, or from a
figure-specific pre-aggregated count; without an owner confirmation, guessing which would risk
exactly the "inferred provenance" failure mode this whole repair batch exists to close.

## Denominator

Not stated; part of the same "bind exact roster/source" open item above (owner binding
required). The final strain/BGC set the stacked bars are counted over must be named explicitly,
not left as "the current cohort."

## Exclusions / defaults

- **Structurally-zero `Unresolved` category**: omitted from the legend and scale (DEC-005,
  cross-figure register row, verbatim: "Omit structurally zero Unresolved from legend and scale;
  caption may state its zero count"). The caption *may* still disclose that the count is zero —
  omission from the legend/scale is not the same as hiding the fact from the reader; it means
  the reader is not shown a plotted bar/segment for a category with nothing in it.
- **Chart type preserved**: stacked bars are retained — this repair is not a chart-type redesign,
  it is a labeling/legend/collision correction on the existing format (DEC-005: "retain stacked
  bars").
- **Y-axis title**: vertical and padded, or omitted entirely if it cannot be laid out without
  collision — not rotated to an illegible angle, not truncated (DEC-005: "vertical or omitted
  y-axis title").

## Collision / legend-materiality / caption policy

- `DEC-005` (verbatim, `DECISION_AND_HOLD_LEDGER.tsv`): "BW01 Streptomyces bee boundary inventory
  is REDESIGN: vertical or omitted y-axis title, omit structurally zero Unresolved category,
  retain stacked bars, add reusable collision/plot-bounds check, and keep owner notes separate."
  Acceptance evidence required per the same ledger row: "Collision-check and visual-QA evidence
  before any corrected owner presentation."
- Cross-figure register row (verbatim summary): "Vertical padded y-axis title or omission;
  reusable collision/plot-bounds QA required."
- This repair should reuse the same collision/plot-bounds check utility named across the rest of
  this batch (see `REPAIR_SPEC_Q-013_F14.md` for the shared cross-figure collision-rule wording)
  rather than growing an independent BW01-specific one — the material-representation principle
  applied here (omit a structurally-zero category from the legend) is the same principle
  POL-FF402-021 applies to SCI-01A's `Other` panel, even though BW01 itself carries no
  POL-FF402 number.

## Acceptance checks

1. `Unresolved` does not appear in the legend or scale when its count is structurally zero; the
   caption may still state the zero count in prose.
2. Chart remains stacked bars; no chart-type substitution is introduced by this repair.
3. Y-axis title is vertical and padded, or omitted — never truncated or illegibly rotated.
4. A reusable collision/plot-bounds check passes at declared final physical size before any
   corrected presentation is shown to the owner.
5. Owner notes remain a separate artifact from the figure's own caption.
6. Every plotted roster/source field traces to an owner-confirmed field (once bound) — no
   category or count is presented from an inferred or guessed source.

## Owner binding required

1. **Exact roster/source field** the boundary-inventory counts are drawn from.
2. **Denominator** — the exact strain/BGC set the stacked bars are counted over.
3. **Confirmation that no other category besides `Unresolved` is currently structurally zero**
   in the intended final subset (if another category is also zero, the same omission rule
   applies to it, and the owner should confirm the full list rather than this spec assuming only
   one).

## Non-overlap statement

This spec does not implement, render, or touch the existing BW01 frozen artwork. It restates
`DEC-005`'s decision precisely as a set of testable acceptance checks and names the one binding
gap (`exact roster/source`) the decision itself left open, so a future candidate does not have to
re-derive DEC-005 from the ledger by hand.
