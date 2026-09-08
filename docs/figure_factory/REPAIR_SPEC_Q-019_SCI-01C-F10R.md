# REPAIR_SPEC_Q-019 — FF402-SCI-01C-F10R profiles

## Status

- Queue: FF402-Q-019, priority P1, status REPAIR_FIRST.
- Repair surface: an authoritative cohort label (not an invented abbreviation), an exact
  producer/source field for every token family, and collision-safe categorical x-labels at
  declared physical width.
- Disposition: `RETAIN_AND_DEEPEN` (per the parent renderer-policy addendum). No frozen-proof
  mutation, delegated presentation, or render is authorized by this spec.

## Exact source field(s) — NOT YET BOUND (owner binding required)

The addendum names three token families this figure displays — transport, resistance-routing,
and regulatory — but does not name their exact source fields. This spec does not invent them:

- **Transport tokens**: candidate source lead only, not a binding — this engine already tracks a
  `resistance_tiers` source scan (seen in `mamey/deep_data.py`'s `rt = ss.get('resistance_tiers',
  ...)`) which may be the resistance-routing family's actual source; transport-specific fields
  are not yet identified anywhere reviewed for this spec.
- **Regulatory tokens**: not yet identified.
- Each of the three families must be bound to its **exact producer/source field**
  (POL-FF402-031) before any candidate implementation — a plausible-looking existing scan is not
  itself a binding; the owner must confirm it.

## Denominator

Not stated in the queue row or addendum beyond "an authoritative cohort/program label" — the
cohort scope itself is an owner binding (see below), separate from the label-wording question.

## Exclusions / defaults

- **No invented abbreviations**: an undefined shorthand (the addendum's own example: `BW`) must
  never appear on the visible surface. Use `Bee/Wasp`, or an explicitly defined authoritative
  label if the cohort in question is not that literal pairing (POL-FF402-029).
- Every abbreviation actually used elsewhere in the figure (axis, legend, title, caption) must be
  expanded at least once on the visible surface or in the adjacent methods block — a glossary
  buried in a separate document does not satisfy this.
- A token family with **no** confirmed producer/source field must not appear on the figure at
  all — POL-FF402-031 fails closed on this, and the current (unrepaired) rendering is explicitly
  stated as non-final until the source-bound successor passes layout QA.

## Collision / legend-materiality / caption policy

- **POL-FF402-029** (verbatim): "Do not show an invented or undefined cohort abbreviation such
  as BW; use Bee/Wasp or an explicitly defined authoritative label. A candidate must expand every
  cohort/program abbreviation in the visible title, legend, axis, caption, or adjacent methods
  block."
- **POL-FF402-030** (verbatim): "Require collision-safe categorical x-labels at the declared
  physical width, considering wrapping, spacing, faceting, rotation with sufficient margin, or
  separate panels/pages for evidence channels. A candidate must perform final-width plot-bounds
  and label-collision checks and choose an alternate layout when needed."
- **POL-FF402-031** (verbatim): "Define every displayed transport, resistance-routing, and
  regulatory-token family and name its exact producer/source field in the adjacent traveling
  caption/methods block. A candidate must fail closed when a visible token family lacks its
  exact producer/source field, and it must keep the current rendering non-final until the
  source-bound successor passes layout QA."

## Acceptance checks

1. No undefined/invented abbreviation appears anywhere on the visible surface; every abbreviation
   used is expanded on-surface or in the adjacent methods block.
2. Every visible transport/resistance-routing/regulatory token family names its exact
   producer/source field adjacent to the figure; a family with no confirmed field is not shown.
3. Categorical x-axis labels pass a final-physical-width collision/plot-bounds check; when they
   cannot, the candidate uses wrapping, rotation with margin, faceting, or separate panels rather
   than accepting overlap.
4. The figure is explicitly marked non-final in its own metadata/caption until the check above
   passes with the real, owner-bound source fields (not placeholder text).

## Owner binding required

1. **Cohort/program authoritative label** — confirm `Bee/Wasp` or supply the correct defined
   label if the actual cohort differs from that literal pairing.
2. **Transport-token family's exact producer/source field.**
3. **Resistance-routing-token family's exact producer/source field** (confirm or replace the
   `resistance_tiers` scan lead above).
4. **Regulatory-token family's exact producer/source field.**
5. **Cohort scope / denominator** for the figure as a whole.
6. Optional: **whether transport, resistance-routing, and regulatory tokens should be split into
   separate panels/pages** (the addendum explicitly allows this as a resolution to the collision
   policy, at the owner's discretion) — this spec does not choose a layout on the owner's behalf.

## Non-overlap statement

This spec does not implement, render, or bind any of the six owner items above by inference. It
shares its abbreviation-expansion and collision-check requirements with the other specs in this
batch (see `REPAIR_SPEC_Q-013_F14.md`, `REPAIR_SPEC_Q-014_F15.md`, `REPAIR_SPEC_Q-015_G01.md`)
so a future implementation reuses one shared collision-check utility rather than several.
