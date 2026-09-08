# REPAIR_SPEC_Q-021 — V381-G06 total-domain BGC bins

## Status

- Queue: FF402-Q-021, priority P1, status REPAIR_FIRST.
- Repair surface: fixed `total_domains` bin edges and explicit non-overmerge-resolution boundary.
- Authority: explicit owner historical methods policy (`HISTORICAL_REPAIR_REQUIREMENT_NO_RENDER_OR_SOURCE_MUTATION`).
- This is a specification only. No frozen proof, source file, or render is touched by this document.

## Exact source field(s) — PARTIALLY BOUND

- **Field:** `total_domains`, computed as `sum(domain_counts.values())` over a BGC's
  `domain_architecture` per-BGC source-scan record (`mamey/deep_data.py:32-49`,
  `extract_profiles()`). `domain_counts` is itself the output of Mamey's `domain_architecture`
  source scan over antiSMASH's own domain annotations for that region — this is a Mamey-derived
  aggregate, not a single raw antiSMASH field, and the caption must say so rather than implying a
  direct antiSMASH column.
- **Observation/deduplication unit:** one row per `(strain, bgc_id)` pair, matching the same
  physical-BGC identity contract used throughout this engine (`strain / full node-or-contig /
  region / bgc_alias`). A candidate must confirm it dedupes on this key, not on `bgc_id` alone
  (a bare `bgc_id` can repeat across strains and, within a fragmented assembly, potentially
  across regions).
- **Consumer:** `mamey/cohort_figures.py:1527-1528` (`G06 domain richness`) already reads this
  exact field for its existing (pre-repair) rendering — a repair candidate must read the same
  field, not a different or re-derived one.

## Denominator — NOT YET BOUND (owner binding required, see below)

The `total_domains` field itself is bound (above). What is **not** bound by this spec is which
BGCs are *retained* in the plotted cohort before binning — i.e., whether every governed BGC with
a `domain_architecture` record is included, or whether a boundary/assembly-quality floor (e.g.
excluding `VERY_POOR`-tier strains, or edge-truncated BGCs) applies first. The addendum text
("retained-BGC denominator, boundary/assembly context") requires this to be stated explicitly;
this spec cannot supply it without inventing a threshold, so it is named as an owner binding.

## Exclusions / defaults

- A BGC with no `domain_architecture` record at all (the source scan never ran, or the region
  was excluded upstream) must be excluded from the denominator, not silently counted as
  `total_domains = 0` — the current `dc.get(d, 0)` / `sum(dc.values())` pattern legitimately
  returns 0 for a BGC that has domains counted but none of the tracked kind, which is a real
  zero; that is different from a BGC that was never scanned at all, and a candidate must not
  conflate the two.
- The plot must state the fixed bin edges directly in the caption/methods block (not only in a
  legend), and must not silently widen or narrow them from one render to the next without a
  version-noted change — "fixed" per the policy requirement means fixed across the cohort's
  lifetime, not merely fixed within one render.

## Collision / legend-materiality / caption policy

- **POL-FF402-026** (verbatim): "Disclose fixed `total_domains` bin edges, observation/
  deduplication unit, retained-BGC denominator, boundary/assembly context, and state that the
  plot does not itself resolve overmerge. A candidate must emit the fixed edges and explicit
  non-resolution wording; no binning-only output may claim an overmerge correction state."
- The non-overmerge-resolution sentence is mandatory adjacent text, not an implied caveat — a
  reader must not be able to interpret a domain-richness bin as evidence that a fragmented/
  over-merged protocluster question has been settled.

## Acceptance checks

1. Caption/methods names `total_domains` exactly and states it is a Mamey-computed sum over the
   `domain_architecture` source scan's per-BGC domain counts, not a single raw antiSMASH field.
2. Caption states the observation/deduplication unit as the four-part physical-BGC identity.
3. Caption states the retained-BGC denominator explicitly (owner-bound value, once supplied).
4. Bin edges are printed as fixed values in the caption/methods, not only encoded visually.
5. A sentence stating the plot does not itself resolve or correct an overmerge/split-pathway
   question is present adjacent to the figure, not buried in a separate document.

## Owner binding required

1. **Retained-BGC denominator / boundary policy**: which assembly-quality tiers and boundary
   classes (interior/edge/full-contig) are included before binning — this spec deliberately does
   not choose a threshold.
2. **Fixed bin-edge values**: the actual numeric edges to lock in (this spec states the
   requirement that they be fixed and disclosed; it does not propose specific cut points, since
   that is a presentation decision on real cohort data, not a source-provenance question).

## Non-overlap statement

This spec does not implement, render, or touch the existing G06 figure or any frozen proof. It
binds only the source-field/observation-unit/non-resolution-wording contract a future G06
candidate must satisfy; the denominator and bin-edge values remain explicit open questions for
Alex, not silently assumed here.
