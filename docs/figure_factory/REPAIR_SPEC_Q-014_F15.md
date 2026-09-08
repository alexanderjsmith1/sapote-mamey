# REPAIR_SPEC_Q-014 — F15 strain ordination by mean BGC domain profile

## Status

- Queue: FF402-Q-014, priority P0, status REPAIR_FIRST.
- Repair surface: remove unused PRIVATE legend; collision-aware exact strain labels;
  authoritative roles and a per-strain default-off assembly-status policy.
- Disposition: `REDESIGN` (per the parent renderer-policy addendum). No render, patch, or
  scientific decision is authorized here.

## Exact source field(s) — PARTIALLY BOUND

- **Ordination basis**: mean BGC domain profile per strain (per the figure's own name/purpose;
  the exact feature columns feeding the mean are an owner binding, same shape of gap as F14's
  feature vector — see below).
- **Label roster**: strain identity labels must come from the authoritative strain-roster
  source this bundle already uses elsewhere (not a locally re-typed or ad hoc strain list) —
  this spec requires the candidate to name which authoritative source it reads, not invent a
  parallel one.
- **Default-off flag**: the addendum requires honoring "authoritative cohort/role handling and
  [a named strain's] `DEFAULT_OFF` behavior" — i.e. one specific strain carries a documented
  assembly-status flag that defaults it OFF the plot unless explicitly overridden. This spec
  does not repeat the strain's identifier (kept out of this document by house convention); the
  candidate must locate the flag from the authoritative strain/assembly metadata this bundle
  already tracks, not hardcode a strain-name exception in renderer code.

## Denominator — NOT YET BOUND (owner binding required)

Which strains are in scope for the ordination (the full governed cohort, or a filtered subset)
is not stated in the queue row or addendum beyond "authoritative cohort/role handling" — this is
named as an owner binding rather than assumed.

## Exclusions / defaults

- **PRIVATE legend entry**: removed unless materially represented in the final subset (the
  cross-figure material-encodings rule) — i.e. if zero strains in the final plotted subset carry
  a PRIVATE release tag, the legend entry for it does not appear at all, regardless of whether
  earlier drafts included it.
- **Default-off strain**: excluded from the plotted subset by default per its documented
  assembly-status flag; an explicit override (not a silent inclusion) is required to include it,
  and the caption must disclose whether the override was used.
- Labels must remain the exact strain identifiers — this repair explicitly forbids trading label
  legibility for identity loss (truncation, generic placeholders, or omission of colliding
  labels is not an acceptable resolution; see collision policy below).

## Collision / legend-materiality / caption policy

- Cross-figure material-encodings rule (addendum): unused/zero-member legend entries omitted.
- F15-specific collision rule (addendum, verbatim): "use leader lines, facets, or selected-label
  modes when labels are dense... refuse static output if labels, labels-to-points, title,
  caption, or plot bounds collide at the declared final size. If a collision-free static layout
  is not possible, F15 must route to a widget or small-multiple design rather than degrade exact
  strain identification."
- The ordination methods block (observation unit, feature vector, transformation/scaling,
  missingness, fit denominator, explained variance, PC-distance interpretation boundary) is
  mandatory adjacent text, matching F14's requirement — see `REPAIR_SPEC_Q-013_F14.md` for the
  shared wording; F15 must not omit any element F14 is also required to state.

## Acceptance checks

1. Caption/methods names the authoritative label-roster source and the ordination feature basis.
2. PRIVATE legend entry appears only when materially represented in the final subset.
3. The default-off strain's flag source is named (not hardcoded), and any override is disclosed.
4. Every plotted strain keeps its exact identifier — no truncation, generic label, or silent
   omission used to resolve a collision.
5. A reusable collision/plot-bounds check runs at the declared final physical size; on failure
   the candidate routes to a widget or small-multiple design rather than shipping an overlapping
   static figure.
6. Ordination methods block matches F14's required element list in full.

## Owner binding required

1. **Exact feature columns** feeding the per-strain mean BGC domain profile.
2. **Cohort scope** — which strains are in scope before the default-off exclusion is applied.
3. **Confirmation of the authoritative label-roster source** to read from (this spec names the
   requirement to use one; it does not itself pick which existing roster file/module is
   canonical for this candidate).

## Non-overlap statement

This spec does not implement or render F15. It shares its collision-check and ordination-methods
wording with `REPAIR_SPEC_Q-013_F14.md` deliberately, so a future implementation can share one
collision-check utility and one methods-block template across F14/F15/G01 rather than growing
three independent versions of the same requirement.
