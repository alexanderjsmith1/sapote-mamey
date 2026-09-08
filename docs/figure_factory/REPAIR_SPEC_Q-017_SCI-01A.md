# REPAIR_SPEC_Q-017 — FF402-SCI-01A genus-aware product-class profile

## Status

- Queue: FF402-Q-017, priority P0, status REPAIR_FIRST.
- Repair surface: omit `Other`; rounded unclipped 5/10 display ceiling; program-context labels;
  adjacent caption/methods.
- Disposition: `REDESIGN`; **policy only in this task** (per the addendum's own SCI-01A section:
  "No frozen-proof mutation, delegated presentation, or render... Retain as policy/test
  requirement only until a separately authorized candidate scope is supplied").

## Exact source field(s) — NOT YET BOUND (owner binding required)

Neither the queue row nor the addendum names the exact product-class source field or the
genus-assignment source for this figure. This is the one item in this batch where the owner's
own authorization explicitly stops at "policy/test requirement only" — no candidate scope has
been separately authorized yet, so this spec does not attempt to bind a source field the owner
has not yet scoped a candidate for.

## Denominator — NOT YET BOUND (owner binding required)

Not stated; withheld pending a separately authorized candidate scope, per the addendum.

## Exclusions / defaults

- **Omit `Other`**: a heterogeneous catch-all `Other` panel is omitted entirely when it is not a
  named, biologically interpretable comparison target (POL-FF402-021) — not shown collapsed,
  not shown at reduced opacity; omitted.
- **Display ceiling**: the quantitative axis/colorbar maximum is rounded UP to the nearest
  multiple of 5 or 10 that is `>= observed maximum`; the exact unrounded maximum is retained in
  a raw-value sidecar, never lost to the rounding (POL-FF402-022).
- **Program-context labels**: a repeated genus-only label is not permitted where multiple program
  contexts are present in the same figure — grouped headings or unambiguous program-by-genus
  labels are required instead (POL-FF402-023).

## Collision / legend-materiality / caption policy

- **POL-FF402-021** (verbatim): "Omit a heterogeneous catch-all Other panel when it is not a
  named biologically interpretable comparison target. A candidate must assert that no Other
  panel is emitted and the legend/scale is generated only from materially represented named
  categories."
- **POL-FF402-022** (verbatim): "Use a human-readable display maximum at a multiple of 5 or 10
  that is greater than or equal to the observed maximum, without clipping data. A focused
  renderer test must check rounded ceiling >= raw maximum and an exact raw-value sidecar retains
  the unrounded maximum."
- **POL-FF402-023** (verbatim): "Repeated genus labels require program context through grouped
  headings or unambiguous program-by-genus labels. A candidate must reject duplicate visible
  genus-only row labels when multiple program contexts are present."
- **POL-FF402-024** (verbatim): "Every owner-review delivery places the full formal caption and
  computational methods directly with the figure; Alex notes remain a separate artifact. A
  candidate delivery check must require adjacent caption/methods and fail if owner notes are
  merged into the scientific caption."

## Acceptance checks

1. No `Other` panel is emitted; every legend/scale entry traces to a materially represented named
   category.
2. Display ceiling is a multiple of 5 or 10, `>= observed maximum`; a raw-value sidecar exists
   and is not clipped.
3. No duplicate visible genus-only row label appears where more than one program context is
   present in the figure.
4. Formal caption and computational methods are adjacent to the figure; any owner/Alex notes are
   a distinct artifact, never merged into the caption.
5. **No render, patch, or delegated presentation occurs under this spec alone** — this item stays
   at policy/test-requirement status until Alex separately authorizes a candidate scope.

## Owner binding required

1. **Candidate-scope authorization** — this is the prerequisite gate itself; nothing else in
   this list can be bound until Alex authorizes a specific candidate scope for SCI-01A.
2. **Product-class source field** and its exact provenance.
3. **Genus-assignment source field.**
4. **Program-context taxonomy** — the exact set of "program contexts" the label-grouping rule
   (POL-FF402-023) must distinguish between.

## Non-overlap statement

This spec does not implement, render, or propose a candidate for SCI-01A — the addendum is
explicit that no candidate scope exists yet for this item. It exists only to pre-register the
four reusable acceptance checks (POL-FF402-021 through -024) against the shared policy test
(`tests/test_figure_repair_specs_v97405.py`) so a future candidate is checked against them from
its first draft, not discovered to violate them after the fact.
