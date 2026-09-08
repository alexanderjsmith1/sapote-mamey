# REPAIR_SPEC_Q-015 — G01 rare diagnostic-chemistry triggers per strain

## Status

- Queue: FF402-Q-015, priority P0, status REPAIR_FIRST.
- Repair surface: a readable declared-width vector static subset/facets, plus a selectable
  widget (strain, trigger/gene, color, genus-reference aggregation).
- Disposition: `RETAIN_AND_REDESIGN/WIDGET` (per the parent renderer-policy addendum). No
  render, patch, or scientific decision is authorized here.

## Exact source field(s) — NOT YET BOUND (owner binding required)

The addendum is explicit that this is the central open question for G01: "bind the exact
trigger/gene definitions, detector/source fields, annotation provenance, final selected-strain
denominator, and any genus-aware reference aggregation rule... No generic rendering or inferred
trigger provenance is authorized." This spec does not attempt to close that gap by inference.
What it does bind, as candidate leads for wherever the owner-supplied definitions should live:

- The engine already carries a `CCTT_triggers` field per BGC (semicolon-joined diagnostic
  tokens, e.g. the `T43-*` prefix family used by `mamey/activity_lead_report.py`'s
  `AF_PREFIXES`/`AB_PREFIXES` constants) — this is the most likely existing carrier of
  "diagnostic-chemistry trigger" values, but the queue's own wording ("rare diagnostic-chemistry
  triggers") may mean a narrower, rarity-filtered subset of that same field, not the full set.
  This spec flags the field as a candidate source; it does not assert it is the correct one.
  A candidate must confirm, not assume.
- Marker/trigger definitions in this engine increasingly live in a central registry
  (`mamey/registry_detector.py` / `mamey/registry_schema.py`, "B2 Phase 1: registry-backed
  detector loader") rather than hardcoded per-scan patterns — a repair candidate should check
  whether the specific triggers this figure needs are already registry-defined there before
  assuming an ad hoc detector must be written.

## Denominator — NOT YET BOUND (owner binding required)

"Final selected-strain denominator" is named explicitly in the addendum as unresolved. This spec
does not propose a strain subset.

## Exclusions / defaults

- No BGC/strain may be plotted under an inferred or generically-labeled trigger — every plotted
  trigger token must trace to an owner-confirmed source field.
- The static product must be a readable, declared-physical-width vector/live-text subset or set
  of facets — an unreadable cohort-wide page is explicitly named a redesign *failure*, not a
  reason to shrink text further (addendum, G01 section, verbatim intent preserved here).
- Any genus-aware reference aggregation rule (how a genus-level reference comparator is chosen
  or computed) is an owner binding, not a candidate-invented default.

## Collision / legend-materiality / caption policy

- Cross-figure material-encodings and collision rules (see `REPAIR_SPEC_Q-013_F14.md` for the
  full verbatim text) apply identically here: no zero-member legend entries; a reusable
  collision/plot-bounds check at declared final physical size; route to facets/widget/small-
  multiple rather than accept overlap.
- The companion widget must preserve the *same* source and denominator contract as the static
  artifact while adding selection controls (strain, trigger/gene, color, genus-reference
  aggregation) — the widget is a complement, not a separate, independently-sourced product.

## Acceptance checks

1. Every trigger/gene token displayed traces to an explicitly owner-confirmed source field —
   the candidate's own methods block names that field, not a placeholder like "diagnostic scan."
2. Detector/source-field, annotation-provenance, and genus-aggregation-rule sections are all
   present in the caption/methods, matching the addendum's named list exactly.
3. The static artifact fits its declared physical width with legible text at final size (a
   reusable collision/plot-bounds check, not a subjective eyeball pass).
4. The widget specification (if in scope for this pass) names the same source/denominator
   contract as the static artifact — no silent divergence between the two.
5. No render is produced by satisfying this spec; a failing check on any of the above blocks
   moving to implementation, not just to publication.

## Owner binding required

1. **Exact trigger/gene definitions** and their precise source field(s) — confirm or replace the
   `CCTT_triggers` candidate lead above.
2. **Detector/source-field and annotation-provenance** documentation, if not already covered by
   confirming (1).
3. **Final selected-strain denominator.**
4. **Genus-aware reference aggregation rule.**
5. **CPU-slot / scheduling confirmation** — the addendum notes this figure is held pending "a
   future CPU allocation"; this spec does not itself request or assume compute time.

## Non-overlap statement

This spec does not implement, render, or bind any of the five owner items above by inference —
doing so would be exactly the "inferred trigger provenance" the addendum prohibits. It shares
its collision-check and material-encodings wording with `REPAIR_SPEC_Q-013_F14.md` and
`REPAIR_SPEC_Q-014_F15.md` so a future implementation can reuse one shared collision-check
utility rather than three independent ones.
